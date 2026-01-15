"""
Audit commands for Muban CLI.
"""
import sys
from datetime import datetime, timedelta
from typing import Optional
import re

import click

from ..api import MubanAPIClient
from ..exceptions import MubanError, PermissionDeniedError
from ..utils import (
    OutputFormat,
    confirm_action,
    print_error,
    print_info,
    print_json,
    print_success,
    setup_logging,
)
from . import common_options, pass_context, require_config, MubanContext, format_audit_logs


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


def register_audit_commands(cli: click.Group) -> None:
    """Register audit commands with the CLI."""
    
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
        truncate_length: int,
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
                    total_pages = data.get('totalPages', 1)
                    click.echo(f"\nAudit Logs (Page {page}/{total_pages}, {total} total):\n")
                
                format_audit_logs(logs, fmt, truncate_length)
                    
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
        truncate_length: int,
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
                    total = data.get('totalItems', 0)
                    total_pages = data.get('totalPages', 1)
                    click.echo(f"\nSecurity Events (Page {page}/{total_pages}, {total} total):\n")
                
                format_audit_logs(logs, fmt, truncate_length)
                    
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
                    total = len(events)
                    click.echo(f"\nEvent Types ({total} total):\n")
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
