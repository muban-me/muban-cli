"""
Audit API - Audit log operations.
"""

from datetime import datetime
from typing import Optional, Dict, Any

from ._http import HTTPClient


class AuditAPI:
    """
    API for audit log operations.
    
    Handles:
    - Audit log listing and filtering
    - Statistics and analytics
    - Security events
    - Dashboard data
    """
    
    def __init__(self, http: HTTPClient):
        """
        Initialize Audit API.
        
        Args:
            http: HTTP client instance
        """
        self._http = http
    
    def get_logs(
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
        
        return self._http.request("GET", "audit/logs", params=params)
    
    def get_log(self, log_id: str) -> Dict[str, Any]:
        """Get specific audit log entry (admin only)."""
        return self._http.request("GET", f"audit/logs/{log_id}")
    
    def get_statistics(
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
        
        return self._http.request("GET", "audit/statistics", params=params)
    
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
        
        return self._http.request("GET", "audit/security", params=params)
    
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
        
        return self._http.request("GET", "audit/failures", params=params)
    
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
        
        return self._http.request("GET", f"audit/users/{user_id}", params=params)
    
    def get_event_types(self) -> Dict[str, Any]:
        """Get available audit event types."""
        return self._http.request("GET", "audit/event-types")
    
    def get_severity_levels(self) -> Dict[str, Any]:
        """Get available severity levels."""
        return self._http.request("GET", "audit/severity-levels")
    
    def get_health(self) -> Dict[str, Any]:
        """Check audit system health."""
        return self._http.request("GET", "audit/health")
    
    def cleanup(self) -> Dict[str, Any]:
        """Trigger audit log cleanup (admin only)."""
        return self._http.request("POST", "audit/cleanup")
    
    # Dashboard methods
    
    def get_dashboard_overview(self) -> Dict[str, Any]:
        """Get audit dashboard overview (admin only)."""
        return self._http.request("GET", "audit/dashboard/overview")
    
    def get_security_threats(self) -> Dict[str, Any]:
        """Get security threats summary (admin only)."""
        return self._http.request("GET", "audit/dashboard/security-threats")
    
    def get_system_health_metrics(self) -> Dict[str, Any]:
        """Get system health metrics (admin only)."""
        return self._http.request("GET", "audit/dashboard/system-health")
    
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
        
        return self._http.request("GET", "audit/dashboard/user-patterns", params=params)
    
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
        
        return self._http.request("GET", "audit/dashboard/compliance", params=params)
