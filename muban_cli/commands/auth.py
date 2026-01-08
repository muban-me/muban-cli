"""
Authentication commands for Muban CLI.

Commands:
- login: Authenticate with credentials
- logout: Clear stored authentication
- whoami: Show authentication status
- refresh: Refresh access token
"""

import sys
import time
from typing import Optional

import click

from . import (
    MubanContext,
    pass_context,
    print_success,
    print_error,
    print_info,
)
from ..exceptions import AuthenticationError, MubanError
from ..utils import confirm_action


def register_auth_commands(cli: click.Group) -> None:
    """Register authentication commands with the CLI."""
    
    @cli.command('login')
    @click.option('--username', '-u', help='Username or email')
    @click.option('--password', '-p', help='Password (will prompt if not provided)')
    @click.option('--server', '-s', help='Server URL (overrides configured server)')
    @click.option('--auth-endpoint', help='Custom auth endpoint path (e.g., /oauth/token)')
    @pass_context
    def login(
        ctx: MubanContext,
        username: Optional[str],
        password: Optional[str],
        server: Optional[str],
        auth_endpoint: Optional[str]
    ):
        """
        Authenticate with username and password to obtain a token.
        
        \b
        Examples:
          muban login
          muban login --username admin@example.com
          muban login -u admin -p secret --server https://api.muban.me
        """
        from ..auth import MubanAuthClient
        
        config_manager = ctx.config_manager
        config = config_manager.get()
        
        # Override server if provided
        if server:
            config.server_url = server
        
        if not config.server_url:
            print_error(
                "Server URL not configured.",
                "Run 'muban configure --server URL' first."
            )
            sys.exit(1)
        
        # Prompt for credentials if not provided
        if not username:
            username = click.prompt("Username")
        
        if not password:
            password = click.prompt("Password", hide_input=True)
        
        # At this point username and password are guaranteed to be strings
        assert username is not None
        assert password is not None
        
        print_info(f"Authenticating to {config.get_auth_server_url()}...")
        
        try:
            with MubanAuthClient(config) as auth_client:
                result = auth_client.login(
                    username=username,
                    password=password,
                    auth_endpoint=auth_endpoint
                )
                
                # Save the token and refresh token
                token = result.get('access_token')
                if token:
                    update_data = {'token': token}
                    
                    # Save refresh token if provided
                    if result.get('refresh_token'):
                        update_data['refresh_token'] = result['refresh_token']
                    
                    # Calculate expiration time
                    if result.get('expires_in'):
                        update_data['token_expires_at'] = int(time.time()) + int(result['expires_in'])
                    
                    config_manager.update(**update_data)
                    print_success("Login successful! Token saved.")
                    
                    if result.get('expires_in'):
                        click.echo(f"  Token expires in: {result['expires_in']} seconds")
                    if result.get('refresh_token'):
                        click.echo("  Refresh token saved for automatic renewal.")
                else:
                    print_error("Login succeeded but no token received.")
                    sys.exit(1)
                    
        except AuthenticationError as e:
            print_error(f"Login failed: {e}")
            sys.exit(1)
        except MubanError as e:
            print_error(str(e))
            sys.exit(1)

    @cli.command('logout')
    @click.option('--yes', '-y', is_flag=True, help='Skip confirmation')
    @pass_context
    def logout(ctx: MubanContext, yes: bool):
        """
        Clear stored authentication token.
        """
        if not yes:
            if not confirm_action("Clear stored authentication token?"):
                print_info("Cancelled.")
                return
        
        config_manager = ctx.config_manager
        config_manager.update(token='', refresh_token='', token_expires_at=0)
        print_success("Logged out successfully.")

    @cli.command('refresh')
    @click.option('--auth-endpoint', help='Custom auth endpoint path')
    @pass_context
    def refresh(ctx: MubanContext, auth_endpoint: Optional[str]):
        """
        Refresh the access token using the stored refresh token.
        
        \b
        Examples:
          muban refresh
          muban refresh --auth-endpoint /oauth/token
        """
        from ..auth import MubanAuthClient
        
        config_manager = ctx.config_manager
        config = config_manager.get()
        
        if not config.has_refresh_token():
            print_error(
                "No refresh token available.",
                "Run 'muban login' to authenticate."
            )
            sys.exit(1)
        
        print_info("Refreshing access token...")
        
        try:
            with MubanAuthClient(config) as auth_client:
                result = auth_client.refresh_token(
                    refresh_token=config.refresh_token,
                    auth_endpoint=auth_endpoint
                )
                
                token = result.get('access_token')
                if token:
                    update_data = {'token': token}
                    
                    # Update refresh token if a new one is provided
                    if result.get('refresh_token'):
                        update_data['refresh_token'] = result['refresh_token']
                    
                    # Update expiration time
                    if result.get('expires_in'):
                        update_data['token_expires_at'] = int(time.time()) + int(result['expires_in'])
                    
                    config_manager.update(**update_data)
                    print_success("Token refreshed successfully!")
                    
                    if result.get('expires_in'):
                        click.echo(f"  Token expires in: {result['expires_in']} seconds")
                else:
                    print_error("Refresh succeeded but no token received.")
                    sys.exit(1)
                    
        except AuthenticationError as e:
            print_error(
                f"Token refresh failed: {e}",
                "Your session may have expired. Run 'muban login' to re-authenticate."
            )
            sys.exit(1)
        except MubanError as e:
            print_error(str(e))
            sys.exit(1)

    @cli.command('whoami')
    @pass_context
    def whoami(ctx: MubanContext):
        """
        Show current authentication status.
        """
        config = ctx.config_manager.get()
        
        if config.is_configured():
            click.echo("\nAuthentication Status: " + click.style("Authenticated", fg="green"))
            click.echo(f"  Server: {config.server_url}")
            click.echo(f"  Token:  {config.token[:20]}...{config.token[-10:]}" if len(config.token) > 30 else f"  Token: {config.token}")
            
            # Show token expiration status
            if config.token_expires_at:
                remaining = config.token_expires_at - int(time.time())
                if remaining > 0:
                    hours, remainder = divmod(remaining, 3600)
                    minutes, seconds = divmod(remainder, 60)
                    if hours > 0:
                        click.echo(f"  Expires: in {hours}h {minutes}m {seconds}s")
                    elif minutes > 0:
                        click.echo(f"  Expires: in {minutes}m {seconds}s")
                    else:
                        click.echo(f"  Expires: in {seconds}s " + click.style("(expiring soon!)", fg="yellow"))
                else:
                    click.echo("  Expires: " + click.style("EXPIRED", fg="red"))
                    if config.has_refresh_token():
                        print_info("Run 'muban refresh' to get a new token.")
                    else:
                        print_info("Run 'muban login' to re-authenticate.")
            
            # Show refresh token availability
            if config.has_refresh_token():
                click.echo("  Refresh: " + click.style("available", fg="green"))
            else:
                click.echo("  Refresh: " + click.style("not available", fg="yellow"))
        else:
            click.echo("\nAuthentication Status: " + click.style("Not authenticated", fg="red"))
            click.echo(f"  Server: {config.server_url or '(not configured)'}")
            print_info("Run 'muban login' to authenticate.")
