"""
Async Operations API - Asynchronous document generation.
"""

from datetime import datetime
from typing import Optional, Dict, Any, List

from ._http import HTTPClient


class AsyncOpsAPI:
    """
    API for asynchronous operations.
    
    Handles:
    - Bulk async document generation
    - Request tracking
    - Worker management
    - Metrics and health
    """
    
    def __init__(self, http: HTTPClient):
        """
        Initialize Async Operations API.
        
        Args:
            http: HTTP client instance
        """
        self._http = http
    
    def submit_bulk(
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
        return self._http.request("POST", "async/bulk", json_data=payload)
    
    def get_workers(self) -> Dict[str, Any]:
        """Get worker thread status (admin only)."""
        return self._http.request("GET", "async/workers")
    
    def get_requests(
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
        return self._http.request("GET", "async/requests", params=params)
    
    def get_request_details(self, request_id: str) -> Dict[str, Any]:
        """
        Get detailed information about a specific async request.
        
        Args:
            request_id: Request UUID
        
        Returns:
            Async request details including metrics and error info
        """
        return self._http.request("GET", f"async/requests/{request_id}")
    
    def get_metrics(self) -> Dict[str, Any]:
        """
        Get async metrics dashboard (admin only).
        
        Returns:
            Queue depth, performance metrics, throughput, error rates
        """
        return self._http.request("GET", "async/metrics")
    
    def get_health(self) -> Dict[str, Any]:
        """
        Get async system health status (admin only).
        
        Returns:
            Health check for async components (ActiveMQ, queue depth, workers)
        """
        return self._http.request("GET", "async/health")
    
    def get_errors(
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
        return self._http.request("GET", "async/errors", params=params)
