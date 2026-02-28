"""
Muban API Client Package.

This package provides a modular API client for the Muban Document Generation Service.

Structure:
    - client.py: Main MubanAPIClient facade (backward-compatible)
    - _http.py: Base HTTP client with session, auth, and error handling
    - templates.py: Template management and document generation
    - users.py: User management
    - audit.py: Audit log operations
    - admin.py: Administrative operations
    - async_ops.py: Asynchronous operations

Usage:
    from muban_cli.api import MubanAPIClient, get_client
    
    # Create client
    client = MubanAPIClient()
    
    # New style (domain-specific)
    templates = client.templates.list()
    user = client.users.get_current()
    
    # Legacy style (backward-compatible flat methods)
    templates = client.list_templates()
    user = client.get_current_user()
"""

from .client import MubanAPIClient, get_client
from ._http import HTTPClient
from .templates import TemplatesAPI
from .users import UsersAPI
from .audit import AuditAPI
from .admin import AdminAPI
from .async_ops import AsyncOpsAPI

__all__ = [
    # Main client
    "MubanAPIClient",
    "get_client",
    # HTTP layer
    "HTTPClient",
    # Domain APIs
    "TemplatesAPI",
    "UsersAPI",
    "AuditAPI",
    "AdminAPI",
    "AsyncOpsAPI",
]
