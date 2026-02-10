"""
User management commands for Muban CLI.
"""
import sys
from typing import List, Optional, Tuple

import click

from ..api import MubanAPIClient
from ..exceptions import MubanError, PermissionDeniedError
from ..utils import (
    format_datetime,
    OutputFormat,
    print_csv,
    print_error,
    print_json,
    print_success,
    print_table,
    setup_logging,
    truncate_string,
)
from . import common_options, pass_context, require_config, MubanContext


def _format_bool(value: bool, fmt: OutputFormat = OutputFormat.TABLE) -> str:
    """Format boolean value with color (for table) or plain text (for CSV)."""
    if fmt == OutputFormat.CSV:
        return "Yes" if value else "No"
    return click.style("Yes", fg="green") if value else click.style("No", fg="red")


def _format_roles(roles: List[str]) -> str:
    """Format roles list, stripping ROLE_ prefix for cleaner display."""
    if not roles:
        return "None"
    return ', '.join(r.replace('ROLE_', '') for r in roles)


def _format_title(title: str) -> str:
    """Format a title with styling."""
    return click.style(title, bold=True)


def register_user_commands(cli: click.Group) -> None:
    """Register user management commands with the CLI."""
    
    @cli.group('users')
    def users():
        """User management commands."""
        pass

    @users.command('me')
    @common_options
    @pass_context
    @require_config
    def user_me(ctx: MubanContext, verbose: bool, quiet: bool, output_format: str, truncate_length: int):
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
                    click.echo(f"  Roles:      {_format_roles(roles)}")
                    click.echo(f"  Enabled:    {_format_bool(user_data.get('enabled', False))}")
                    click.echo(f"  Created:    {format_datetime(user_data.get('created'))}")
                    click.echo(f"  Last Login: {format_datetime(user_data.get('lastLogin'))}")
                    
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
        truncate_length: int,
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
        truncate_length: int,
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
    @click.option('--sort-by', type=click.Choice(['username', 'email', 'firstName', 'lastName', 'created', 'lastLogin']),
                  default='username', help='Sort field (default: username)')
    @click.option('--sort-dir', type=click.Choice(['asc', 'desc']),
                  default='asc', help='Sort direction (default: asc)')
    @pass_context
    @require_config
    def user_list(
        ctx: MubanContext,
        verbose: bool,
        quiet: bool,
        output_format: str,
        truncate_length: int,
        page: int,
        size: int,
        search: Optional[str],
        role: Optional[str],
        enabled: Optional[bool],
        sort_by: str,
        sort_dir: str
    ):
        """List all users (admin only)."""
        setup_logging(verbose, quiet)
        fmt = OutputFormat(output_format)
        
        try:
            with MubanAPIClient(ctx.config_manager.get()) as client:
                result = client.list_users(
                    page=page - 1,  # API is 0-indexed
                    size=size,
                    search=search,
                    role=role,
                    enabled=enabled,
                    sort_by=sort_by,
                    sort_dir=sort_dir
                )
                
                if fmt == OutputFormat.JSON:
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
                    
                    # For CSV, don't truncate data
                    if fmt == OutputFormat.CSV:
                        for user in users_list:
                            roles_list = user.get('roles', [])
                            roles_str = _format_roles(roles_list)
                            created = user.get('created', '')
                            rows.append([
                                str(user.get('id', '')),
                                user.get('username', 'N/A'),
                                user.get('email', ''),
                                roles_str,
                                'Yes' if user.get('enabled', False) else 'No',
                                format_datetime(created)[:10] if created else 'N/A'
                            ])
                        print_csv(headers, rows)
                    elif truncate_length > 0:
                        for user in users_list:
                            roles_list = user.get('roles', [])
                            roles_str = _format_roles(roles_list)
                            created = user.get('created', '')
                            rows.append([
                                str(user.get('id', '')),
                                user.get('username', 'N/A'),
                                truncate_string(user.get('email', ''), truncate_length),
                                roles_str,
                                _format_bool(user.get('enabled', False), fmt),
                                format_datetime(created)[:10] if created else 'N/A'
                            ])
                        # Pagination info - support both formats
                        total = data.get('totalItems', data.get('totalElements', 0))
                        total_pages = data.get('totalPages', 1)
                        click.echo(f"\nUsers (Page {page}/{total_pages}, {total} total):\n")
                        print_table(headers, rows)
                    else:
                        for user in users_list:
                            roles_list = user.get('roles', [])
                            roles_str = _format_roles(roles_list)
                            created = user.get('created', '')
                            rows.append([
                                str(user.get('id', '')),
                                user.get('username', 'N/A'),
                                user.get('email', ''),
                                roles_str,
                                _format_bool(user.get('enabled', False), fmt),
                                format_datetime(created)[:10] if created else 'N/A'
                            ])
                        # Pagination info - support both formats
                        total = data.get('totalItems', data.get('totalElements', 0))
                        total_pages = data.get('totalPages', 1)
                        click.echo(f"\nUsers (Page {page}/{total_pages}, {total} total):\n")
                        print_table(headers, rows)
                    
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
    def user_get(ctx: MubanContext, verbose: bool, quiet: bool, output_format: str, truncate_length: int, user_id: str):
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
                    click.echo(f"  Roles:      {_format_roles(roles)}")
                    click.echo(f"  Enabled:    {_format_bool(user_data.get('enabled', False))}")
                    click.echo(f"  Created:    {format_datetime(user_data.get('created'))}")
                    click.echo(f"  Last Login: {format_datetime(user_data.get('lastLogin'))}")
                    
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
        truncate_length: int,
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
        truncate_length: int,
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
        truncate_length: int,
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
        truncate_length: int,
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
        new_roles: List[str]
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
        truncate_length: int,
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
    def user_enable(ctx: MubanContext, verbose: bool, quiet: bool, output_format: str, truncate_length: int, user_id: str):
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
    def user_disable(ctx: MubanContext, verbose: bool, quiet: bool, output_format: str, truncate_length: int, user_id: str):
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
