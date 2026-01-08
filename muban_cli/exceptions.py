"""
Custom exceptions for Muban CLI.
"""

from typing import Optional, Dict, Any


class MubanError(Exception):
    """Base exception for Muban CLI errors."""
    
    def __init__(self, message: str, details: Optional[str] = None):
        super().__init__(message)
        self.message = message
        self.details = details


class ConfigurationError(MubanError):
    """Raised when configuration is invalid or missing."""
    pass


class AuthenticationError(MubanError):
    """Raised when authentication fails."""
    pass


class APIError(MubanError):
    """Raised when API request fails."""
    
    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        response_data: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message)
        self.status_code = status_code
        self.response_data = response_data or {}


class ValidationError(MubanError):
    """Raised when input validation fails."""
    pass


class TemplateNotFoundError(APIError):
    """Raised when template is not found."""
    pass


class PermissionDeniedError(APIError):
    """Raised when user lacks required permissions."""
    pass
