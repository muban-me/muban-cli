"""
Base HTTP client for Muban API.

Handles session management, authentication, retries, and error handling.
"""

import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List, Union
from urllib.parse import urljoin

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .. import __version__
from ..config import MubanConfig, get_config, get_config_manager
from ..exceptions import (
    APIError,
    AuthenticationError,
    TemplateNotFoundError,
    PermissionDeniedError,
    ValidationError,
)

logger = logging.getLogger(__name__)


class HTTPClient:
    """
    Base HTTP client for the Muban API.
    
    Handles:
    - Session management with retry logic
    - Authentication headers
    - Token refresh
    - Error response handling
    """
    
    API_VERSION = "v1"
    
    def __init__(self, config: Optional[MubanConfig] = None):
        """
        Initialize the HTTP client.
        
        Args:
            config: Optional configuration. Uses global config if not provided.
        """
        self.config = config or get_config()
        self._session: Optional[requests.Session] = None
        self._auto_refresh: bool = True
        self._refresh_attempted: bool = False
    
    @property
    def session(self) -> requests.Session:
        """Get or create HTTP session with retry logic."""
        if self._session is None:
            self._session = requests.Session()
            
            retry_strategy = Retry(
                total=self.config.max_retries,
                backoff_factor=1,
                backoff_max=120,
                status_forcelist=[429, 502, 503, 504],
                allowed_methods=["HEAD", "GET", "OPTIONS", "POST", "PUT", "DELETE"],
                respect_retry_after_header=True,
            )
            adapter = HTTPAdapter(max_retries=retry_strategy)
            self._session.mount("http://", adapter)
            self._session.mount("https://", adapter)
            
            self._session.headers.update({
                "User-Agent": f"muban-cli/{__version__}",
                "Accept": "application/json",
            })
        
        return self._session
    
    @property
    def base_url(self) -> str:
        """Get the base URL for API requests."""
        return urljoin(self.config.server_url, f"/api/{self.API_VERSION}/")
    
    def _get_headers(self, extra_headers: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        """Get request headers including authentication."""
        headers = {}
        
        if self.config.token:
            headers["Authorization"] = f"Bearer {self.config.token}"
        
        if extra_headers:
            headers.update(extra_headers)
        
        return headers
    
    def _handle_response(
        self,
        response: requests.Response,
        expected_status: Union[int, List[int]] = 200
    ) -> Dict[str, Any]:
        """Handle API response and raise appropriate exceptions."""
        if isinstance(expected_status, int):
            expected_status = [expected_status]
        
        logger.debug(f"Request: {response.request.method} {response.request.url}")
        logger.debug(f"Response: {response.status_code}")
        
        if response.status_code in expected_status:
            if response.status_code == 204:
                return {"success": True}
            try:
                return response.json()
            except ValueError:
                return {"success": True, "content": response.content}
        
        try:
            error_data = response.json()
            error_msg = self._extract_error_message(error_data)
            
            meta = error_data.get("meta", {})
            correlation_id = meta.get("correlationId") or meta.get("correlation_id")
            if correlation_id:
                logger.error(
                    "API error [%s %s] status=%d correlation_id=%s",
                    response.request.method,
                    response.request.url,
                    response.status_code,
                    correlation_id
                )
        except ValueError:
            error_msg = response.text or f"HTTP {response.status_code}"
            error_data = {}
        
        if response.status_code == 401:
            raise AuthenticationError(
                "Authentication failed: " + (error_msg or "Please check your API key."),
                details=error_msg
            )
        elif response.status_code == 403:
            raise PermissionDeniedError(
                "Permission denied: " + (error_msg or "You don't have access to this resource."),
                status_code=response.status_code,
                response_data=error_data
            )
        elif response.status_code == 404:
            raise TemplateNotFoundError(
                "Resource not found: " + (error_msg or "The requested resource does not exist."),
                status_code=response.status_code,
                response_data=error_data
            )
        elif response.status_code == 400:
            raise ValidationError(
                f"Invalid request: {error_msg}",
                details=str(error_data)
            )
        elif response.status_code == 422:
            raise ValidationError(
                f"Validation failed: {error_msg}",
                details=str(error_data)
            )
        else:
            raise APIError(
                f"API request failed: {error_msg}",
                status_code=response.status_code,
                response_data=error_data
            )
    
    def _extract_error_message(self, error_data: Dict[str, Any]) -> str:
        """Extract error message from API response."""
        messages = []
        
        if "errors" in error_data and error_data["errors"]:
            errors = error_data["errors"]
            if isinstance(errors, list) and errors:
                error_messages = []
                for err in errors:
                    if isinstance(err, dict):
                        code = err.get("code", "")
                        msg = err.get("message", str(err))
                        if code:
                            error_messages.append(f"[{code}] {msg}")
                        else:
                            error_messages.append(msg)
                    else:
                        error_messages.append(str(err))
                messages.append("; ".join(error_messages))
        elif "message" in error_data:
            messages.append(error_data["message"])
        elif "data" in error_data:
            messages.append(str(error_data["data"]))
        else:
            messages.append(str(error_data))
        
        meta = error_data.get("meta", {})
        correlation_id = meta.get("correlationId") or meta.get("correlation_id")
        if correlation_id:
            messages.append(f"(Correlation ID: {correlation_id})")
        
        return " ".join(messages)
    
    def _try_refresh_token(self) -> bool:
        """Attempt to refresh the access token if a refresh token is available."""
        if self._refresh_attempted:
            return False
        
        self._refresh_attempted = True
        
        if not self.config.has_refresh_token():
            logger.debug("No refresh token available for automatic refresh")
            return False
        
        logger.info("Access token expired, attempting automatic refresh...")
        
        try:
            from ..auth import MubanAuthClient
            import time
            
            with MubanAuthClient(self.config) as auth_client:
                result = auth_client.refresh_token(self.config.refresh_token)
                
                token = result.get('access_token')
                if token:
                    self.config.token = token
                    
                    if result.get('refresh_token'):
                        self.config.refresh_token = result['refresh_token']
                    
                    if result.get('expires_in'):
                        self.config.token_expires_at = int(time.time()) + int(result['expires_in'])
                    
                    try:
                        config_manager = get_config_manager()
                        config_manager.save(self.config)
                        logger.info("Token refreshed and saved successfully")
                    except Exception as e:
                        logger.warning(f"Could not persist refreshed token: {e}")
                    
                    return True
        except Exception as e:
            logger.warning(f"Automatic token refresh failed: {e}")
        
        return False
    
    def request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        files: Optional[Dict[str, Any]] = None,
        stream: bool = False,
        expected_status: Union[int, List[int]] = 200,
    ) -> Dict[str, Any]:
        """
        Make an API request.
        
        Args:
            method: HTTP method
            endpoint: API endpoint (relative to base URL)
            params: Query parameters
            json_data: JSON body data
            files: Files for multipart upload
            stream: Whether to stream the response
            expected_status: Expected status code(s)
        
        Returns:
            Parsed response data
        """
        if self._auto_refresh and self.config.is_token_expired():
            self._try_refresh_token()
        
        self._refresh_attempted = False
        
        url = urljoin(self.base_url, endpoint)
        headers = self._get_headers()
        
        if params:
            params = {k: v for k, v in params.items() if v is not None}
        
        try:
            response = self.session.request(
                method=method,
                url=url,
                params=params,
                json=json_data,
                files=files,
                headers=headers,
                timeout=self.config.timeout,
                verify=self.config.verify_ssl,
                stream=stream,
            )
            
            if response.status_code == 401 and self._auto_refresh and not self._refresh_attempted:
                if self._try_refresh_token():
                    headers = self._get_headers()
                    response = self.session.request(
                        method=method,
                        url=url,
                        params=params,
                        json=json_data,
                        files=files,
                        headers=headers,
                        timeout=self.config.timeout,
                        verify=self.config.verify_ssl,
                        stream=stream,
                    )
                    
        except requests.exceptions.ConnectionError as e:
            raise APIError(f"Connection failed: {e}")
        except requests.exceptions.Timeout as e:
            raise APIError(f"Request timed out: {e}")
        except requests.exceptions.RequestException as e:
            raise APIError(f"Request failed: {e}")
        
        return self._handle_response(response, expected_status)
    
    def download(
        self,
        endpoint: str,
        output_path: Path,
        params: Optional[Dict[str, Any]] = None,
    ) -> Path:
        """Download a file from the API."""
        url = urljoin(self.base_url, endpoint)
        headers = self._get_headers()
        
        try:
            response = self.session.get(
                url,
                params=params,
                headers=headers,
                timeout=self.config.timeout,
                verify=self.config.verify_ssl,
                stream=True,
            )
        except requests.exceptions.RequestException as e:
            raise APIError(f"Download failed: {e}")
        
        if response.status_code == 404:
            raise TemplateNotFoundError("Resource not found")
        elif response.status_code == 401:
            raise AuthenticationError("Authentication failed")
        elif response.status_code == 403:
            raise PermissionDeniedError("Permission denied")
        elif response.status_code != 200:
            raise APIError(f"Download failed with status {response.status_code}")
        
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        return output_path
    
    def close(self) -> None:
        """Close the HTTP session."""
        if self._session:
            self._session.close()
            self._session = None
    
    def __enter__(self) -> "HTTPClient":
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()
