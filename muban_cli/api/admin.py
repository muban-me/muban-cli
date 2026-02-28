"""
Admin API - Administrative operations.
"""

from typing import Dict, Any

from ._http import HTTPClient


class AdminAPI:
    """
    API for administrative operations.
    
    Handles:
    - Template integrity verification
    - Digest regeneration
    - Server configuration
    """
    
    def __init__(self, http: HTTPClient):
        """
        Initialize Admin API.
        
        Args:
            http: HTTP client instance
        """
        self._http = http
    
    def verify_template_integrity(self, template_id: str) -> Dict[str, Any]:
        """
        Verify template integrity (admin only).
        
        Args:
            template_id: Template UUID
        
        Returns:
            Verification result
        """
        return self._http.request(
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
        return self._http.request("POST", f"admin/templates/{template_id}/regenerate-digest")
    
    def regenerate_all_digests(self) -> Dict[str, Any]:
        """
        Regenerate all template digests (admin only).
        
        Returns:
            Regeneration results
        """
        return self._http.request(
            "POST",
            "admin/templates/regenerate-all-digests",
            expected_status=[200, 207, 500]
        )
    
    def get_server_config(self) -> Dict[str, Any]:
        """Get server configuration (admin only)."""
        return self._http.request("GET", "config")
