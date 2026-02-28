"""
API client for Muban Document Generation Service.

This module re-exports from the new modular api/ package for backward compatibility.

For new code, prefer importing from muban_cli.api directly:
    from muban_cli.api import MubanAPIClient, get_client
"""

# Re-export everything from the new modular package
from .api import (
    MubanAPIClient,
    get_client,
    HTTPClient,
    TemplatesAPI,
    UsersAPI,
    AuditAPI,
    AdminAPI,
    AsyncOpsAPI,
)

__all__ = [
    "MubanAPIClient",
    "get_client",
    "HTTPClient",
    "TemplatesAPI",
    "UsersAPI",
    "AuditAPI",
    "AdminAPI",
    "AsyncOpsAPI",
]
