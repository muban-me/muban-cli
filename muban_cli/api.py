"""
API client for Muban Document Generation Service.

Implements all REST API endpoints as defined in the OpenAPI specification.
"""

import logging
from pathlib import Path
from typing import Optional, Dict, Any, List, Union
from datetime import datetime
from urllib.parse import urljoin

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .config import MubanConfig, get_config, get_config_manager
from .exceptions import (
    APIError,
    AuthenticationError,
    TemplateNotFoundError,
    PermissionDeniedError,
    ValidationError,
)

logger = logging.getLogger(__name__)


class MubanAPIClient:
    """
    Client for interacting with the Muban Document Generation Service API.
    
    Supports all API v1 endpoints including:
    - Template management (list, get, upload, download, delete)
    - Document generation
    - Audit operations
    - Admin operations
    - Configuration
    """
    
    API_VERSION = "v1"
    
    def __init__(self, config: Optional[MubanConfig] = None):
        """
        Initialize the API client.
        
        Args:
            config: Optional configuration. Uses global config if not provided.
        """
        self.config = config or get_config()
        self._session: Optional[requests.Session] = None
        self._auto_refresh: bool = True  # Enable automatic token refresh
        self._refresh_attempted: bool = False  # Track if refresh was already tried
    
    @property
    def session(self) -> requests.Session:
        """Get or create HTTP session with retry logic."""
        if self._session is None:
            self._session = requests.Session()
            
            # Configure retry strategy
            retry_strategy = Retry(
                total=3,
                backoff_factor=1,
                status_forcelist=[429, 500, 502, 503, 504],
                allowed_methods=["HEAD", "GET", "OPTIONS", "POST", "PUT", "DELETE"],
            )
            adapter = HTTPAdapter(max_retries=retry_strategy)
            self._session.mount("http://", adapter)
            self._session.mount("https://", adapter)
            
            # Set default headers
            self._session.headers.update({
                "User-Agent": "muban-cli/1.0.0",
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
        """
        Handle API response and raise appropriate exceptions.
        
        Args:
            response: The HTTP response
            expected_status: Expected status code(s)
        
        Returns:
            Parsed JSON response data
        """
        if isinstance(expected_status, int):
            expected_status = [expected_status]
        
        # Log request details in verbose mode
        logger.debug(f"Request: {response.request.method} {response.request.url}")
        logger.debug(f"Response: {response.status_code}")
        
        # Handle successful responses
        if response.status_code in expected_status:
            if response.status_code == 204:
                return {"success": True}
            try:
                return response.json()
            except ValueError:
                # Binary response or empty
                return {"success": True, "content": response.content}
        
        # Parse error response
        try:
            error_data = response.json()
            error_msg = self._extract_error_message(error_data)
        except ValueError:
            error_msg = response.text or f"HTTP {response.status_code}"
            error_data = {}
        
        # Map status codes to exceptions
        if response.status_code == 401:
            raise AuthenticationError(
                "Authentication failed. Please check your API key.",
                details=error_msg
            )
        elif response.status_code == 403:
            raise PermissionDeniedError(
                "Permission denied. You don't have access to this resource.",
                status_code=response.status_code,
                response_data=error_data
            )
        elif response.status_code == 404:
            raise TemplateNotFoundError(
                "Resource not found.",
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
        # Try different error formats
        if "errors" in error_data and error_data["errors"]:
            errors = error_data["errors"]
            if isinstance(errors, list) and errors:
                return errors[0].get("message", str(errors[0]))
        
        if "message" in error_data:
            return error_data["message"]
        
        if "data" in error_data:
            return str(error_data["data"])
        
        return str(error_data)
    
    def _try_refresh_token(self) -> bool:
        """
        Attempt to refresh the access token if a refresh token is available.
        
        Returns:
            True if token was refreshed successfully, False otherwise
        """
        if self._refresh_attempted:
            # Already tried refreshing in this request cycle
            return False
        
        self._refresh_attempted = True
        
        if not self.config.has_refresh_token():
            logger.debug("No refresh token available for automatic refresh")
            return False
        
        logger.info("Access token expired, attempting automatic refresh...")
        
        try:
            from .auth import MubanAuthClient
            import time
            
            with MubanAuthClient(self.config) as auth_client:
                result = auth_client.refresh_token(self.config.refresh_token)
                
                token = result.get('access_token')
                if token:
                    # Update config in memory
                    self.config.token = token
                    
                    if result.get('refresh_token'):
                        self.config.refresh_token = result['refresh_token']
                    
                    if result.get('expires_in'):
                        self.config.token_expires_at = int(time.time()) + int(result['expires_in'])
                    
                    # Persist to disk
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
    
    def _request(
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
        # Check if token is expired and try to refresh before making request
        if self._auto_refresh and self.config.is_token_expired():
            self._try_refresh_token()
        
        # Reset refresh flag for this request cycle
        self._refresh_attempted = False
        
        url = urljoin(self.base_url, endpoint)
        headers = self._get_headers()
        
        # Remove None values from params
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
            
            # If we get 401 and haven't tried refresh yet, try to refresh and retry
            if response.status_code == 401 and self._auto_refresh and not self._refresh_attempted:
                if self._try_refresh_token():
                    # Update headers with new token and retry
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
    
    def _download(
        self,
        endpoint: str,
        output_path: Path,
        params: Optional[Dict[str, Any]] = None,
    ) -> Path:
        """
        Download a file from the API.
        
        Args:
            endpoint: API endpoint
            output_path: Path to save the file
            params: Query parameters
        
        Returns:
            Path to the downloaded file
        """
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
        
        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write content to file
        with open(output_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        return output_path
    
    # ========== Template Operations ==========
    
    def list_templates(
        self,
        page: int = 1,
        size: int = 20,
        search: Optional[str] = None,
        sort_by: Optional[str] = None,
        sort_dir: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        List templates with pagination.
        
        Args:
            page: Page number (1-indexed)
            size: Items per page
            search: Search term
            sort_by: Sort field (name, author, created, fileSize)
            sort_dir: Sort direction (asc, desc)
        
        Returns:
            Paginated list of templates
        """
        params: Dict[str, Any] = {"page": page, "size": size}
        if search:
            params["search"] = search
        if sort_by:
            params["sortBy"] = sort_by
        if sort_dir:
            params["sortDir"] = sort_dir
        
        return self._request("GET", "templates", params=params)
    
    def get_template(self, template_id: str) -> Dict[str, Any]:
        """
        Get template details.
        
        Args:
            template_id: Template UUID
        
        Returns:
            Template details
        """
        return self._request("GET", f"templates/{template_id}")
    
    def get_template_parameters(self, template_id: str) -> Dict[str, Any]:
        """
        Get template parameters.
        
        Args:
            template_id: Template UUID
        
        Returns:
            List of template parameters
        """
        return self._request("GET", f"templates/{template_id}/params")
    
    def get_template_fields(self, template_id: str) -> Dict[str, Any]:
        """
        Get template fields.
        
        Args:
            template_id: Template UUID
        
        Returns:
            List of template fields
        """
        return self._request("GET", f"templates/{template_id}/fields")
    
    def upload_template(
        self,
        file_path: Path,
        name: str,
        author: str,
        metadata: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Upload a new template.
        
        Args:
            file_path: Path to ZIP file
            name: Template name
            author: Template author
            metadata: Optional metadata
        
        Returns:
            Uploaded template details
        """
        if not file_path.exists():
            raise ValidationError(f"File not found: {file_path}")
        
        if not file_path.suffix.lower() == '.zip':
            raise ValidationError("Template must be a ZIP file")
        
        with open(file_path, 'rb') as f:
            files = {
                'file': (file_path.name, f, 'application/zip'),
            }
            data = {
                'name': name,
                'author': author,
            }
            if metadata:
                data['metadata'] = metadata
            
            url = urljoin(self.base_url, "templates/upload")
            headers = self._get_headers()
            
            response = self.session.post(
                url,
                data=data,
                files=files,
                headers=headers,
                timeout=self.config.timeout,
                verify=self.config.verify_ssl,
            )
            
            return self._handle_response(response)
    
    def download_template(
        self,
        template_id: str,
        output_path: Optional[Path] = None
    ) -> Path:
        """
        Download a template.
        
        Args:
            template_id: Template UUID
            output_path: Optional output path
        
        Returns:
            Path to downloaded file
        """
        if output_path is None:
            output_path = Path(f"{template_id}.zip")
        
        return self._download(f"templates/{template_id}/download", output_path)
    
    def delete_template(self, template_id: str) -> Dict[str, Any]:
        """
        Delete a template.
        
        Args:
            template_id: Template UUID
        
        Returns:
            Success response
        """
        return self._request(
            "DELETE",
            f"templates/{template_id}",
            expected_status=[200, 204]
        )
    
    def generate_document(
        self,
        template_id: str,
        output_format: str,
        parameters: List[Dict[str, Any]],
        output_path: Optional[Path] = None,
        filename: Optional[str] = None,
        data: Optional[Dict[str, Any]] = None,
        document_locale: Optional[str] = None,
        pdf_export_options: Optional[Dict[str, Any]] = None,
        html_export_options: Optional[Dict[str, Any]] = None,
        ignore_pagination: bool = False
    ) -> Path:
        """
        Generate a document from a template.
        
        Args:
            template_id: Template UUID
            output_format: Output format (pdf, xlsx, docx, rtf, html)
            parameters: List of parameter name/value pairs
            output_path: Optional output path
            filename: Optional custom filename
            data: Optional JSON data source
            document_locale: Optional locale (e.g., 'en_US', 'pl_PL')
            pdf_export_options: PDF-specific options
            html_export_options: HTML-specific options
            ignore_pagination: Whether to ignore pagination
        
        Returns:
            Path to generated document
        """
        # Build request body
        request_data: Dict[str, Any] = {
            "parameters": parameters
        }
        
        if filename:
            request_data["filename"] = filename
        if data:
            request_data["data"] = data
        if document_locale:
            request_data["documentLocale"] = document_locale
        if pdf_export_options:
            request_data["pdfExportOptions"] = pdf_export_options
        if html_export_options:
            request_data["htmlExportOptions"] = html_export_options
        if ignore_pagination:
            request_data["ignorePagination"] = ignore_pagination
        
        # Make request
        url = urljoin(self.base_url, f"templates/{template_id}/generate/{output_format}")
        headers = self._get_headers({"Content-Type": "application/json"})
        
        try:
            response = self.session.post(
                url,
                json=request_data,
                headers=headers,
                timeout=self.config.timeout * 2,  # Allow more time for generation
                verify=self.config.verify_ssl,
                stream=True,
            )
        except requests.exceptions.RequestException as e:
            raise APIError(f"Document generation failed: {e}")
        
        if response.status_code != 200:
            self._handle_response(response)
        
        # Determine output path
        if output_path is None:
            content_disposition = response.headers.get('Content-Disposition', '')
            if 'filename=' in content_disposition:
                fname = content_disposition.split('filename=')[1].strip('"\'')
            else:
                fname = filename or f"document.{output_format}"
            output_path = Path(fname)
        
        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write content
        with open(output_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        return output_path
    
    def generate_document_raw(
        self,
        template_id: str,
        output_format: str,
        request_data: Dict[str, Any],
        output_path: Optional[Path] = None
    ) -> Path:
        """
        Generate a document with a raw request body.
        
        This allows passing the full request body for advanced testing.
        
        Args:
            template_id: Template UUID
            output_format: Output format (pdf, xlsx, docx, rtf, html)
            request_data: Full request body as dict
            output_path: Optional output path
        
        Returns:
            Path to generated document
        """
        url = urljoin(self.base_url, f"templates/{template_id}/generate/{output_format}")
        headers = self._get_headers({"Content-Type": "application/json"})
        
        try:
            response = self.session.post(
                url,
                json=request_data,
                headers=headers,
                timeout=self.config.timeout * 2,
                verify=self.config.verify_ssl,
                stream=True,
            )
        except requests.exceptions.RequestException as e:
            raise APIError(f"Document generation failed: {e}")
        
        if response.status_code != 200:
            self._handle_response(response)
        
        # Determine output path
        if output_path is None:
            content_disposition = response.headers.get('Content-Disposition', '')
            if 'filename=' in content_disposition:
                fname = content_disposition.split('filename=')[1].strip('"\'')
            else:
                fname = f"document.{output_format}"
            output_path = Path(fname)
        
        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write content
        with open(output_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        return output_path
    
    def get_fonts(self) -> Dict[str, Any]:
        """Get available fonts."""
        return self._request("GET", "templates/fonts")
    
    def get_icc_profiles(self) -> Dict[str, Any]:
        """Get available ICC profiles."""
        return self._request("GET", "templates/icc-profiles")
    
    # ========== Admin Operations ==========
    
    def verify_template_integrity(self, template_id: str) -> Dict[str, Any]:
        """
        Verify template integrity (admin only).
        
        Args:
            template_id: Template UUID
        
        Returns:
            Verification result
        """
        return self._request(
            "POST",
            f"admin/templates/{template_id}/verify-integrity",
            expected_status=[200, 422]
        )
    
    def regenerate_template_digest(self, template_id: str) -> Dict[str, Any]:
        """
        Regenerate template digest (admin only).
        
        Args:
            template_id: Template UUID
        
        Returns:
            Regeneration result
        """
        return self._request("POST", f"admin/templates/{template_id}/regenerate-digest")
    
    def regenerate_all_digests(self) -> Dict[str, Any]:
        """
        Regenerate all template digests (admin only).
        
        Returns:
            Regeneration results
        """
        return self._request(
            "POST",
            "admin/templates/regenerate-all-digests",
            expected_status=[200, 207, 500]
        )
    
    # ========== Audit Operations ==========
    
    def get_audit_logs(
        self,
        page: int = 1,
        size: int = 50,
        event_type: Optional[str] = None,
        severity: Optional[str] = None,
        user_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        success: Optional[bool] = None
    ) -> Dict[str, Any]:
        """
        Get audit logs with filtering (admin only).
        
        Args:
            page: Page number
            size: Items per page
            event_type: Filter by event type
            severity: Filter by severity (LOW, MEDIUM, HIGH, CRITICAL)
            user_id: Filter by user ID
            ip_address: Filter by IP address
            start_time: Start time filter
            end_time: End time filter
            success: Filter by success status
        
        Returns:
            Paginated audit logs
        """
        params: Dict[str, Any] = {"page": page, "size": size}
        
        if event_type:
            params["eventType"] = event_type
        if severity:
            params["severity"] = severity
        if user_id:
            params["userId"] = user_id
        if ip_address:
            params["ipAddress"] = ip_address
        if start_time:
            params["startTime"] = start_time.isoformat()
        if end_time:
            params["endTime"] = end_time.isoformat()
        if success is not None:
            params["success"] = success
        
        return self._request("GET", "audit/logs", params=params)
    
    def get_audit_log(self, log_id: str) -> Dict[str, Any]:
        """Get specific audit log entry (admin only)."""
        return self._request("GET", f"audit/logs/{log_id}")
    
    def get_audit_statistics(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Get audit statistics (admin only)."""
        params = {}
        if start_time:
            params["startTime"] = start_time.isoformat()
        if end_time:
            params["endTime"] = end_time.isoformat()
        
        return self._request("GET", "audit/statistics", params=params)
    
    def get_security_events(
        self,
        page: int = 1,
        size: int = 50,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Get security events (admin only)."""
        params: Dict[str, Any] = {"page": page, "size": size}
        if start_time:
            params["startTime"] = start_time.isoformat()
        if end_time:
            params["endTime"] = end_time.isoformat()
        
        return self._request("GET", "audit/security", params=params)
    
    def get_failed_operations(
        self,
        page: int = 1,
        size: int = 50,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Get failed operations (admin only)."""
        params: Dict[str, Any] = {"page": page, "size": size}
        if start_time:
            params["startTime"] = start_time.isoformat()
        if end_time:
            params["endTime"] = end_time.isoformat()
        
        return self._request("GET", "audit/failures", params=params)
    
    def get_user_activity(
        self,
        user_id: str,
        page: int = 1,
        size: int = 50,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Get audit logs for specific user (admin only)."""
        params: Dict[str, Any] = {"page": page, "size": size}
        if start_time:
            params["startTime"] = start_time.isoformat()
        if end_time:
            params["endTime"] = end_time.isoformat()
        
        return self._request("GET", f"audit/users/{user_id}", params=params)
    
    def get_event_types(self) -> Dict[str, Any]:
        """Get available audit event types."""
        return self._request("GET", "audit/event-types")
    
    def get_severity_levels(self) -> Dict[str, Any]:
        """Get available severity levels."""
        return self._request("GET", "audit/severity-levels")
    
    def get_audit_health(self) -> Dict[str, Any]:
        """Check audit system health."""
        return self._request("GET", "audit/health")
    
    def cleanup_audit_logs(self) -> Dict[str, Any]:
        """Trigger audit log cleanup (admin only)."""
        return self._request("POST", "audit/cleanup")
    
    # ========== Audit Dashboard ==========
    
    def get_dashboard_overview(self) -> Dict[str, Any]:
        """Get audit dashboard overview (admin only)."""
        return self._request("GET", "audit/dashboard/overview")
    
    def get_security_threats(self) -> Dict[str, Any]:
        """Get security threats summary (admin only)."""
        return self._request("GET", "audit/dashboard/security-threats")
    
    def get_system_health_metrics(self) -> Dict[str, Any]:
        """Get system health metrics (admin only)."""
        return self._request("GET", "audit/dashboard/system-health")
    
    def get_user_activity_patterns(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Get user activity patterns (admin only)."""
        params = {}
        if start_time:
            params["startTime"] = start_time.isoformat()
        if end_time:
            params["endTime"] = end_time.isoformat()
        
        return self._request("GET", "audit/dashboard/user-patterns", params=params)
    
    def get_compliance_activity(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Get compliance activity dashboard (admin only)."""
        params = {}
        if start_time:
            params["startTime"] = start_time.isoformat()
        if end_time:
            params["endTime"] = end_time.isoformat()
        
        return self._request("GET", "audit/dashboard/compliance", params=params)
    
    # ========== User Management ==========
    
    def get_current_user(self) -> Dict[str, Any]:
        """Get current authenticated user profile."""
        return self._request("GET", "users/me")
    
    def update_current_user(
        self,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        email: Optional[str] = None
    ) -> Dict[str, Any]:
        """Update current user profile."""
        data = {}
        if first_name is not None:
            data["firstName"] = first_name
        if last_name is not None:
            data["lastName"] = last_name
        if email is not None:
            data["email"] = email
        
        return self._request("PUT", "users/me", json_data=data)
    
    def change_current_user_password(
        self,
        current_password: str,
        new_password: str
    ) -> Dict[str, Any]:
        """Change current user's password."""
        return self._request(
            "PUT",
            "users/me/password",
            json_data={
                "currentPassword": current_password,
                "newPassword": new_password
            }
        )
    
    def list_users(
        self,
        page: int = 1,
        size: int = 20,
        search: Optional[str] = None,
        role: Optional[str] = None,
        enabled: Optional[bool] = None,
        sort_by: Optional[str] = None,
        sort_dir: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        List users (admin only).
        
        Args:
            page: Page number
            size: Page size
            search: Search query (username, email, name)
            role: Filter by role (ROLE_USER, ROLE_ADMIN, ROLE_MANAGER)
            enabled: Filter by enabled status
            sort_by: Sort field (username, email, firstName, lastName, created, lastLogin)
            sort_dir: Sort direction (asc, desc)
        """
        params: Dict[str, Any] = {"page": page, "size": size}
        if search:
            params["search"] = search
        if role:
            params["role"] = role
        if enabled is not None:
            params["enabled"] = enabled
        if sort_by:
            params["sortBy"] = sort_by
        if sort_dir:
            params["sortDir"] = sort_dir
        
        return self._request("GET", "users", params=params)
    
    def get_user(self, user_id: str) -> Dict[str, Any]:
        """Get user by ID (admin or own profile)."""
        return self._request("GET", f"users/{user_id}")
    
    def create_user(
        self,
        username: str,
        email: str,
        password: str,
        first_name: str,
        last_name: str,
        roles: Optional[List[str]] = None,
        enabled: bool = True
    ) -> Dict[str, Any]:
        """
        Create new user (admin only).
        
        Args:
            username: Username (3-50 chars)
            email: Email address
            password: Password (min 8 chars)
            first_name: First name
            last_name: Last name
            roles: List of roles (ROLE_USER, ROLE_ADMIN, ROLE_MANAGER)
            enabled: Whether user is enabled
        """
        data = {
            "username": username,
            "email": email,
            "password": password,
            "firstName": first_name,
            "lastName": last_name,
            "enabled": enabled
        }
        if roles:
            data["roles"] = roles
        
        return self._request("POST", "users", json_data=data, expected_status=201)
    
    def update_user(
        self,
        user_id: str,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        email: Optional[str] = None
    ) -> Dict[str, Any]:
        """Update user profile (admin or own profile)."""
        data = {}
        if first_name is not None:
            data["firstName"] = first_name
        if last_name is not None:
            data["lastName"] = last_name
        if email is not None:
            data["email"] = email
        
        return self._request("PUT", f"users/{user_id}", json_data=data)
    
    def delete_user(self, user_id: str) -> Dict[str, Any]:
        """Delete user (admin only, cannot delete own account)."""
        return self._request("DELETE", f"users/{user_id}", expected_status=204)
    
    def update_user_roles(
        self,
        user_id: str,
        roles: List[str]
    ) -> Dict[str, Any]:
        """
        Update user roles (admin only).
        
        Args:
            user_id: User UUID
            roles: List of roles (ROLE_USER, ROLE_ADMIN, ROLE_MANAGER)
        """
        return self._request(
            "PUT",
            f"users/{user_id}/roles",
            json_data={"roles": roles}
        )
    
    def change_user_password(
        self,
        user_id: str,
        current_password: str,
        new_password: str
    ) -> Dict[str, Any]:
        """Change user password (admin or own password)."""
        return self._request(
            "PUT",
            f"users/{user_id}/password",
            json_data={
                "currentPassword": current_password,
                "newPassword": new_password
            }
        )
    
    def enable_user(self, user_id: str) -> Dict[str, Any]:
        """Enable user account (admin only)."""
        return self._request("PUT", f"users/{user_id}", json_data={"enabled": True})
    
    def disable_user(self, user_id: str) -> Dict[str, Any]:
        """Disable user account (admin only)."""
        return self._request("PUT", f"users/{user_id}", json_data={"enabled": False})
    
    # ========== Async Operations ==========
    
    def submit_bulk_async(
        self,
        requests: List[Dict[str, Any]],
        batch_correlation_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Submit bulk async document generation requests.
        
        Args:
            requests: List of request items with templateId, format, parameters
            batch_correlation_id: Optional correlation ID for the entire batch
        
        Returns:
            Bulk submission response with tracking IDs
        """
        payload: Dict[str, Any] = {"requests": requests}
        if batch_correlation_id:
            payload["batchCorrelationId"] = batch_correlation_id
        return self._request("POST", "async/bulk", json_data=payload)
    
    def get_async_workers(self) -> Dict[str, Any]:
        """Get worker thread status (admin only)."""
        return self._request("GET", "async/workers")
    
    def get_async_requests(
        self,
        status: Optional[str] = None,
        user_id: Optional[str] = None,
        template_id: Optional[str] = None,
        since: Optional[datetime] = None,
        page: int = 1,
        size: int = 20
    ) -> Dict[str, Any]:
        """
        Get paginated list of async requests.
        
        Args:
            status: Filter by status (QUEUED/PROCESSING/COMPLETED/FAILED/TIMEOUT)
            user_id: Filter by user ID
            template_id: Filter by template ID
            since: Filter by start time
            page: Page number
            size: Items per page (max 100)
        
        Returns:
            Paginated async requests
        """
        params: Dict[str, Any] = {"page": page, "size": size}
        if status:
            params["status"] = status
        if user_id:
            params["userId"] = user_id
        if template_id:
            params["templateId"] = template_id
        if since:
            params["since"] = since.isoformat()
        return self._request("GET", "async/requests", params=params)
    
    def get_async_request_details(self, request_id: str) -> Dict[str, Any]:
        """
        Get detailed information about a specific async request.
        
        Args:
            request_id: Request UUID
        
        Returns:
            Async request details including metrics and error info
        """
        return self._request("GET", f"async/requests/{request_id}")
    
    def get_async_metrics(self) -> Dict[str, Any]:
        """
        Get async metrics dashboard (admin only).
        
        Returns:
            Queue depth, performance metrics, throughput, error rates
        """
        return self._request("GET", "async/metrics")
    
    def get_async_health(self) -> Dict[str, Any]:
        """
        Get async system health status (admin only).
        
        Returns:
            Health check for async components (ActiveMQ, queue depth, workers)
        """
        return self._request("GET", "async/health")
    
    def get_async_errors(
        self,
        since: Optional[datetime] = None,
        page: int = 1,
        size: int = 20
    ) -> Dict[str, Any]:
        """
        Get async error log (admin only).
        
        Args:
            since: Show errors since this timestamp (default: last 24 hours)
            page: Page number
            size: Items per page
        
        Returns:
            Paginated list of failed/timed-out async requests
        """
        params: Dict[str, Any] = {"page": page, "size": size}
        if since:
            params["since"] = since.isoformat()
        return self._request("GET", "async/errors", params=params)
    
    # ========== Configuration ==========
    
    def get_server_config(self) -> Dict[str, Any]:
        """Get server configuration (admin only)."""
        return self._request("GET", "config")
    
    def close(self) -> None:
        """Close the HTTP session."""
        if self._session:
            self._session.close()
            self._session = None
    
    def __enter__(self) -> "MubanAPIClient":
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()


# Convenience function for quick API access
def get_client(config: Optional[MubanConfig] = None) -> MubanAPIClient:
    """
    Get an API client instance.
    
    Args:
        config: Optional configuration
    
    Returns:
        MubanAPIClient instance
    """
    return MubanAPIClient(config)
