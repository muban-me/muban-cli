"""
Muban CLI - Command Line Interface for Muban Document Generation Service.

This module provides the main CLI entry point and all commands for:
- Configuration management
- Template operations (list, get, upload, download, delete)
- Document generation
- Audit operations (admin)
- System administration
"""

import sys
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import click

from . import __version__
from .config import (
    ConfigManager,
    get_config_manager,
    DEFAULT_SERVER_URL,
)
from .api import MubanAPIClient
from .exceptions import (
    MubanError,
    AuthenticationError,
    ValidationError,
    TemplateNotFoundError,
    PermissionDeniedError,
)
from .utils import (
    setup_logging,
    print_success,
    print_error,
    print_info,
    print_json,
    print_table,
    format_template_list,
    format_template_detail,
    format_parameters,
    format_fields,
    format_audit_logs,
    parse_parameters,
    load_json_file,
    confirm_action,
    truncate_string,
    OutputFormat,
)

logger = logging.getLogger(__name__)


# ============================================================================
# CLI Context and Common Options
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
    
    return wrapper


# ============================================================================
# Main CLI Group
# ============================================================================

@click.group()
@click.version_option(version=__version__, prog_name='muban')
@click.option(
    '--config-dir',
    type=click.Path(path_type=Path),
    envvar='MUBAN_CONFIG_DIR',
    help='Custom configuration directory'
)
@click.pass_context
def cli(ctx, config_dir: Optional[Path]):
    """
    Muban CLI - Document Generation Service Management Tool.
    
    A command-line interface for managing JasperReports templates
    and generating documents through the Muban API.
    
    \b
    Quick Start:
      1. Configure server:         muban configure --server https://api.muban.me
      2. Login with credentials:   muban login
      3. List templates:           muban list
      4. Generate a document:      muban generate TEMPLATE_ID -p title=Report
    
    \b
    Environment Variables:
      MUBAN_TOKEN        - JWT Bearer token (from login)
      MUBAN_SERVER_URL   - API server URL (default: https://api.muban.me)
      MUBAN_CONFIG_DIR   - Custom configuration directory
    """
    ctx.ensure_object(MubanContext)
    ctx.obj.config_manager = get_config_manager(config_dir)


# ============================================================================
# Configuration Commands
# ============================================================================

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
    '--timeout', '-t',
    type=int,
    help='Request timeout in seconds'
)
@click.option(
    '--no-verify-ssl',
    is_flag=True,
    help='Disable SSL certificate verification'
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
    timeout: Optional[int],
    no_verify_ssl: bool,
    show: bool
):
    """
    Configure Muban CLI settings.
    
    \b
    Examples:
      muban configure --server https://api.muban.me
      muban configure --auth-server https://auth.muban.me
      muban configure --show
    """
    config_manager = ctx.config_manager
    
    if show:
        config = config_manager.get()
        click.echo("\nCurrent Configuration:")
        click.echo(f"  Server URL:      {config.server_url}")
        click.echo(f"  Auth Server:     {config.auth_server_url or '(same as server)'}")
        click.echo(f"  Token:           {'*' * 20 + '...' if config.token else '(not authenticated)'}")
        click.echo(f"  Timeout:         {config.timeout}s")
        click.echo(f"  Verify SSL:      {config.verify_ssl}")
        click.echo(f"  Config Path:     {config_manager.get_config_path()}")
        return
    
    # Interactive configuration if no options provided
    if not any([server, auth_server, timeout, no_verify_ssl]):
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
    
    # Update configuration
    updates = {}
    if server:
        updates['server_url'] = server
    if auth_server:
        updates['auth_server_url'] = auth_server
    if timeout:
        updates['timeout'] = timeout
    if no_verify_ssl:
        updates['verify_ssl'] = False
    
    if updates:
        config_manager.update(**updates)
        print_success("Configuration saved successfully.")
        print_info("Run 'muban login' to authenticate with your credentials.")
    else:
        print_info("No changes made.")


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
    from .auth import MubanAuthClient
    
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
                import time
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
    from .auth import MubanAuthClient
    
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
                import time
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
    import time
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


@cli.command('config-clear')
@click.confirmation_option(prompt='Are you sure you want to clear all configuration?')
@pass_context
def config_clear(ctx: MubanContext):
    """Clear all stored configuration."""
    ctx.config_manager.clear()
    print_success("Configuration cleared.")


# ============================================================================
# Template Commands
# ============================================================================

@cli.command('list')
@common_options
@click.option('--page', '-p', type=int, default=1, help='Page number')
@click.option('--size', '-n', type=int, default=20, help='Items per page')
@click.option('--search', '-s', help='Search term')
@pass_context
@require_config
def list_templates(
    ctx: MubanContext,
    verbose: bool,
    quiet: bool,
    output_format: str,
    page: int,
    size: int,
    search: Optional[str]
):
    """
    List available templates.
    
    \b
    Examples:
      muban list
      muban list --search "invoice" --format json
      muban list --page 2 --size 50
    """
    setup_logging(verbose, quiet)
    fmt = OutputFormat(output_format)
    
    try:
        with MubanAPIClient(ctx.config_manager.get()) as client:
            result = client.list_templates(page=page, size=size, search=search)
            
            data = result.get('data', {})
            templates = data.get('items', [])
            
            if not quiet and fmt != OutputFormat.JSON:
                total = data.get('totalItems', 0)
                total_pages = data.get('totalPages', 1)
                click.echo(f"\nTemplates (Page {page}/{total_pages}, {total} total):\n")
            
            format_template_list(templates, fmt)
            
    except MubanError as e:
        print_error(str(e), e.details if hasattr(e, 'details') else None)
        sys.exit(1)


@cli.command('get')
@common_options
@click.argument('template_id')
@click.option('--params', is_flag=True, help='Show template parameters')
@click.option('--fields', is_flag=True, help='Show template fields')
@pass_context
@require_config
def get_template(
    ctx: MubanContext,
    verbose: bool,
    quiet: bool,
    output_format: str,
    template_id: str,
    params: bool,
    fields: bool
):
    """
    Get template details.
    
    \b
    Examples:
      muban get abc123-uuid
      muban get abc123-uuid --params
      muban get abc123-uuid --fields --format json
    """
    setup_logging(verbose, quiet)
    fmt = OutputFormat(output_format)
    
    try:
        with MubanAPIClient(ctx.config_manager.get()) as client:
            # Get basic template info
            result = client.get_template(template_id)
            template = result.get('data', {})
            
            format_template_detail(template, fmt)
            
            # Get parameters if requested
            if params:
                click.echo("\n--- Parameters ---")
                params_result = client.get_template_parameters(template_id)
                parameters = params_result.get('data', [])
                format_parameters(parameters, fmt)
            
            # Get fields if requested
            if fields:
                click.echo("\n--- Fields ---")
                fields_result = client.get_template_fields(template_id)
                field_list = fields_result.get('data', [])
                format_fields(field_list, fmt)
                
    except TemplateNotFoundError:
        print_error(f"Template not found: {template_id}")
        sys.exit(1)
    except MubanError as e:
        print_error(str(e))
        sys.exit(1)


@cli.command('push')
@common_options
@click.argument('file', type=click.Path(exists=True, path_type=Path))
@click.option('--name', '-n', required=True, help='Template name')
@click.option('--author', '-a', required=True, help='Template author')
@click.option('--metadata', '-m', help='Template metadata/description')
@pass_context
@require_config
def push_template(
    ctx: MubanContext,
    verbose: bool,
    quiet: bool,
    output_format: str,
    file: Path,
    name: str,
    author: str,
    metadata: Optional[str]
):
    """
    Upload a template to the server.
    
    \b
    The file must be a ZIP archive containing the JasperReports template.
    
    \b
    Examples:
      muban push report.zip --name "Monthly Report" --author "John Doe"
      muban push invoice.zip -n "Invoice" -a "Finance Team" -m "Standard invoice"
    """
    setup_logging(verbose, quiet)
    fmt = OutputFormat(output_format)
    
    if not file.suffix.lower() == '.zip':
        print_error("Template must be a ZIP file.")
        sys.exit(1)
    
    try:
        with MubanAPIClient(ctx.config_manager.get()) as client:
            if not quiet:
                print_info(f"Uploading template: {file.name}")
            
            result = client.upload_template(
                file_path=file,
                name=name,
                author=author,
                metadata=metadata
            )
            
            template = result.get('data', {})
            
            if fmt == OutputFormat.JSON:
                print_json(template)
            else:
                print_success(f"Template uploaded successfully!")
                click.echo(f"  ID: {template.get('id')}")
                click.echo(f"  Name: {template.get('name')}")
                
    except ValidationError as e:
        print_error(f"Validation error: {e}")
        sys.exit(1)
    except PermissionDeniedError:
        print_error("Permission denied. Manager role required.")
        sys.exit(1)
    except MubanError as e:
        print_error(str(e))
        sys.exit(1)


@cli.command('pull')
@common_options
@click.argument('template_id')
@click.option('--output', '-o', type=click.Path(path_type=Path), help='Output path')
@pass_context
@require_config
def pull_template(
    ctx: MubanContext,
    verbose: bool,
    quiet: bool,
    output_format: str,
    template_id: str,
    output: Optional[Path]
):
    """
    Download a template from the server.
    
    \b
    Examples:
      muban pull abc123-uuid
      muban pull abc123-uuid -o ./templates/report.zip
    """
    setup_logging(verbose, quiet)
    
    try:
        with MubanAPIClient(ctx.config_manager.get()) as client:
            if not quiet:
                print_info(f"Downloading template: {template_id}")
            
            output_path = client.download_template(template_id, output)
            
            print_success(f"Template downloaded: {output_path}")
                
    except TemplateNotFoundError:
        print_error(f"Template not found: {template_id}")
        sys.exit(1)
    except MubanError as e:
        print_error(str(e))
        sys.exit(1)


@cli.command('delete')
@common_options
@click.argument('template_id')
@click.option('--yes', '-y', is_flag=True, help='Skip confirmation')
@pass_context
@require_config
def delete_template(
    ctx: MubanContext,
    verbose: bool,
    quiet: bool,
    output_format: str,
    template_id: str,
    yes: bool
):
    """
    Delete a template from the server.
    
    \b
    Examples:
      muban delete abc123-uuid
      muban delete abc123-uuid --yes
    """
    setup_logging(verbose, quiet)
    
    if not yes:
        if not confirm_action(f"Delete template {template_id}?"):
            print_info("Cancelled.")
            return
    
    try:
        with MubanAPIClient(ctx.config_manager.get()) as client:
            client.delete_template(template_id)
            print_success(f"Template deleted: {template_id}")
                
    except TemplateNotFoundError:
        print_error(f"Template not found: {template_id}")
        sys.exit(1)
    except PermissionDeniedError:
        print_error("Permission denied. Manager role required.")
        sys.exit(1)
    except MubanError as e:
        print_error(str(e))
        sys.exit(1)


@cli.command('search')
@common_options
@click.argument('query')
@click.option('--page', '-p', type=int, default=1, help='Page number')
@click.option('--size', '-n', type=int, default=20, help='Items per page')
@pass_context
@require_config
def search_templates(
    ctx: MubanContext,
    verbose: bool,
    quiet: bool,
    output_format: str,
    query: str,
    page: int,
    size: int
):
    """
    Search templates by name or description.
    
    \b
    Examples:
      muban search "invoice"
      muban search "quarterly report" --format json
    """
    setup_logging(verbose, quiet)
    fmt = OutputFormat(output_format)
    
    try:
        with MubanAPIClient(ctx.config_manager.get()) as client:
            result = client.list_templates(page=page, size=size, search=query)
            
            data = result.get('data', {})
            templates = data.get('items', [])
            
            if not quiet and fmt != OutputFormat.JSON:
                total = data.get('totalItems', 0)
                click.echo(f"\nSearch results for '{query}' ({total} found):\n")
            
            format_template_list(templates, fmt)
            
    except MubanError as e:
        print_error(str(e))
        sys.exit(1)


# ============================================================================
# Document Generation Commands
# ============================================================================

@cli.command('generate')
@common_options
@click.argument('template_id')
@click.option(
    '--output-format', '-F',
    'doc_format',
    type=click.Choice(['pdf', 'xlsx', 'docx', 'rtf', 'html']),
    default='pdf',
    help='Output document format'
)
@click.option('--output', '-o', type=click.Path(path_type=Path), help='Output file path')
@click.option('--param', '-p', 'params', multiple=True, help='Parameter in name=value format')
@click.option('--params-file', type=click.Path(exists=True, path_type=Path), help='JSON file with parameters')
@click.option('--data-file', type=click.Path(exists=True, path_type=Path), help='JSON file with data source')
@click.option('--request-body', '-b', help='Full JSON request body (overrides other params)')
@click.option('--request-file', '-B', type=click.Path(exists=True, path_type=Path), help='JSON file with full request body')
@click.option('--locale', '-l', help='Document locale (e.g., en_US, pl_PL)')
@click.option('--filename', help='Custom output filename')
@click.option('--no-pagination', is_flag=True, help='Ignore pagination')
@click.option('--pdf-pdfa', type=click.Choice(['PDF/A-1a', 'PDF/A-1b', 'PDF/A-2a', 'PDF/A-2b', 'PDF/A-3a', 'PDF/A-3b']), help='PDF/A conformance')
@click.option('--pdf-password', help='PDF user password')
@click.option('--pdf-owner-password', help='PDF owner password')
@pass_context
@require_config
def generate_document(
    ctx: MubanContext,
    verbose: bool,
    quiet: bool,
    output_format: str,
    template_id: str,
    doc_format: str,
    output: Optional[Path],
    params: Tuple[str, ...],
    params_file: Optional[Path],
    data_file: Optional[Path],
    request_body: Optional[str],
    request_file: Optional[Path],
    locale: Optional[str],
    filename: Optional[str],
    no_pagination: bool,
    pdf_pdfa: Optional[str],
    pdf_password: Optional[str],
    pdf_owner_password: Optional[str]
):
    """
    Generate a document from a template.
    
    \b
    Examples:
      muban generate abc123 -p title="Sales Report" -p year=2025
      muban generate abc123 --params-file params.json -F xlsx
      muban generate abc123 --data-file data.json -o report.pdf
      muban generate abc123 --pdf-pdfa PDF/A-1b --locale pl_PL
      muban generate abc123 -b '{"parameters":[{"name":"title","value":"Test"}]}'
      muban generate abc123 -B request.json -F pdf
    """
    setup_logging(verbose, quiet)
    
    # Check for full request body mode
    full_request: Optional[Dict[str, Any]] = None
    
    if request_file:
        try:
            full_request = load_json_file(request_file)
        except ValueError as e:
            print_error(f"Invalid request file: {e}")
            sys.exit(1)
    elif request_body:
        import json
        try:
            full_request = json.loads(request_body)
        except json.JSONDecodeError as e:
            print_error(f"Invalid request body JSON: {e}")
            sys.exit(1)
    
    # If full request provided, use direct API call
    if full_request is not None:
        try:
            with MubanAPIClient(ctx.config_manager.get()) as client:
                if not quiet:
                    print_info(f"Generating {doc_format.upper()} document with custom request body...")
                
                output_path = client.generate_document_raw(
                    template_id=template_id,
                    output_format=doc_format,
                    request_data=full_request,
                    output_path=output
                )
                
                print_success(f"Document generated: {output_path}")
                    
        except TemplateNotFoundError:
            print_error(f"Template not found: {template_id}")
            sys.exit(1)
        except ValidationError as e:
            print_error(f"Validation error: {e}")
            sys.exit(1)
        except MubanError as e:
            print_error(str(e))
            sys.exit(1)
        return
    
    # Standard parameter-based generation
    # Parse parameters
    parameters: List[Dict[str, Any]] = []
    
    if params_file:
        try:
            params_data = load_json_file(params_file)
            if isinstance(params_data, list):
                for item in params_data:
                    if isinstance(item, dict):
                        parameters.append(item)
            elif isinstance(params_data, dict):
                parameters.extend([{"name": k, "value": v} for k, v in params_data.items()])
        except ValueError as e:
            print_error(f"Invalid params file: {e}")
            sys.exit(1)
    
    if params:
        try:
            parameters.extend(parse_parameters(list(params)))
        except ValueError as e:
            print_error(str(e))
            sys.exit(1)
    
    # Load data source
    data = None
    if data_file:
        try:
            data = load_json_file(data_file)
        except ValueError as e:
            print_error(f"Invalid data file: {e}")
            sys.exit(1)
    
    # Build PDF options
    pdf_options = None
    if any([pdf_pdfa, pdf_password, pdf_owner_password]):
        pdf_options = {}
        if pdf_pdfa:
            pdf_options['pdfaConformance'] = pdf_pdfa
        if pdf_password:
            pdf_options['userPassword'] = pdf_password
        if pdf_owner_password:
            pdf_options['ownerPassword'] = pdf_owner_password
    
    try:
        with MubanAPIClient(ctx.config_manager.get()) as client:
            if not quiet:
                print_info(f"Generating {doc_format.upper()} document...")
            
            output_path = client.generate_document(
                template_id=template_id,
                output_format=doc_format,
                parameters=parameters,
                output_path=output,
                filename=filename,
                data=data,
                document_locale=locale,
                pdf_export_options=pdf_options,
                ignore_pagination=no_pagination
            )
            
            print_success(f"Document generated: {output_path}")
                
    except TemplateNotFoundError:
        print_error(f"Template not found: {template_id}")
        sys.exit(1)
    except ValidationError as e:
        print_error(f"Validation error: {e}")
        sys.exit(1)
    except MubanError as e:
        print_error(str(e))
        sys.exit(1)


# ============================================================================
# Utility Commands
# ============================================================================

@cli.command('fonts')
@common_options
@pass_context
@require_config
def list_fonts(ctx: MubanContext, verbose: bool, quiet: bool, output_format: str):
    """List available fonts for document generation."""
    setup_logging(verbose, quiet)
    fmt = OutputFormat(output_format)
    
    try:
        with MubanAPIClient(ctx.config_manager.get()) as client:
            result = client.get_fonts()
            fonts = result.get('data', [])
            
            if fmt == OutputFormat.JSON:
                print_json(fonts)
            else:
                click.echo("\nAvailable Fonts:\n")
                headers = ["Name", "Faces", "PDF Embedded"]
                rows = []
                for font in fonts:
                    rows.append([
                        font.get('name', '-'),
                        ', '.join(font.get('faces', [])),
                        'Yes' if font.get('pdfEmbedded') else 'No'
                    ])
                print_table(headers, rows)
                
    except MubanError as e:
        print_error(str(e))
        sys.exit(1)


@cli.command('icc-profiles')
@common_options
@pass_context
@require_config
def list_icc_profiles(ctx: MubanContext, verbose: bool, quiet: bool, output_format: str):
    """List available ICC color profiles for PDF export."""
    setup_logging(verbose, quiet)
    fmt = OutputFormat(output_format)
    
    try:
        with MubanAPIClient(ctx.config_manager.get()) as client:
            result = client.get_icc_profiles()
            profiles = result.get('data', [])
            
            if fmt == OutputFormat.JSON:
                print_json(profiles)
            else:
                click.echo("\nAvailable ICC Profiles:\n")
                for profile in profiles:
                    click.echo(f"  • {profile}")
                
    except MubanError as e:
        print_error(str(e))
        sys.exit(1)


# ============================================================================
# Admin Commands
# ============================================================================

@cli.group('admin')
def admin():
    """Administrative commands (requires admin role)."""
    pass


@admin.command('verify-integrity')
@common_options
@click.argument('template_id')
@pass_context
@require_config
def verify_integrity(
    ctx: MubanContext,
    verbose: bool,
    quiet: bool,
    output_format: str,
    template_id: str
):
    """Verify template file integrity."""
    setup_logging(verbose, quiet)
    fmt = OutputFormat(output_format)
    
    try:
        with MubanAPIClient(ctx.config_manager.get()) as client:
            result = client.verify_template_integrity(template_id)
            
            if fmt == OutputFormat.JSON:
                print_json(result)
            else:
                print_success("Template integrity verified.")
                
    except ValidationError as e:
        print_error(f"Integrity check failed: {e}")
        sys.exit(1)
    except PermissionDeniedError:
        print_error("Permission denied. Admin role required.")
        sys.exit(1)
    except MubanError as e:
        print_error(str(e))
        sys.exit(1)


@admin.command('regenerate-digest')
@common_options
@click.argument('template_id')
@pass_context
@require_config
def regenerate_digest(
    ctx: MubanContext,
    verbose: bool,
    quiet: bool,
    output_format: str,
    template_id: str
):
    """Regenerate integrity digest for a template."""
    setup_logging(verbose, quiet)
    fmt = OutputFormat(output_format)
    
    try:
        with MubanAPIClient(ctx.config_manager.get()) as client:
            result = client.regenerate_template_digest(template_id)
            
            if fmt == OutputFormat.JSON:
                print_json(result)
            else:
                print_success("Digest regenerated successfully.")
                
    except PermissionDeniedError:
        print_error("Permission denied. Admin role required.")
        sys.exit(1)
    except MubanError as e:
        print_error(str(e))
        sys.exit(1)


@admin.command('regenerate-all-digests')
@common_options
@click.option('--yes', '-y', is_flag=True, help='Skip confirmation')
@pass_context
@require_config
def regenerate_all_digests(
    ctx: MubanContext,
    verbose: bool,
    quiet: bool,
    output_format: str,
    yes: bool
):
    """Regenerate integrity digests for all templates."""
    setup_logging(verbose, quiet)
    fmt = OutputFormat(output_format)
    
    if not yes:
        if not confirm_action("Regenerate digests for ALL templates?"):
            print_info("Cancelled.")
            return
    
    try:
        with MubanAPIClient(ctx.config_manager.get()) as client:
            result = client.regenerate_all_digests()
            
            if fmt == OutputFormat.JSON:
                print_json(result)
            else:
                print_success("All digests regenerated.")
                
    except PermissionDeniedError:
        print_error("Permission denied. Admin role required.")
        sys.exit(1)
    except MubanError as e:
        print_error(str(e))
        sys.exit(1)


@admin.command('server-config')
@common_options
@pass_context
@require_config
def server_config(ctx: MubanContext, verbose: bool, quiet: bool, output_format: str):
    """Get server configuration."""
    setup_logging(verbose, quiet)
    
    try:
        with MubanAPIClient(ctx.config_manager.get()) as client:
            result = client.get_server_config()
            print_json(result.get('data', {}))
                
    except PermissionDeniedError:
        print_error("Permission denied. Admin role required.")
        sys.exit(1)
    except MubanError as e:
        print_error(str(e))
        sys.exit(1)


# ============================================================================
# Audit Commands
# ============================================================================

@cli.group('audit')
def audit():
    """Audit and monitoring commands (requires admin role)."""
    pass


@audit.command('logs')
@common_options
@click.option('--page', '-p', type=int, default=1, help='Page number')
@click.option('--size', '-n', type=int, default=50, help='Items per page')
@click.option('--event-type', '-e', help='Filter by event type')
@click.option('--severity', '-s', type=click.Choice(['LOW', 'MEDIUM', 'HIGH', 'CRITICAL']), help='Filter by severity')
@click.option('--user', '-u', help='Filter by user ID')
@click.option('--ip', help='Filter by IP address')
@click.option('--success/--failed', default=None, help='Filter by success status')
@click.option('--since', help='Start time (ISO format or relative like "1d", "2h")')
@pass_context
@require_config
def audit_logs(
    ctx: MubanContext,
    verbose: bool,
    quiet: bool,
    output_format: str,
    page: int,
    size: int,
    event_type: Optional[str],
    severity: Optional[str],
    user: Optional[str],
    ip: Optional[str],
    success: Optional[bool],
    since: Optional[str]
):
    """
    View audit logs.
    
    \b
    Examples:
      muban audit logs
      muban audit logs --severity HIGH --since 1d
      muban audit logs --event-type LOGIN_FAILURE --format json
    """
    setup_logging(verbose, quiet)
    fmt = OutputFormat(output_format)
    
    # Parse relative time
    start_time = None
    if since:
        start_time = parse_relative_time(since)
    
    try:
        with MubanAPIClient(ctx.config_manager.get()) as client:
            result = client.get_audit_logs(
                page=page,
                size=size,
                event_type=event_type,
                severity=severity,
                user_id=user,
                ip_address=ip,
                success=success,
                start_time=start_time
            )
            
            data = result.get('data', {})
            logs = data.get('items', [])
            
            if not quiet and fmt != OutputFormat.JSON:
                total = data.get('totalItems', 0)
                click.echo(f"\nAudit Logs ({total} total):\n")
            
            format_audit_logs(logs, fmt)
                
    except PermissionDeniedError:
        print_error("Permission denied. Admin role required.")
        sys.exit(1)
    except MubanError as e:
        print_error(str(e))
        sys.exit(1)


@audit.command('statistics')
@common_options
@click.option('--since', help='Start time (ISO format or relative like "7d")')
@pass_context
@require_config
def audit_statistics(
    ctx: MubanContext,
    verbose: bool,
    quiet: bool,
    output_format: str,
    since: Optional[str]
):
    """Get audit statistics."""
    setup_logging(verbose, quiet)
    
    start_time = None
    if since:
        start_time = parse_relative_time(since)
    
    try:
        with MubanAPIClient(ctx.config_manager.get()) as client:
            result = client.get_audit_statistics(start_time=start_time)
            print_json(result.get('data', {}))
                
    except PermissionDeniedError:
        print_error("Permission denied. Admin role required.")
        sys.exit(1)
    except MubanError as e:
        print_error(str(e))
        sys.exit(1)


@audit.command('security')
@common_options
@click.option('--page', '-p', type=int, default=1, help='Page number')
@click.option('--size', '-n', type=int, default=50, help='Items per page')
@click.option('--since', help='Start time')
@pass_context
@require_config
def audit_security(
    ctx: MubanContext,
    verbose: bool,
    quiet: bool,
    output_format: str,
    page: int,
    size: int,
    since: Optional[str]
):
    """Get security events."""
    setup_logging(verbose, quiet)
    fmt = OutputFormat(output_format)
    
    start_time = None
    if since:
        start_time = parse_relative_time(since)
    
    try:
        with MubanAPIClient(ctx.config_manager.get()) as client:
            result = client.get_security_events(
                page=page,
                size=size,
                start_time=start_time
            )
            
            data = result.get('data', {})
            logs = data.get('items', [])
            
            if not quiet and fmt != OutputFormat.JSON:
                click.echo("\nSecurity Events:\n")
            
            format_audit_logs(logs, fmt)
                
    except PermissionDeniedError:
        print_error("Permission denied. Admin role required.")
        sys.exit(1)
    except MubanError as e:
        print_error(str(e))
        sys.exit(1)


@audit.command('dashboard')
@common_options
@pass_context
@require_config
def audit_dashboard(ctx: MubanContext, verbose: bool, quiet: bool, output_format: str):
    """Get audit dashboard overview."""
    setup_logging(verbose, quiet)
    
    try:
        with MubanAPIClient(ctx.config_manager.get()) as client:
            result = client.get_dashboard_overview()
            print_json(result.get('data', {}))
                
    except PermissionDeniedError:
        print_error("Permission denied. Admin role required.")
        sys.exit(1)
    except MubanError as e:
        print_error(str(e))
        sys.exit(1)


@audit.command('threats')
@common_options
@pass_context
@require_config
def audit_threats(ctx: MubanContext, verbose: bool, quiet: bool, output_format: str):
    """Get security threats summary."""
    setup_logging(verbose, quiet)
    
    try:
        with MubanAPIClient(ctx.config_manager.get()) as client:
            result = client.get_security_threats()
            print_json(result.get('data', {}))
                
    except PermissionDeniedError:
        print_error("Permission denied. Admin role required.")
        sys.exit(1)
    except MubanError as e:
        print_error(str(e))
        sys.exit(1)


@audit.command('health')
@common_options
@pass_context
@require_config
def audit_health(ctx: MubanContext, verbose: bool, quiet: bool, output_format: str):
    """Check audit system health."""
    setup_logging(verbose, quiet)
    
    try:
        with MubanAPIClient(ctx.config_manager.get()) as client:
            result = client.get_audit_health()
            
            if output_format == 'json':
                print_json(result)
            else:
                print_success(f"Audit system is operational: {result.get('data', '')}")
                
    except MubanError as e:
        print_error(str(e))
        sys.exit(1)


@audit.command('event-types')
@common_options
@pass_context
@require_config
def audit_event_types(ctx: MubanContext, verbose: bool, quiet: bool, output_format: str):
    """List available audit event types."""
    setup_logging(verbose, quiet)
    
    try:
        with MubanAPIClient(ctx.config_manager.get()) as client:
            result = client.get_event_types()
            events = result.get('data', [])
            
            if output_format == 'json':
                print_json(events)
            else:
                click.echo("\nAvailable Event Types:\n")
                for event in events:
                    click.echo(f"  • {event}")
                
    except PermissionDeniedError:
        print_error("Permission denied. Admin role required.")
        sys.exit(1)
    except MubanError as e:
        print_error(str(e))
        sys.exit(1)


@audit.command('cleanup')
@common_options
@click.option('--yes', '-y', is_flag=True, help='Skip confirmation')
@pass_context
@require_config
def audit_cleanup(
    ctx: MubanContext,
    verbose: bool,
    quiet: bool,
    output_format: str,
    yes: bool
):
    """Trigger audit log cleanup."""
    setup_logging(verbose, quiet)
    
    if not yes:
        if not confirm_action("Trigger audit log cleanup?"):
            print_info("Cancelled.")
            return
    
    try:
        with MubanAPIClient(ctx.config_manager.get()) as client:
            result = client.cleanup_audit_logs()
            print_success(f"Cleanup initiated: {result.get('data', '')}")
                
    except PermissionDeniedError:
        print_error("Permission denied. Admin role required.")
        sys.exit(1)
    except MubanError as e:
        print_error(str(e))
        sys.exit(1)


# ============================================================================
# User Management Commands
# ============================================================================

def _format_bool(value: bool) -> str:
    """Format boolean value with color."""
    return click.style("Yes", fg="green") if value else click.style("No", fg="red")


def _format_title(title: str) -> str:
    """Format a title with styling."""
    return click.style(title, bold=True)


@cli.group('users')
def users():
    """User management commands."""
    pass


@users.command('me')
@common_options
@pass_context
@require_config
def user_me(ctx: MubanContext, verbose: bool, quiet: bool, output_format: str):
    """Get current user profile."""
    setup_logging(verbose, quiet)
    
    try:
        with MubanAPIClient(ctx.config_manager.get()) as client:
            result = client.get_current_user()
            user_data = result.get('data', {})
            
            if output_format == 'json':
                print_json(user_data)
            else:
                click.echo(_format_title("Current User Profile"))
                click.echo(f"  ID:         {user_data.get('id', 'N/A')}")
                click.echo(f"  Username:   {user_data.get('username', 'N/A')}")
                click.echo(f"  Email:      {user_data.get('email', 'N/A')}")
                click.echo(f"  First Name: {user_data.get('firstName', 'N/A')}")
                click.echo(f"  Last Name:  {user_data.get('lastName', 'N/A')}")
                roles = user_data.get('roles', [])
                click.echo(f"  Roles:      {', '.join(roles) if roles else 'None'}")
                click.echo(f"  Enabled:    {_format_bool(user_data.get('enabled', False))}")
                click.echo(f"  Created:    {user_data.get('createdAt', 'N/A')}")
                
    except MubanError as e:
        print_error(str(e))
        sys.exit(1)


@users.command('update-me')
@common_options
@click.option('--email', help='New email address')
@click.option('--first-name', help='New first name')
@click.option('--last-name', help='New last name')
@pass_context
@require_config
def user_update_me(
    ctx: MubanContext,
    verbose: bool,
    quiet: bool,
    output_format: str,
    email: Optional[str],
    first_name: Optional[str],
    last_name: Optional[str]
):
    """Update current user profile."""
    setup_logging(verbose, quiet)
    
    if not email and not first_name and not last_name:
        print_error("No update options provided. Use --email, --first-name, or --last-name")
        sys.exit(1)
    
    try:
        with MubanAPIClient(ctx.config_manager.get()) as client:
            result = client.update_current_user(
                first_name=first_name,
                last_name=last_name,
                email=email
            )
            
            if output_format == 'json':
                print_json(result)
            else:
                print_success("Profile updated successfully")
                
    except MubanError as e:
        print_error(str(e))
        sys.exit(1)


@users.command('change-password')
@common_options
@click.option('--current', prompt=True, hide_input=True, help='Current password')
@click.option('--new-password', prompt=True, hide_input=True, confirmation_prompt=True, help='New password')
@pass_context
@require_config
def user_change_password(
    ctx: MubanContext,
    verbose: bool,
    quiet: bool,
    output_format: str,
    current: str,
    new_password: str
):
    """Change current user password."""
    setup_logging(verbose, quiet)
    
    try:
        with MubanAPIClient(ctx.config_manager.get()) as client:
            client.change_current_user_password(current, new_password)
            
            if output_format == 'json':
                print_json({'success': True, 'message': 'Password changed successfully'})
            else:
                print_success("Password changed successfully")
                
    except MubanError as e:
        print_error(str(e))
        sys.exit(1)


@users.command('list')
@common_options
@click.option('--page', '-p', type=int, default=1, help='Page number')
@click.option('--size', '-n', type=int, default=20, help='Items per page')
@click.option('--search', '-s', help='Search by username or email')
@click.option('--role', '-r', type=click.Choice(['ROLE_USER', 'ROLE_ADMIN', 'ROLE_MANAGER']), help='Filter by role')
@click.option('--enabled/--disabled', default=None, help='Filter by enabled status')
@pass_context
@require_config
def user_list(
    ctx: MubanContext,
    verbose: bool,
    quiet: bool,
    output_format: str,
    page: int,
    size: int,
    search: Optional[str],
    role: Optional[str],
    enabled: Optional[bool]
):
    """List all users (admin only)."""
    setup_logging(verbose, quiet)
    
    try:
        with MubanAPIClient(ctx.config_manager.get()) as client:
            result = client.list_users(
                page=page - 1,  # API is 0-indexed
                size=size,
                search=search,
                role=role,
                enabled=enabled
            )
            
            if output_format == 'json':
                print_json(result)
            else:
                data = result.get('data', {})
                # Support both Spring Pageable (content) and custom (items) formats
                users_list = data.get('items', data.get('content', []))
                
                if not users_list:
                    click.echo("No users found.")
                    return
                
                # Build table
                headers = ['ID', 'Username', 'Email', 'Roles', 'Enabled', 'Created']
                rows: List[List[str]] = []
                
                for user in users_list:
                    roles_list = user.get('roles', [])
                    roles_str = ', '.join(r.replace('ROLE_', '') for r in roles_list)
                    created = user.get('created', user.get('createdAt', ''))
                    rows.append([
                        str(user.get('id', '')),
                        user.get('username', 'N/A'),
                        truncate_string(user.get('email', ''), 25),
                        roles_str,
                        _format_bool(user.get('enabled', False)),
                        created[:10] if created else 'N/A'
                    ])
                
                print_table(headers, rows)
                
                # Pagination info - support both formats
                total = data.get('totalItems', data.get('totalElements', 0))
                total_pages = data.get('totalPages', 1)
                click.echo(f"\nPage {page} of {total_pages} ({total} total users)")
                
    except PermissionDeniedError:
        print_error("Permission denied. Admin role required.")
        sys.exit(1)
    except MubanError as e:
        print_error(str(e))
        sys.exit(1)


@users.command('get')
@common_options
@click.argument('user_id', type=str)
@pass_context
@require_config
def user_get(ctx: MubanContext, verbose: bool, quiet: bool, output_format: str, user_id: str):
    """Get user details by ID (admin only)."""
    setup_logging(verbose, quiet)
    
    try:
        with MubanAPIClient(ctx.config_manager.get()) as client:
            result = client.get_user(user_id)
            user_data = result.get('data', {})
            
            if output_format == 'json':
                print_json(user_data)
            else:
                click.echo(_format_title(f"User: {user_data.get('username', 'Unknown')}"))
                click.echo(f"  ID:         {user_data.get('id', 'N/A')}")
                click.echo(f"  Username:   {user_data.get('username', 'N/A')}")
                click.echo(f"  Email:      {user_data.get('email', 'N/A')}")
                click.echo(f"  First Name: {user_data.get('firstName', 'N/A')}")
                click.echo(f"  Last Name:  {user_data.get('lastName', 'N/A')}")
                roles = user_data.get('roles', [])
                click.echo(f"  Roles:      {', '.join(roles) if roles else 'None'}")
                click.echo(f"  Enabled:    {_format_bool(user_data.get('enabled', False))}")
                click.echo(f"  Created:    {user_data.get('createdAt', 'N/A')}")
                click.echo(f"  Updated:    {user_data.get('updatedAt', 'N/A')}")
                
    except PermissionDeniedError:
        print_error("Permission denied. Admin role required.")
        sys.exit(1)
    except MubanError as e:
        print_error(str(e))
        sys.exit(1)


@users.command('create')
@common_options
@click.option('--username', '-u', required=True, help='Username')
@click.option('--email', '-e', required=True, help='Email address')
@click.option('--password', '-p', prompt=True, hide_input=True, confirmation_prompt=True, help='Password')
@click.option('--first-name', help='First name')
@click.option('--last-name', help='Last name')
@click.option('--role', '-r', 'roles', multiple=True, 
              type=click.Choice(['ROLE_USER', 'ROLE_ADMIN', 'ROLE_MANAGER']),
              default=['ROLE_USER'], help='User roles (can specify multiple)')
@click.option('--disabled', is_flag=True, help='Create user as disabled')
@pass_context
@require_config
def user_create(
    ctx: MubanContext,
    verbose: bool,
    quiet: bool,
    output_format: str,
    username: str,
    email: str,
    password: str,
    first_name: Optional[str],
    last_name: Optional[str],
    roles: Tuple[str, ...],
    disabled: bool
):
    """Create a new user (admin only)."""
    setup_logging(verbose, quiet)
    
    try:
        with MubanAPIClient(ctx.config_manager.get()) as client:
            result = client.create_user(
                username=username,
                email=email,
                password=password,
                first_name=first_name or "",
                last_name=last_name or "",
                roles=list(roles) if roles else None,
                enabled=not disabled
            )
            created_user = result.get('data', {})
            
            if output_format == 'json':
                print_json(created_user)
            else:
                print_success(f"User '{username}' created successfully with ID: {created_user.get('id')}")
                
    except PermissionDeniedError:
        print_error("Permission denied. Admin role required.")
        sys.exit(1)
    except MubanError as e:
        print_error(str(e))
        sys.exit(1)


@users.command('update')
@common_options
@click.argument('user_id', type=str)
@click.option('--email', help='New email address')
@click.option('--first-name', help='New first name')
@click.option('--last-name', help='New last name')
@pass_context
@require_config
def user_update(
    ctx: MubanContext,
    verbose: bool,
    quiet: bool,
    output_format: str,
    user_id: str,
    email: Optional[str],
    first_name: Optional[str],
    last_name: Optional[str]
):
    """Update a user's profile (admin only)."""
    setup_logging(verbose, quiet)
    
    try:
        with MubanAPIClient(ctx.config_manager.get()) as client:
            result = client.update_user(
                user_id=user_id,
                first_name=first_name,
                last_name=last_name,
                email=email
            )
            
            if output_format == 'json':
                print_json(result)
            else:
                print_success(f"User {user_id} updated successfully")
                
    except PermissionDeniedError:
        print_error("Permission denied. Admin role required.")
        sys.exit(1)
    except MubanError as e:
        print_error(str(e))
        sys.exit(1)


@users.command('delete')
@common_options
@click.argument('user_id', type=str)
@click.option('--yes', '-y', 'force', is_flag=True, help='Skip confirmation')
@pass_context
@require_config
def user_delete(
    ctx: MubanContext,
    verbose: bool,
    quiet: bool,
    output_format: str,
    user_id: str,
    force: bool
):
    """Delete a user (admin only)."""
    setup_logging(verbose, quiet)
    
    if not force:
        if not click.confirm(f"Are you sure you want to delete user {user_id}?"):
            click.echo("Aborted.")
            return
    
    try:
        with MubanAPIClient(ctx.config_manager.get()) as client:
            client.delete_user(user_id)
            
            if output_format == 'json':
                print_json({'success': True, 'message': f'User {user_id} deleted'})
            else:
                print_success(f"User {user_id} deleted successfully")
                
    except PermissionDeniedError:
        print_error("Permission denied. Admin role required.")
        sys.exit(1)
    except MubanError as e:
        print_error(str(e))
        sys.exit(1)


@users.command('roles')
@common_options
@click.argument('user_id', type=str)
@click.option('--set', '-s', 'set_roles', multiple=True,
              type=click.Choice(['ROLE_USER', 'ROLE_ADMIN', 'ROLE_MANAGER']),
              help='Set roles (replaces existing roles)')
@click.option('--add', '-a', 'add_roles', multiple=True,
              type=click.Choice(['ROLE_USER', 'ROLE_ADMIN', 'ROLE_MANAGER']),
              help='Add roles to existing roles')
@pass_context
@require_config
def user_roles(
    ctx: MubanContext,
    verbose: bool,
    quiet: bool,
    output_format: str,
    user_id: str,
    set_roles: Tuple[str, ...],
    add_roles: Tuple[str, ...]
):
    """Manage user roles (admin only)."""
    setup_logging(verbose, quiet)
    
    if not set_roles and not add_roles:
        # Just show current roles
        try:
            with MubanAPIClient(ctx.config_manager.get()) as client:
                result = client.get_user(user_id)
                user_data = result.get('data', {})
                roles = user_data.get('roles', [])
                
                if output_format == 'json':
                    print_json({'userId': user_id, 'roles': roles})
                else:
                    click.echo(f"User {user_id} roles: {', '.join(roles) if roles else 'None'}")
                    
        except PermissionDeniedError:
            print_error("Permission denied. Admin role required.")
            sys.exit(1)
        except MubanError as e:
            print_error(str(e))
            sys.exit(1)
        return
    
    # Determine new roles
    if set_roles:
        new_roles = list(set_roles)
    else:
        # Need to get current roles and add new ones
        try:
            with MubanAPIClient(ctx.config_manager.get()) as client:
                result = client.get_user(user_id)
                current_roles = result.get('data', {}).get('roles', [])
                new_roles = list(set(current_roles) | set(add_roles))
        except MubanError as e:
            print_error(str(e))
            sys.exit(1)
    
    try:
        with MubanAPIClient(ctx.config_manager.get()) as client:
            client.update_user_roles(user_id, new_roles)
            
            if output_format == 'json':
                print_json({'success': True, 'userId': user_id, 'roles': new_roles})
            else:
                print_success(f"User {user_id} roles updated: {', '.join(new_roles)}")
                
    except PermissionDeniedError:
        print_error("Permission denied. Admin role required.")
        sys.exit(1)
    except MubanError as e:
        print_error(str(e))
        sys.exit(1)


@users.command('set-password')
@common_options
@click.argument('user_id', type=str)
@click.option('--current', prompt=True, hide_input=True, help='Current password (or admin auth)')
@click.option('--password', '-p', prompt="New password", hide_input=True, confirmation_prompt=True, help='New password')
@pass_context
@require_config
def user_set_password(
    ctx: MubanContext,
    verbose: bool,
    quiet: bool,
    output_format: str,
    user_id: str,
    current: str,
    password: str
):
    """Change a user's password (admin or own password)."""
    setup_logging(verbose, quiet)
    
    try:
        with MubanAPIClient(ctx.config_manager.get()) as client:
            client.change_user_password(user_id, current, password)
            
            if output_format == 'json':
                print_json({'success': True, 'message': f'Password changed for user {user_id}'})
            else:
                print_success(f"Password changed for user {user_id}")
                
    except PermissionDeniedError:
        print_error("Permission denied. Admin role required.")
        sys.exit(1)
    except MubanError as e:
        print_error(str(e))
        sys.exit(1)


@users.command('enable')
@common_options
@click.argument('user_id', type=str)
@pass_context
@require_config
def user_enable(ctx: MubanContext, verbose: bool, quiet: bool, output_format: str, user_id: str):
    """Enable a user account (admin only)."""
    setup_logging(verbose, quiet)
    
    try:
        with MubanAPIClient(ctx.config_manager.get()) as client:
            client.enable_user(user_id)
            
            if output_format == 'json':
                print_json({'success': True, 'message': f'User {user_id} enabled'})
            else:
                print_success(f"User {user_id} enabled")
                
    except PermissionDeniedError:
        print_error("Permission denied. Admin role required.")
        sys.exit(1)
    except MubanError as e:
        print_error(str(e))
        sys.exit(1)


@users.command('disable')
@common_options
@click.argument('user_id', type=str)
@pass_context
@require_config
def user_disable(ctx: MubanContext, verbose: bool, quiet: bool, output_format: str, user_id: str):
    """Disable a user account (admin only)."""
    setup_logging(verbose, quiet)
    
    try:
        with MubanAPIClient(ctx.config_manager.get()) as client:
            client.disable_user(user_id)
            
            if output_format == 'json':
                print_json({'success': True, 'message': f'User {user_id} disabled'})
            else:
                print_success(f"User {user_id} disabled")
                
    except PermissionDeniedError:
        print_error("Permission denied. Admin role required.")
        sys.exit(1)
    except MubanError as e:
        print_error(str(e))
        sys.exit(1)


# ============================================================================
# Helper Functions
# ============================================================================

def parse_relative_time(time_str: str) -> Optional[datetime]:
    """
    Parse relative time string like "1d", "2h", "30m" or ISO format.
    
    Args:
        time_str: Time string
    
    Returns:
        datetime object or None
    """
    try:
        # Try ISO format first
        return datetime.fromisoformat(time_str.replace('Z', '+00:00'))
    except ValueError:
        pass
    
    # Parse relative format
    import re
    match = re.match(r'^(\d+)([dhms])$', time_str.lower())
    if match:
        value = int(match.group(1))
        unit = match.group(2)
        
        delta_map = {
            'd': timedelta(days=value),
            'h': timedelta(hours=value),
            'm': timedelta(minutes=value),
            's': timedelta(seconds=value),
        }
        
        if unit in delta_map:
            return datetime.now() - delta_map[unit]
    
    return None


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
        print_error(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
