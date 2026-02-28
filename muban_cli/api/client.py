"""
Muban API Client - Main facade for all API operations.

This module provides backward-compatible access to all API endpoints while
organizing functionality into domain-specific modules.
"""

from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List

from ..config import MubanConfig, get_config
from ._http import HTTPClient
from .templates import TemplatesAPI
from .users import UsersAPI
from .audit import AuditAPI
from .admin import AdminAPI
from .async_ops import AsyncOpsAPI


class MubanAPIClient:
    """
    Client for interacting with the Muban Document Generation Service API.
    
    This is a facade that provides both:
    - Domain-specific sub-clients (client.templates, client.users, etc.)
    - Backward-compatible flat methods (client.list_templates(), etc.)
    
    Usage (new style):
        client = MubanAPIClient()
        templates = client.templates.list()
        user = client.users.get_current()
    
    Usage (backward-compatible):
        client = MubanAPIClient()
        templates = client.list_templates()
        user = client.get_current_user()
    """
    
    API_VERSION = "v1"
    
    def __init__(self, config: Optional[MubanConfig] = None):
        """
        Initialize the API client.
        
        Args:
            config: Optional configuration. Uses global config if not provided.
        """
        self._http = HTTPClient(config)
        
        # Domain-specific API modules
        self.templates = TemplatesAPI(self._http)
        self.users = UsersAPI(self._http)
        self.audit = AuditAPI(self._http)
        self.admin = AdminAPI(self._http)
        self.async_ops = AsyncOpsAPI(self._http)
    
    @property
    def config(self) -> MubanConfig:
        """Get the configuration."""
        return self._http.config
    
    @property
    def base_url(self) -> str:
        """Get the base URL for API requests."""
        return self._http.base_url
    
    # ========== Backward-Compatible Template Methods ==========
    
    def list_templates(
        self,
        page: int = 1,
        size: int = 20,
        search: Optional[str] = None,
        description: Optional[str] = None,
        sort_by: Optional[str] = None,
        sort_dir: Optional[str] = None
    ) -> Dict[str, Any]:
        """List templates with pagination."""
        return self.templates.list(page, size, search, description, sort_by, sort_dir)
    
    def get_template(self, template_id: str) -> Dict[str, Any]:
        """Get template details."""
        return self.templates.get(template_id)
    
    def get_template_parameters(self, template_id: str) -> Dict[str, Any]:
        """Get template parameters."""
        return self.templates.get_parameters(template_id)
    
    def get_template_fields(self, template_id: str) -> Dict[str, Any]:
        """Get template fields."""
        return self.templates.get_fields(template_id)
    
    def upload_template(
        self,
        file_path: Path,
        name: str,
        author: str,
        description: Optional[str] = None,
        metadata: Optional[str] = None
    ) -> Dict[str, Any]:
        """Upload a new template."""
        return self.templates.upload(file_path, name, author, description, metadata)
    
    def download_template(
        self,
        template_id: str,
        output_path: Optional[Path] = None
    ) -> Path:
        """Download a template."""
        return self.templates.download(template_id, output_path)
    
    def delete_template(self, template_id: str) -> Dict[str, Any]:
        """Delete a template."""
        return self.templates.delete(template_id)
    
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
        txt_export_options: Optional[Dict[str, Any]] = None,
        ignore_pagination: bool = False
    ) -> Path:
        """Generate a document from a template."""
        return self.templates.generate(
            template_id, output_format, parameters, output_path, filename,
            data, document_locale, pdf_export_options, html_export_options,
            txt_export_options, ignore_pagination
        )
    
    def generate_document_raw(
        self,
        template_id: str,
        output_format: str,
        request_data: Dict[str, Any],
        output_path: Optional[Path] = None
    ) -> Path:
        """Generate a document with a raw request body."""
        return self.templates.generate_raw(template_id, output_format, request_data, output_path)
    
    def get_fonts(self) -> Dict[str, Any]:
        """Get available fonts."""
        return self.templates.get_fonts()
    
    def get_icc_profiles(self) -> Dict[str, Any]:
        """Get available ICC profiles."""
        return self.templates.get_icc_profiles()
    
    # ========== Backward-Compatible Admin Methods ==========
    
    def verify_template_integrity(self, template_id: str) -> Dict[str, Any]:
        """Verify template integrity (admin only)."""
        return self.admin.verify_template_integrity(template_id)
    
    def regenerate_template_digest(self, template_id: str) -> Dict[str, Any]:
        """Regenerate template digest (admin only)."""
        return self.admin.regenerate_template_digest(template_id)
    
    def regenerate_all_digests(self) -> Dict[str, Any]:
        """Regenerate all template digests (admin only)."""
        return self.admin.regenerate_all_digests()
    
    def get_server_config(self) -> Dict[str, Any]:
        """Get server configuration (admin only)."""
        return self.admin.get_server_config()
    
    # ========== Backward-Compatible Audit Methods ==========
    
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
        """Get audit logs with filtering (admin only)."""
        return self.audit.get_logs(
            page, size, event_type, severity, user_id,
            ip_address, start_time, end_time, success
        )
    
    def get_audit_log(self, log_id: str) -> Dict[str, Any]:
        """Get specific audit log entry (admin only)."""
        return self.audit.get_log(log_id)
    
    def get_audit_statistics(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Get audit statistics (admin only)."""
        return self.audit.get_statistics(start_time, end_time)
    
    def get_security_events(
        self,
        page: int = 1,
        size: int = 50,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Get security events (admin only)."""
        return self.audit.get_security_events(page, size, start_time, end_time)
    
    def get_failed_operations(
        self,
        page: int = 1,
        size: int = 50,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Get failed operations (admin only)."""
        return self.audit.get_failed_operations(page, size, start_time, end_time)
    
    def get_user_activity(
        self,
        user_id: str,
        page: int = 1,
        size: int = 50,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Get audit logs for specific user (admin only)."""
        return self.audit.get_user_activity(user_id, page, size, start_time, end_time)
    
    def get_event_types(self) -> Dict[str, Any]:
        """Get available audit event types."""
        return self.audit.get_event_types()
    
    def get_severity_levels(self) -> Dict[str, Any]:
        """Get available severity levels."""
        return self.audit.get_severity_levels()
    
    def get_audit_health(self) -> Dict[str, Any]:
        """Check audit system health."""
        return self.audit.get_health()
    
    def cleanup_audit_logs(self) -> Dict[str, Any]:
        """Trigger audit log cleanup (admin only)."""
        return self.audit.cleanup()
    
    def get_dashboard_overview(self) -> Dict[str, Any]:
        """Get audit dashboard overview (admin only)."""
        return self.audit.get_dashboard_overview()
    
    def get_security_threats(self) -> Dict[str, Any]:
        """Get security threats summary (admin only)."""
        return self.audit.get_security_threats()
    
    def get_system_health_metrics(self) -> Dict[str, Any]:
        """Get system health metrics (admin only)."""
        return self.audit.get_system_health_metrics()
    
    def get_user_activity_patterns(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Get user activity patterns (admin only)."""
        return self.audit.get_user_activity_patterns(start_time, end_time)
    
    def get_compliance_activity(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Get compliance activity dashboard (admin only)."""
        return self.audit.get_compliance_activity(start_time, end_time)
    
    # ========== Backward-Compatible User Methods ==========
    
    def get_current_user(self) -> Dict[str, Any]:
        """Get current authenticated user profile."""
        return self.users.get_current()
    
    def update_current_user(
        self,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        email: Optional[str] = None
    ) -> Dict[str, Any]:
        """Update current user profile."""
        return self.users.update_current(first_name, last_name, email)
    
    def change_current_user_password(
        self,
        current_password: str,
        new_password: str
    ) -> Dict[str, Any]:
        """Change current user's password."""
        return self.users.change_current_password(current_password, new_password)
    
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
        """List users (admin only)."""
        return self.users.list(page, size, search, role, enabled, sort_by, sort_dir)
    
    def get_user(self, user_id: str) -> Dict[str, Any]:
        """Get user by ID (admin or own profile)."""
        return self.users.get(user_id)
    
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
        """Create new user (admin only)."""
        return self.users.create(username, email, password, first_name, last_name, roles, enabled)
    
    def update_user(
        self,
        user_id: str,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        email: Optional[str] = None
    ) -> Dict[str, Any]:
        """Update user profile (admin or own profile)."""
        return self.users.update(user_id, first_name, last_name, email)
    
    def delete_user(self, user_id: str) -> Dict[str, Any]:
        """Delete user (admin only, cannot delete own account)."""
        return self.users.delete(user_id)
    
    def update_user_roles(
        self,
        user_id: str,
        roles: List[str]
    ) -> Dict[str, Any]:
        """Update user roles (admin only)."""
        return self.users.update_roles(user_id, roles)
    
    def change_user_password(
        self,
        user_id: str,
        current_password: str,
        new_password: str
    ) -> Dict[str, Any]:
        """Change user password (admin or own password)."""
        return self.users.change_password(user_id, current_password, new_password)
    
    def enable_user(self, user_id: str) -> Dict[str, Any]:
        """Enable user account (admin only)."""
        return self.users.enable(user_id)
    
    def disable_user(self, user_id: str) -> Dict[str, Any]:
        """Disable user account (admin only)."""
        return self.users.disable(user_id)
    
    # ========== Backward-Compatible Async Methods ==========
    
    def submit_bulk_async(
        self,
        requests: List[Dict[str, Any]],
        batch_correlation_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Submit bulk async document generation requests."""
        return self.async_ops.submit_bulk(requests, batch_correlation_id)
    
    def get_async_workers(self) -> Dict[str, Any]:
        """Get worker thread status (admin only)."""
        return self.async_ops.get_workers()
    
    def get_async_requests(
        self,
        status: Optional[str] = None,
        user_id: Optional[str] = None,
        template_id: Optional[str] = None,
        since: Optional[datetime] = None,
        page: int = 1,
        size: int = 20
    ) -> Dict[str, Any]:
        """Get paginated list of async requests."""
        return self.async_ops.get_requests(status, user_id, template_id, since, page, size)
    
    def get_async_request_details(self, request_id: str) -> Dict[str, Any]:
        """Get detailed information about a specific async request."""
        return self.async_ops.get_request_details(request_id)
    
    def get_async_metrics(self) -> Dict[str, Any]:
        """Get async metrics dashboard (admin only)."""
        return self.async_ops.get_metrics()
    
    def get_async_health(self) -> Dict[str, Any]:
        """Get async system health status (admin only)."""
        return self.async_ops.get_health()
    
    def get_async_errors(
        self,
        since: Optional[datetime] = None,
        page: int = 1,
        size: int = 20
    ) -> Dict[str, Any]:
        """Get async error log (admin only)."""
        return self.async_ops.get_errors(since, page, size)
    
    # ========== Context Manager ==========
    
    def close(self) -> None:
        """Close the HTTP session."""
        self._http.close()
    
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
