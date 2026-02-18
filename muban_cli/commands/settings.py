"""
Configuration/settings commands for Muban CLI.

Commands:
- configure: Configure CLI settings
- config-clear: Clear all configuration
"""

from typing import Optional

import click

from .. import __prog_name__
from . import (
    MubanContext,
    pass_context,
    print_success,
    print_info,
)
from ..config import DEFAULT_SERVER_URL


def register_settings_commands(cli: click.Group) -> None:
    """Register configuration commands with the CLI."""
    
    @cli.command('configure')
    @click.option(
        '--server', '-s',
        help=f'API server URL (default: {DEFAULT_SERVER_URL})'
    )
    @click.option(
        '--auth-server',
        help='Auth server URL (if different from API server)'
    )
    @click.option(
        '--client-id',
        help='OAuth2 Client ID for client credentials authentication'
    )
    @click.option(
        '--client-secret',
        help='OAuth2 Client Secret for client credentials authentication'
    )
    @click.option(
        '--timeout', '-t',
        type=int,
        help='Request timeout in seconds'
    )
    @click.option(
        '--max-retries',
        type=int,
        help='Max retries for transient errors (0 to disable)'
    )
    @click.option(
        '--no-verify-ssl',
        is_flag=True,
        help='Disable SSL certificate verification'
    )
    @click.option(
        '--author', '-a',
        help='Default author name for template uploads'
    )
    @click.option(
        '--auto-upload/--no-auto-upload',
        default=None,
        help='Auto-upload packages after creation'
    )
    @click.option(
        '--show',
        is_flag=True,
        help='Show current configuration'
    )
    @pass_context
    def configure(
        ctx: MubanContext,
        server: Optional[str],
        auth_server: Optional[str],
        client_id: Optional[str],
        client_secret: Optional[str],
        timeout: Optional[int],
        max_retries: Optional[int],
        no_verify_ssl: bool,
        author: Optional[str],
        auto_upload: Optional[bool],
        show: bool
    ):
        """
        Configure Muban CLI settings.
        
        \b
        Examples:
          muban configure --server https://api.muban.me
          muban configure --auth-server https://auth.muban.me
          muban configure --client-id MY_ID --client-secret MY_SECRET
          muban configure --show
        """
        config_manager = ctx.config_manager
        
        if show:
            config = config_manager.get()
            click.echo("\nCurrent Configuration:")
            click.echo(f"  Server URL:      {config.server_url}")
            click.echo(f"  Auth Server:     {config.auth_server_url or '(same as server)'}")
            click.echo(f"  Client ID:       {config.client_id or '(not configured)'}")
            click.echo(f"  Client Secret:   {'*' * 10 + '...' if config.client_secret else '(not configured)'}")
            click.echo(f"  Token:           {'*' * 20 + '...' if config.token else '(not authenticated)'}")
            click.echo(f"  Timeout:         {config.timeout}s")
            click.echo(f"  Max Retries:     {config.max_retries}")
            click.echo(f"  Verify SSL:      {config.verify_ssl}")
            click.echo(f"  Default Author:  {config.default_author or '(not set)'}")
            click.echo(f"  Auto-upload:     {config.auto_upload_on_package}")
            click.echo(f"  Config Path:     {config_manager.get_config_path()}")
            return
        
        # Interactive configuration if no options provided
        if not any([server, auth_server, client_id, client_secret, timeout, max_retries is not None, no_verify_ssl, author, auto_upload is not None]):
            click.echo("Interactive configuration setup:")
            
            current = config_manager.get()
            
            server = click.prompt(
                "API Server URL",
                default=current.server_url or DEFAULT_SERVER_URL
            )
            
            auth_server = click.prompt(
                "Auth Server URL (leave empty if same as API server)",
                default=current.auth_server_url or '',
                show_default=False
            )
            
            timeout = click.prompt(
                "Request timeout (seconds)",
                default=current.timeout,
                type=int
            )
            
            max_retries = click.prompt(
                "Max retries for transient errors (0 to disable)",
                default=current.max_retries,
                type=int
            )
            
            author = click.prompt(
                "Default author for template uploads (leave empty for none)",
                default=current.default_author or '',
                show_default=False
            )
        
        # Update configuration
        updates = {}
        if server:
            updates['server_url'] = server
        if auth_server:
            updates['auth_server_url'] = auth_server
        if client_id:
            updates['client_id'] = client_id
        if client_secret:
            updates['client_secret'] = client_secret
        if timeout:
            updates['timeout'] = timeout
        if max_retries is not None:
            updates['max_retries'] = max_retries
        if no_verify_ssl:
            updates['verify_ssl'] = False
        if author is not None:
            updates['default_author'] = author
        if auto_upload is not None:
            updates['auto_upload_on_package'] = auto_upload
        
        if updates:
            config_manager.update(**updates)
            print_success("Configuration saved successfully.")
            if client_id and client_secret:
                print_info(f"Run '{__prog_name__} login --client-credentials' to authenticate.")
            else:
                print_info(f"Run '{__prog_name__} login' to authenticate with your credentials.")
        else:
            print_info("No changes made.")

    @cli.command('config-clear')
    @click.confirmation_option(prompt='Are you sure you want to clear all configuration?')
    @pass_context
    def config_clear(ctx: MubanContext):
        """Clear all stored configuration."""
        ctx.config_manager.clear()
        print_success("Configuration cleared.")
