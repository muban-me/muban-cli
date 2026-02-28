"""
Users API - User management operations.
"""

from typing import Optional, Dict, Any, List

from ._http import HTTPClient


class UsersAPI:
    """
    API for user management operations.
    
    Handles:
    - Current user profile
    - User CRUD (admin)
    - Role management
    - Password changes
    """
    
    def __init__(self, http: HTTPClient):
        """
        Initialize Users API.
        
        Args:
            http: HTTP client instance
        """
        self._http = http
    
    def get_current(self) -> Dict[str, Any]:
        """Get current authenticated user profile."""
        return self._http.request("GET", "users/me")
    
    def update_current(
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
        
        return self._http.request("PUT", "users/me", json_data=data)
    
    def change_current_password(
        self,
        current_password: str,
        new_password: str
    ) -> Dict[str, Any]:
        """Change current user's password."""
        return self._http.request(
            "PUT",
            "users/me/password",
            json_data={
                "currentPassword": current_password,
                "newPassword": new_password
            }
        )
    
    def list(
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
        
        return self._http.request("GET", "users", params=params)
    
    def get(self, user_id: str) -> Dict[str, Any]:
        """Get user by ID (admin or own profile)."""
        return self._http.request("GET", f"users/{user_id}")
    
    def create(
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
        
        return self._http.request("POST", "users", json_data=data, expected_status=201)
    
    def update(
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
        
        return self._http.request("PUT", f"users/{user_id}", json_data=data)
    
    def delete(self, user_id: str) -> Dict[str, Any]:
        """Delete user (admin only, cannot delete own account)."""
        return self._http.request("DELETE", f"users/{user_id}", expected_status=204)
    
    def update_roles(
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
        return self._http.request(
            "PUT",
            f"users/{user_id}/roles",
            json_data={"roles": roles}
        )
    
    def change_password(
        self,
        user_id: str,
        current_password: str,
        new_password: str
    ) -> Dict[str, Any]:
        """Change user password (admin or own password)."""
        return self._http.request(
            "PUT",
            f"users/{user_id}/password",
            json_data={
                "currentPassword": current_password,
                "newPassword": new_password
            }
        )
    
    def enable(self, user_id: str) -> Dict[str, Any]:
        """Enable user account (admin only)."""
        return self._http.request("PUT", f"users/{user_id}", json_data={"enabled": True})
    
    def disable(self, user_id: str) -> Dict[str, Any]:
        """Disable user account (admin only)."""
        return self._http.request("PUT", f"users/{user_id}", json_data={"enabled": False})
