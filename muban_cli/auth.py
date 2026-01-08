"""
Authentication module for Muban CLI.

Handles OAuth2/credential-based authentication to obtain JWT tokens.
"""

import logging
from typing import Optional, Dict, Any
from urllib.parse import urljoin

import requests

from .config import MubanConfig
from .exceptions import AuthenticationError, APIError

logger = logging.getLogger(__name__)


class MubanAuthClient:
    """
    Authentication client for obtaining JWT tokens.
    
    Supports:
    - Password grant (username/password)
    - Client credentials grant
    - Token refresh
    """
    
    # Common auth endpoint paths to try
    AUTH_ENDPOINTS = [
        "/oauth/token",
        "/auth/token",
        "/api/auth/token",
        "/api/v1/auth/token",
        "/api/v1/auth/login",
        "/auth/login",
    ]
    
    def __init__(self, config: MubanConfig):
        """
        Initialize authentication client.
        
        Args:
            config: Muban configuration
        """
        self.config = config
        self._session: Optional[requests.Session] = None
    
    @property
    def session(self) -> requests.Session:
        """Get or create HTTP session."""
        if self._session is None:
            self._session = requests.Session()
            self._session.headers.update({
                "User-Agent": "muban-cli/1.0.0",
                "Accept": "application/json",
                "Content-Type": "application/json",
            })
        return self._session
    
    @property
    def auth_base_url(self) -> str:
        """Get the base URL for authentication."""
        return self.config.get_auth_server_url()
    
    def login(
        self,
        username: str,
        password: str,
        auth_endpoint: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Authenticate with username and password.
        
        Args:
            username: User's username or email
            password: User's password
            auth_endpoint: Optional custom auth endpoint path
        
        Returns:
            Dict containing access_token and optionally refresh_token
        
        Raises:
            AuthenticationError: If authentication fails
        """
        # Try specified endpoint or common ones
        endpoints_to_try = [auth_endpoint] if auth_endpoint else self.AUTH_ENDPOINTS
        
        last_error = None
        
        for endpoint in endpoints_to_try:
            if endpoint is None:
                continue
                
            try:
                result = self._try_login(endpoint, username, password)
                if result:
                    return result
            except AuthenticationError as e:
                last_error = e
                # If it's a clear auth failure, don't try other endpoints
                if "Invalid credentials" in str(e) or "401" in str(e):
                    raise
            except APIError as e:
                last_error = e
                logger.debug(f"Auth endpoint {endpoint} failed: {e}")
                continue
        
        if last_error:
            raise last_error
        
        raise AuthenticationError(
            "Could not find authentication endpoint. "
            "Please specify --auth-endpoint or configure auth_server_url."
        )
    
    def _try_login(
        self,
        endpoint: str,
        username: str,
        password: str
    ) -> Optional[Dict[str, Any]]:
        """
        Try to authenticate at a specific endpoint.
        
        Args:
            endpoint: Auth endpoint path
            username: Username
            password: Password
        
        Returns:
            Token response or None if endpoint not found
        """
        url = urljoin(self.auth_base_url, endpoint.lstrip('/'))
        logger.debug(f"Trying auth endpoint: {url}")
        
        # Try different request formats
        # Format 1: JSON body with username/password
        json_payload = {
            "username": username,
            "password": password
        }
        
        # Format 2: OAuth2 password grant (form data)
        form_payload = {
            "grant_type": "password",
            "username": username,
            "password": password
        }
        
        # Try JSON format first
        try:
            response = self.session.post(
                url,
                json=json_payload,
                timeout=self.config.timeout,
                verify=self.config.verify_ssl,
            )
            
            if response.status_code == 404:
                # Endpoint not found, try next
                return None
            
            return self._handle_auth_response(response)
            
        except requests.exceptions.RequestException:
            pass
        
        # Try form data format (OAuth2 style)
        try:
            response = self.session.post(
                url,
                data=form_payload,
                headers={
                    "Content-Type": "application/x-www-form-urlencoded",
                    "Accept": "application/json",
                },
                timeout=self.config.timeout,
                verify=self.config.verify_ssl,
            )
            
            if response.status_code == 404:
                return None
            
            return self._handle_auth_response(response)
            
        except requests.exceptions.RequestException as e:
            raise APIError(f"Connection failed: {e}")
    
    def _handle_auth_response(self, response: requests.Response) -> Dict[str, Any]:
        """
        Handle authentication response.
        
        Args:
            response: HTTP response
        
        Returns:
            Token data
        
        Raises:
            AuthenticationError: On auth failure
        """
        if response.status_code == 200:
            try:
                data = response.json()
                
                # Extract token from various response formats
                token = (
                    data.get("access_token") or
                    data.get("token") or
                    data.get("data", {}).get("access_token") or
                    data.get("data", {}).get("token")
                )
                
                if token:
                    return {
                        "access_token": token,
                        "refresh_token": data.get("refresh_token"),
                        "expires_in": data.get("expires_in"),
                        "token_type": data.get("token_type", "Bearer"),
                    }
                else:
                    raise AuthenticationError(
                        "Authentication succeeded but no token in response"
                    )
            except ValueError as e:
                raise AuthenticationError(f"Invalid response format: {e}")
        
        elif response.status_code == 401:
            try:
                error_data = response.json()
                msg = (
                    error_data.get("message") or
                    error_data.get("error_description") or
                    error_data.get("error") or
                    "Invalid credentials"
                )
            except ValueError:
                msg = "Invalid credentials"
            
            raise AuthenticationError(f"Authentication failed: {msg}")
        
        elif response.status_code == 400:
            try:
                error_data = response.json()
                msg = error_data.get("message") or error_data.get("error") or "Bad request"
            except ValueError:
                msg = response.text or "Bad request"
            
            raise AuthenticationError(f"Authentication error: {msg}")
        
        else:
            raise APIError(
                f"Unexpected response: HTTP {response.status_code}",
                status_code=response.status_code
            )
    
    def refresh_token(
        self,
        refresh_token: str,
        auth_endpoint: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Refresh an access token using a refresh token.
        
        Args:
            refresh_token: The refresh token
            auth_endpoint: Optional custom endpoint
        
        Returns:
            New token data
        """
        endpoint = auth_endpoint or "/oauth/token"
        url = urljoin(self.auth_base_url, endpoint.lstrip('/'))
        
        payload = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token
        }
        
        try:
            response = self.session.post(
                url,
                data=payload,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=self.config.timeout,
                verify=self.config.verify_ssl,
            )
            
            return self._handle_auth_response(response)
            
        except requests.exceptions.RequestException as e:
            raise APIError(f"Token refresh failed: {e}")
    
    def close(self) -> None:
        """Close the HTTP session."""
        if self._session:
            self._session.close()
            self._session = None
    
    def __enter__(self) -> "MubanAuthClient":
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()
