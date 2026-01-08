"""
Muban CLI Commands Package.

This package contains all CLI command modules organized by API endpoint:
- auth: Authentication commands (login, logout, whoami, refresh)
- settings: Configuration commands (configure, config-clear)
- templates: Template management commands (list, get, push, pull, delete, search)
- generate: Document generation commands
- resources: Resource commands (fonts, icc-profiles)
- admin: Administrative commands
- audit: Audit log commands
- users: User management commands
"""

import sys
import logging
from typing import Optional
from functools import wraps

import click

from ..config import ConfigManager, get_config_manager
from ..api import MubanAPIClient
from ..utils import (
    setup_logging,
    print_success,
    print_error,
    print_info,
    print_json,
    print_table,
    OutputFormat,
    format_audit_logs,
)

logger = logging.getLogger(__name__)


# ============================================================================
# CLI Context
# ============================================================================

class MubanContext:
    """CLI context object for sharing state between commands."""
    
    def __init__(self):
        self.config_manager: ConfigManager = None  # type: ignore[assignment]
        self.client: Optional[MubanAPIClient] = None
        self.verbose: bool = False
        self.quiet: bool = False
        self.output_format: OutputFormat = OutputFormat.TABLE


pass_context = click.make_pass_decorator(MubanContext, ensure=True)


# ============================================================================
# Common Decorators
# ============================================================================

def common_options(f):
    """Common options for all commands."""
    f = click.option(
        '-v', '--verbose',
        is_flag=True,
        help='Enable verbose output'
    )(f)
    f = click.option(
        '-q', '--quiet',
        is_flag=True,
        help='Suppress non-essential output'
    )(f)
    f = click.option(
        '-f', '--format',
        'output_format',
        type=click.Choice(['table', 'json']),
        default='table',
        help='Output format'
    )(f)
    return f


def require_config(f):
    """Decorator to require valid configuration."""
    @click.pass_context
    @wraps(f)
    def wrapper(click_ctx, *args, **kwargs):
        ctx = click_ctx.ensure_object(MubanContext)
        config = ctx.config_manager.get()
        
        if not config.is_configured():
            print_error(
                "Muban CLI is not authenticated.",
                "Run 'muban login' to authenticate with your credentials."
            )
            sys.exit(1)
        
        return click_ctx.invoke(f, *args, **kwargs)
    
    return wrapper


# ============================================================================
# Exports
# ============================================================================

__all__ = [
    'MubanContext',
    'pass_context',
    'common_options',
    'require_config',
    'setup_logging',
    'print_success',
    'print_error',
    'print_info',
    'print_json',
    'print_table',
    'format_audit_logs',
    'logger',
]
