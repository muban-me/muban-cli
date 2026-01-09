"""
Muban CLI - Command Line Interface for Muban Document Generation Service.

This module provides the main CLI entry point and orchestrates all command modules.
Commands are organized by API endpoint:
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
from pathlib import Path
from typing import Optional

import click

from . import __version__, __prog_name__
from .config import get_config_manager

# Import command registration functions
from .commands import MubanContext
from .commands.auth import register_auth_commands
from .commands.settings import register_settings_commands
from .commands.templates import register_template_commands
from .commands.generate import register_generate_commands
from .commands.resources import register_resource_commands
from .commands.admin import register_admin_commands
from .commands.audit import register_audit_commands
from .commands.users import register_user_commands

logger = logging.getLogger(__name__)


# ============================================================================
# Main CLI Group
# ============================================================================

CLI_HELP = f"""
Muban CLI - Document Generation Service Management Tool.

A command-line interface for managing JasperReports templates
and generating documents through the Muban API.

\b
Quick Start:
  1. Configure server:         {__prog_name__} configure --server https://api.muban.me
  2. Login with credentials:   {__prog_name__} login
  3. List templates:           {__prog_name__} list
  4. Generate a document:      {__prog_name__} generate TEMPLATE_ID -p title=Report

\b
Service Account / CI-CD (with external IdP like ADFS, Azure AD, Keycloak):
  1. Configure:                {__prog_name__} configure --server https://api.muban.me \\
                                 --auth-server https://adfs.company.com/adfs/oauth2/token \\
                                 --client-id ID --client-secret SECRET
  2. Login:                    {__prog_name__} login --client-credentials

\b
Environment Variables:
  MUBAN_SERVER_URL      - API server URL (default: https://api.muban.me)
  MUBAN_AUTH_SERVER_URL - OAuth2/IdP token endpoint (if different from API)
  MUBAN_CLIENT_ID       - OAuth2 Client ID (for client credentials flow)
  MUBAN_CLIENT_SECRET   - OAuth2 Client Secret (for client credentials flow)
  MUBAN_TOKEN           - JWT Bearer token (skip login, use directly)
  MUBAN_VERIFY_SSL      - Set to 'false' to skip SSL verification (dev only)
  MUBAN_CONFIG_DIR      - Custom configuration directory
"""


@click.group(help=CLI_HELP)
@click.version_option(version=__version__, prog_name=__prog_name__)
@click.option(
    '--config-dir',
    type=click.Path(path_type=Path),
    envvar='MUBAN_CONFIG_DIR',
    help='Custom configuration directory'
)
@click.pass_context
def cli(ctx, config_dir: Optional[Path]):
    """Main CLI entry point."""
    ctx.ensure_object(MubanContext)
    ctx.obj.config_manager = get_config_manager(config_dir)


# ============================================================================
# Register All Commands
# ============================================================================

# Register commands from each module
register_settings_commands(cli)
register_auth_commands(cli)
register_template_commands(cli)
register_generate_commands(cli)
register_resource_commands(cli)
register_admin_commands(cli)
register_audit_commands(cli)
register_user_commands(cli)


# ============================================================================
# Entry Point
# ============================================================================

def main():
    """Main entry point for the CLI."""
    try:
        cli(auto_envvar_prefix='MUBAN')
    except KeyboardInterrupt:
        click.echo("\nAborted.")
        sys.exit(130)
    except Exception as e:
        logger.exception("Unexpected error")
        from .utils import print_error
        print_error(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
