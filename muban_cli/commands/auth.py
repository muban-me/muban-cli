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

from .. import __prog_name__
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
    @click.option('--username', '-u', help='Username or email (for password grant)')
    @click.option('--password', '-p', help='Password (will prompt if not provided)')
    @click.option('--client-credentials', '-c', is_flag=True,
                  help='Use OAuth2 client credentials flow (for service accounts)')
    @click.option('--client-id', help='OAuth2 Client ID (overrides configured)')
    @click.option('--client-secret', help='OAuth2 Client Secret (overrides configured)')
    @click.option('--scope', help='OAuth2 scope to request (space-separated)')
    @click.option('--server', '-s', help='Server URL (overrides configured server)')
    @click.option('--auth-endpoint', help='Custom auth endpoint path (e.g., /oauth/token)')
    @click.option('--no-verify-ssl', '-k', is_flag=True,
                  help='Skip SSL certificate verification (for development)')
    @pass_context
    def login(
        ctx: MubanContext,
        username: Optional[str],
        password: Optional[str],
        client_credentials: bool,
        client_id: Optional[str],
        client_secret: Optional[str],
        scope: Optional[str],
        server: Optional[str],
        auth_endpoint: Optional[str],
        no_verify_ssl: bool
    ):
        """
        Authenticate to obtain an access token.
        
        Supports two authentication methods:
        
        \b
        1. Password Grant (default):
           Interactive login with username and password.
        
        \b
        2. Client Credentials Grant (--client-credentials):
           For service accounts, CI/CD pipelines, and automation.
           Uses client_id and client_secret instead of user credentials.
        
        \b
        Examples:
          muban login                              # Interactive password login
          muban login --username admin@example.com
          muban login --client-credentials         # Use stored client credentials
          muban login -c --client-id ID --client-secret SECRET
          muban login -c -k                        # Skip SSL verification (dev)
        
        \b
        Environment Variables:
          MUBAN_CLIENT_ID     - OAuth2 Client ID
          MUBAN_CLIENT_SECRET - OAuth2 Client Secret
          MUBAN_VERIFY_SSL    - Set to 'false' to skip SSL verification
        """
        from ..auth import MubanAuthClient
        
        config_manager = ctx.config_manager
        config = config_manager.get()
        
        # Override server if provided
        if server:
            config.server_url = server
        
        # Override SSL verification if specified
        if no_verify_ssl:
            config.verify_ssl = False
        
        if not config.server_url:
            print_error(
                "Server URL not configured.",
                f"Run '{__prog_name__} configure --server URL' first."
            )
            sys.exit(1)
        
        # Warn if SSL verification is disabled
        if not config.verify_ssl:
            click.echo(click.style("⚠ Warning: SSL verification disabled", fg="yellow"))
        
        # Determine which authentication flow to use
        if client_credentials:
            # Client credentials flow
            _login_client_credentials(
                ctx, config, config_manager,
                client_id, client_secret, scope, auth_endpoint
            )
        else:
            # Password grant flow
            _login_password(
                ctx, config, config_manager,
                username, password, auth_endpoint
            )


    def _login_password(
        ctx: MubanContext,
        config,
        config_manager,
        username: Optional[str],
        password: Optional[str],
        auth_endpoint: Optional[str]
    ):
        """Handle password grant login flow."""
        from ..auth import MubanAuthClient
        
        # Prompt for credentials if not provided
        if not username:
            username = click.prompt("Username")
        
        if not password:
            password = click.prompt("Password", hide_input=True)
        
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
                
                _save_token_result(config_manager, result)
                print_success("Login successful! Token saved.")
                _print_token_info(result)
                    
        except AuthenticationError as e:
            print_error(f"Login failed: {e}")
            sys.exit(1)
        except MubanError as e:
            print_error(str(e))
            sys.exit(1)


    def _login_client_credentials(
        ctx: MubanContext,
        config,
        config_manager,
        client_id: Optional[str],
        client_secret: Optional[str],
        scope: Optional[str],
        auth_endpoint: Optional[str]
    ):
        """Handle client credentials login flow."""
        from ..auth import MubanAuthClient
        
        # Use provided credentials or fall back to config
        cid = client_id or config.client_id
        csecret = client_secret or config.client_secret
        
        if not cid or not csecret:
            print_error(
                "Client credentials not configured.",
                f"Either provide --client-id and --client-secret options,\n"
                f"set MUBAN_CLIENT_ID and MUBAN_CLIENT_SECRET environment variables,\n"
                f"or run '{__prog_name__} configure --client-id ID --client-secret SECRET'."
            )
            sys.exit(1)
        
        print_info(f"Authenticating with client credentials to {config.get_auth_server_url()}...")
        
        try:
            with MubanAuthClient(config) as auth_client:
                result = auth_client.client_credentials_login(
                    client_id=cid,
                    client_secret=csecret,
                    scope=scope,
                    auth_endpoint=auth_endpoint
                )
                
                _save_token_result(config_manager, result)
                print_success("Client credentials login successful! Token saved.")
                _print_token_info(result)
                    
        except AuthenticationError as e:
            print_error(f"Client credentials login failed: {e}")
            sys.exit(1)
        except MubanError as e:
            print_error(str(e))
            sys.exit(1)


    def _save_token_result(config_manager, result: dict):
        """Save token result to configuration."""
        token = result.get('access_token')
        if not token:
            print_error("Authentication succeeded but no token received.")
            sys.exit(1)
        
        update_data = {'token': token}
        
        # Save refresh token if provided
        if result.get('refresh_token'):
            update_data['refresh_token'] = result['refresh_token']
        
        # Calculate expiration time
        if result.get('expires_in'):
            update_data['token_expires_at'] = int(time.time()) + int(result['expires_in'])
        
        config_manager.update(**update_data)


    def _print_token_info(result: dict):
        """Print token information."""
        if result.get('expires_in'):
            click.echo(f"  Token expires in: {result['expires_in']} seconds")
        if result.get('refresh_token'):
            click.echo("  Refresh token saved for automatic renewal.")

    @cli.command('logout')
    @click.option('--yes', '-y', is_flag=True, help='Skip confirmation')
    @pass_context
    def logout(ctx: MubanContext, yes: bool):
        """
        Clear stored authentication token and invalidate session on server.
        """
        from ..auth import MubanAuthClient
        
        if not yes:
            if not confirm_action("Clear stored authentication token?"):
                print_info("Cancelled.")
                return
        
        config_manager = ctx.config_manager
        config = config_manager.get()
        
        # Try to invalidate refresh token on server (best effort)
        server_logout_ok = False
        had_refresh_token = config.has_refresh_token()
        if had_refresh_token:
            try:
                with MubanAuthClient(config) as auth_client:
                    server_logout_ok = auth_client.logout(config.refresh_token)
            except Exception:
                pass  # Server logout is best effort
        
        # Always clear local tokens regardless of server response
        config_manager.update(token='', refresh_token='', token_expires_at=0)
        
        if server_logout_ok:
            print_success("Logged out successfully. Session invalidated on server.")
        else:
            print_success("Logged out locally.")
            if had_refresh_token and not server_logout_ok:
                print_info("Note: Could not invalidate session on server.")

    @cli.command('refresh')
    @click.option('--auth-endpoint', help='Custom auth endpoint path')
    @pass_context
    def refresh(ctx: MubanContext, auth_endpoint: Optional[str]):
        """
        Refresh the access token using the stored refresh token.
        
        \b
        Examples:
          %(prog)s refresh
          %(prog)s refresh --auth-endpoint /oauth/token
        """
        from ..auth import MubanAuthClient
        
        config_manager = ctx.config_manager
        config = config_manager.get()
        
        if not config.has_refresh_token():
            print_error(
                "No refresh token available.",
                f"Run '{__prog_name__} login' to authenticate."
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
                f"Your session may have expired. Run '{__prog_name__} login' to re-authenticate."
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
                        print_info(f"Run '{__prog_name__} refresh' to get a new token.")
                    elif config.has_client_credentials():
                        print_info(f"Run '{__prog_name__} login --client-credentials' to re-authenticate.")
                    else:
                        print_info(f"Run '{__prog_name__} login' to re-authenticate.")
            
            # Show refresh token availability
            if config.has_refresh_token():
                click.echo("  Refresh: " + click.style("available", fg="green"))
            elif config.has_client_credentials():
                click.echo("  Refresh: " + click.style("via client credentials", fg="cyan"))
            else:
                click.echo("  Refresh: " + click.style("not available", fg="yellow"))
            
            # Show client credentials status
            if config.has_client_credentials():
                click.echo("  Client:  " + click.style(f"{config.client_id[:20]}..." if len(config.client_id) > 20 else config.client_id, fg="cyan"))
        else:
            click.echo("\nAuthentication Status: " + click.style("Not authenticated", fg="red"))
            click.echo(f"  Server: {config.server_url or '(not configured)'}")
            if config.has_client_credentials():
                click.echo("  Client:  " + click.style(f"{config.client_id}", fg="cyan") + " (configured)")
                print_info(f"Run '{__prog_name__} login --client-credentials' to authenticate.")
            else:
                print_info(f"Run '{__prog_name__} login' to authenticate.")
