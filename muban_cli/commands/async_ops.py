"""
Async operations commands for Muban CLI.

Commands for monitoring and managing async document generation.
"""
import sys
import json
from datetime import datetime, timedelta
from typing import Optional, List
from pathlib import Path

import click

from ..api import MubanAPIClient
from ..exceptions import MubanError, PermissionDeniedError
from ..utils import (
    OutputFormat,
    print_csv,
    print_error,
    print_info,
    print_json,
    print_success,
    print_table,
    print_warning,
    setup_logging,
    truncate_string,
    format_datetime,
)
from . import common_options, pass_context, require_config, MubanContext


def parse_relative_time(time_str: str) -> Optional[datetime]:
    """
    Parse relative time string like "1d", "2h", "30m" or ISO format.
    
    Args:
        time_str: Time string
    
    Returns:
        datetime object or None
    """
    import re
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


def format_async_status(status: str) -> str:
    """Format async status with color."""
    color_map = {
        "QUEUED": "blue",
        "PROCESSING": "yellow",
        "COMPLETED": "green",
        "FAILED": "red",
        "TIMEOUT": "magenta",
    }
    return click.style(status, fg=color_map.get(status, "white"))


def format_async_requests_table(requests: List[dict], fmt: OutputFormat, truncate_length: int = 50) -> None:
    """Format and print async requests table."""
    if fmt == OutputFormat.JSON:
        print_json(requests)
        return
    
    if not requests:
        print_info("No async requests found.")
        return
    
    headers = ["Request ID", "Template", "Status", "User", "Created", "Elapsed"]
    rows = []
    
    # For CSV, don't truncate data
    if fmt == OutputFormat.CSV:
        for req in requests:
            elapsed = req.get("elapsedMs")
            elapsed_str = f"{elapsed}ms" if elapsed else "-"
            rows.append([
                str(req.get("requestId", "-")),
                str(req.get("templateId", "-")),
                req.get("status", "-"),
                req.get("userId", "-"),
                format_datetime(req.get("createdAt"))[:16] if req.get("createdAt") else "-",
                elapsed_str,
            ])
        print_csv(headers, rows)
    else:
        for req in requests:
            elapsed = req.get("elapsedMs")
            elapsed_str = f"{elapsed}ms" if elapsed else "-"
            if truncate_length > 0:
                rows.append([
                    truncate_string(str(req.get("requestId", "-")), 36),
                    truncate_string(str(req.get("templateId", "-")), truncate_length),
                    format_async_status(req.get("status", "-")),
                    truncate_string(req.get("userId", "-"), truncate_length),
                    format_datetime(req.get("createdAt"))[:16] if req.get("createdAt") else "-",
                    elapsed_str,
                ])
            else:
                rows.append([
                    str(req.get("requestId", "-")),
                    str(req.get("templateId", "-")),
                    format_async_status(req.get("status", "-")),
                    req.get("userId", "-"),
                    format_datetime(req.get("createdAt"))[:16] if req.get("createdAt") else "-",
                    elapsed_str,
                ])
        print_table(headers, rows)


def register_async_commands(cli: click.Group) -> None:
    """Register async commands with the CLI."""
    
    @cli.group('async')
    def async_group():
        """Async document generation monitoring (requires admin role)."""
        pass

    @async_group.command('submit')
    @common_options
    @click.option('--template', '-t', required=True, help='Template ID')
    @click.option('--doc-format', '-F', 'output_fmt', default='PDF', 
                  type=click.Choice(['PDF', 'DOCX', 'XLSX', 'HTML', 'CSV', 'XML', 'JSON', 'TEXT']),
                  help='Document output format')
    @click.option('--param', '-p', multiple=True, help='Parameter in name=value format')
    @click.option('--data-file', '-d', type=click.Path(exists=True, path_type=Path),
                  help='JSON file with parameters')
    @click.option('--correlation-id', '-c', help='Correlation ID for tracking')
    @pass_context
    @require_config
    def async_submit(
        ctx: MubanContext,
        verbose: bool,
        quiet: bool,
        output_format: str,
        truncate_length: int,
        template: str,
        output_fmt: str,
        param: tuple,
        data_file: Optional[Path],
        correlation_id: Optional[str]
    ):
        """
        Submit a single async document generation request.
        
        \b
        Examples:
          muban async submit -t abc123 -F PDF -p name=John
          muban async submit -t abc123 -d params.json -c my-request-001
        """
        setup_logging(verbose, quiet)
        
        # Build parameters
        parameters = {}
        
        # Load from file if provided
        if data_file:
            try:
                with open(data_file, 'r') as f:
                    parameters = json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                print_error(f"Failed to load parameters file: {e}")
                sys.exit(1)
        
        # Override with command line params
        for p in param:
            if '=' not in p:
                print_error(f"Invalid parameter format: {p}. Use name=value")
                sys.exit(1)
            name, value = p.split('=', 1)
            parameters[name.strip()] = value.strip()
        
        # Build request
        request_item = {
            "templateId": template,
            "format": output_fmt,
            "parameters": parameters
        }
        if correlation_id:
            request_item["correlationId"] = correlation_id
        
        try:
            with MubanAPIClient(ctx.config_manager.get()) as client:
                result = client.submit_bulk_async([request_item])
                
                if output_format == 'json':
                    print_json(result)
                else:
                    submitted = result.get("submitted", 0)
                    failed = result.get("failed", 0)
                    
                    if submitted > 0:
                        tracking_ids = result.get("trackingIds", [])
                        print_success(f"Request submitted successfully!")
                        if tracking_ids:
                            click.echo(f"  Tracking ID: {tracking_ids[0]}")
                    else:
                        errors = result.get("errors", [])
                        print_error("Request failed to submit")
                        for err in errors:
                            click.echo(f"  Error: {err}")
                    
        except PermissionDeniedError:
            print_error("Permission denied. This operation requires appropriate permissions.")
            sys.exit(1)
        except MubanError as e:
            print_error(str(e))
            sys.exit(1)

    @async_group.command('bulk')
    @common_options
    @click.argument('file', type=click.Path(exists=True, path_type=Path))
    @click.option('--batch-id', '-b', help='Batch correlation ID')
    @pass_context
    @require_config
    def async_bulk(
        ctx: MubanContext,
        verbose: bool,
        quiet: bool,
        output_format: str,
        truncate_length: int,
        file: Path,
        batch_id: Optional[str]
    ):
        """
        Submit bulk async requests from a JSON file.
        
        The JSON file should contain an array of request objects with:
        - templateId (required): Template UUID
        - format (required): Output format (PDF, DOCX, etc.)
        - parameters (optional): Key-value pairs for template
        - correlationId (optional): Custom tracking ID
        
        \b
        Examples:
          muban async bulk requests.json
          muban async bulk requests.json --batch-id batch-2026-01-15
        """
        setup_logging(verbose, quiet)
        
        try:
            with open(file, 'r') as f:
                requests_data = json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            print_error(f"Failed to load requests file: {e}")
            sys.exit(1)
        
        if not isinstance(requests_data, list):
            print_error("JSON file must contain an array of request objects")
            sys.exit(1)
        
        if len(requests_data) > 10000:
            print_error(f"Maximum 10,000 requests per batch. Got {len(requests_data)}")
            sys.exit(1)
        
        try:
            with MubanAPIClient(ctx.config_manager.get()) as client:
                result = client.submit_bulk_async(requests_data, batch_id)
                
                if output_format == 'json':
                    print_json(result)
                else:
                    submitted = result.get("submitted", 0)
                    failed = result.get("failed", 0)
                    
                    print_success(f"Bulk submission completed!")
                    click.echo(f"  Submitted: {submitted}")
                    click.echo(f"  Failed: {failed}")
                    
                    if batch_id:
                        click.echo(f"  Batch ID: {batch_id}")
                    
                    errors = result.get("errors", [])
                    if errors and not quiet:
                        click.echo("\nErrors:")
                        for err in errors[:10]:  # Show first 10 errors
                            click.echo(f"  • {err}")
                        if len(errors) > 10:
                            click.echo(f"  ... and {len(errors) - 10} more errors")
                    
        except PermissionDeniedError:
            print_error("Permission denied. This operation requires appropriate permissions.")
            sys.exit(1)
        except MubanError as e:
            print_error(str(e))
            sys.exit(1)

    @async_group.command('list')
    @common_options
    @click.option('--status', '-s', 
                  type=click.Choice(['QUEUED', 'PROCESSING', 'COMPLETED', 'FAILED', 'TIMEOUT']),
                  help='Filter by status')
    @click.option('--user', '-u', help='Filter by user ID')
    @click.option('--template', '-t', help='Filter by template ID')
    @click.option('--since', help='Filter by start time (ISO or relative like "1h", "1d")')
    @click.option('--page', '-p', type=int, default=1, help='Page number')
    @click.option('--size', '-n', type=int, default=20, help='Items per page (max 100)')
    @pass_context
    @require_config
    def async_list(
        ctx: MubanContext,
        verbose: bool,
        quiet: bool,
        output_format: str,
        truncate_length: int,
        status: Optional[str],
        user: Optional[str],
        template: Optional[str],
        since: Optional[str],
        page: int,
        size: int
    ):
        """
        List async requests with optional filtering.
        
        \b
        Examples:
          muban async list
          muban async list --status FAILED --since 1d
          muban async list --template abc123 --format json
        """
        setup_logging(verbose, quiet)
        fmt = OutputFormat(output_format)
        
        since_dt = None
        if since:
            since_dt = parse_relative_time(since)
        
        try:
            with MubanAPIClient(ctx.config_manager.get()) as client:
                result = client.get_async_requests(
                    status=status,
                    user_id=user,
                    template_id=template,
                    since=since_dt,
                    page=page,
                    size=size
                )
                
                data = result.get('data', {})
                requests_list = data.get('items', [])
                
                if not quiet and fmt != OutputFormat.JSON:
                    total = data.get('totalItems', 0)
                    total_pages = data.get('totalPages', 1)
                    click.echo(f"\nAsync Requests (Page {page}/{total_pages}, {total} total):\n")
                
                format_async_requests_table(requests_list, fmt, truncate_length)
                    
        except PermissionDeniedError:
            print_error("Permission denied. Admin role required.")
            sys.exit(1)
        except MubanError as e:
            print_error(str(e))
            sys.exit(1)

    @async_group.command('get')
    @common_options
    @click.argument('request_id')
    @pass_context
    @require_config
    def async_get(
        ctx: MubanContext,
        verbose: bool,
        quiet: bool,
        output_format: str,
        truncate_length: int,
        request_id: str
    ):
        """
        Get detailed information about an async request.
        
        \b
        Examples:
          muban async get abc123-uuid
          muban async get abc123-uuid --format json
        """
        setup_logging(verbose, quiet)
        
        try:
            with MubanAPIClient(ctx.config_manager.get()) as client:
                result = client.get_async_request_details(request_id)
                data = result.get('data', {})
                
                if output_format == 'json':
                    print_json(data)
                else:
                    click.echo(f"\n{'=' * 60}")
                    click.secho(f"Async Request Details", fg="cyan", bold=True)
                    click.echo(f"{'=' * 60}")
                    click.echo(f"Request ID:     {data.get('requestId', '-')}")
                    click.echo(f"Correlation ID: {data.get('correlationId', '-')}")
                    click.echo(f"Template ID:    {data.get('templateId', '-')}")
                    click.echo(f"Format:         {data.get('format', '-')}")
                    click.echo(f"User:           {data.get('userId', '-')}")
                    click.echo(f"Status:         {format_async_status(data.get('status', '-'))}")
                    click.echo(f"Priority:       {data.get('priority', '-')}")
                    click.echo(f"Retry Count:    {data.get('retryCount', 0)}")
                    click.echo()
                    click.echo(f"Created:        {format_datetime(data.get('createdAt'))}")
                    click.echo(f"Started:        {format_datetime(data.get('startedAt'))}")
                    click.echo(f"Completed:      {format_datetime(data.get('completedAt'))}")
                    
                    elapsed = data.get('elapsedMs')
                    if elapsed:
                        click.echo(f"Elapsed:        {elapsed}ms")
                    
                    error_msg = data.get('errorMessage')
                    if error_msg:
                        click.echo()
                        click.secho("Error:", fg="red")
                        click.echo(f"  {error_msg}")
                    
        except PermissionDeniedError:
            print_error("Permission denied. Admin role required.")
            sys.exit(1)
        except MubanError as e:
            print_error(str(e))
            sys.exit(1)

    @async_group.command('workers')
    @common_options
    @pass_context
    @require_config
    def async_workers(ctx: MubanContext, verbose: bool, quiet: bool, output_format: str, truncate_length: int):
        """
        Get worker thread status (requires admin role).
        
        Shows JMS listener container status and currently processing requests.
        """
        setup_logging(verbose, quiet)
        
        try:
            with MubanAPIClient(ctx.config_manager.get()) as client:
                result = client.get_async_workers()
                data = result.get('data', {})
                
                if output_format == 'json':
                    print_json(data)
                else:
                    click.echo(f"\n{'=' * 60}")
                    click.secho("Async Workers Status", fg="cyan", bold=True)
                    click.echo(f"{'=' * 60}")
                    
                    running = data.get('running', False)
                    status_color = "green" if running else "red"
                    click.echo(f"Status:          {click.style('Running' if running else 'Stopped', fg=status_color)}")
                    click.echo(f"Active Workers:  {data.get('activeWorkers', 0)}")
                    click.echo(f"Max Workers:     {data.get('maxWorkers', '-')}")
                    
                    processing = data.get('processing', [])
                    if processing:
                        click.echo(f"\nCurrently Processing ({len(processing)}):")
                        for p in processing:
                            click.echo(f"  • {p.get('requestId', '-')} - {p.get('templateId', '-')} ({p.get('elapsedMs', 0)}ms)")
                    else:
                        click.echo("\nNo requests currently processing.")
                    
        except PermissionDeniedError:
            print_error("Permission denied. Admin role required.")
            sys.exit(1)
        except MubanError as e:
            print_error(str(e))
            sys.exit(1)

    @async_group.command('metrics')
    @common_options
    @pass_context
    @require_config
    def async_metrics(ctx: MubanContext, verbose: bool, quiet: bool, output_format: str, truncate_length: int):
        """
        Get async metrics dashboard (requires admin role).
        
        Shows queue depth, performance metrics, throughput, and error rates.
        """
        setup_logging(verbose, quiet)
        
        try:
            with MubanAPIClient(ctx.config_manager.get()) as client:
                result = client.get_async_metrics()
                
                # The metrics endpoint may return data directly or wrapped
                data = result.get('data', result) if isinstance(result, dict) else result
                
                if output_format == 'json':
                    print_json(data)
                else:
                    click.echo(f"\n{'=' * 60}")
                    click.secho("Async Metrics Dashboard", fg="cyan", bold=True)
                    click.echo(f"{'=' * 60}")
                    
                    # Queue metrics
                    queue = data.get('queue', {})
                    click.echo("\nQueue:")
                    click.echo(f"  Depth:     {queue.get('depth', 0)}")
                    click.echo(f"  Enqueued:  {queue.get('enqueued', 0)}")
                    click.echo(f"  Dequeued:  {queue.get('dequeued', 0)}")
                    
                    # Performance
                    perf = data.get('performance', {})
                    click.echo("\nPerformance:")
                    click.echo(f"  Avg Processing Time: {int(perf.get('avgProcessingTimeMs', 0))}ms")
                    click.echo(f"  Max Processing Time: {int(perf.get('maxProcessingTimeMs', 0))}ms")
                    click.echo(f"  Min Processing Time: {int(perf.get('minProcessingTimeMs', 0))}ms")
                    
                    # Throughput
                    throughput = data.get('throughput', {})
                    click.echo("\nThroughput:")
                    click.echo(f"  Per Minute: {throughput.get('perMinute', 0)}")
                    click.echo(f"  Per Hour:   {throughput.get('perHour', 0)}")
                    
                    # Error rates
                    errors = data.get('errors', {})
                    click.echo("\nErrors:")
                    click.echo(f"  Total:      {errors.get('total', 0)}")
                    click.echo(f"  Rate:       {errors.get('rate', 0):.2%}" if errors.get('rate') else "  Rate:       0%")
                    
        except PermissionDeniedError:
            print_error("Permission denied. Admin role required.")
            sys.exit(1)
        except MubanError as e:
            print_error(str(e))
            sys.exit(1)

    @async_group.command('health')
    @common_options
    @pass_context
    @require_config
    def async_health(ctx: MubanContext, verbose: bool, quiet: bool, output_format: str, truncate_length: int):
        """
        Get async system health status (requires admin role).
        
        Shows health check for async components (ActiveMQ, queue, workers).
        """
        setup_logging(verbose, quiet)
        
        try:
            with MubanAPIClient(ctx.config_manager.get()) as client:
                result = client.get_async_health()
                data = result.get('data', {})
                
                if output_format == 'json':
                    print_json(data)
                else:
                    status = data.get('status', 'UNKNOWN')
                    status_color = {
                        'UP': 'green',
                        'DOWN': 'red',
                        'DEGRADED': 'yellow',
                    }.get(status, 'white')
                    
                    click.echo(f"\n{'=' * 60}")
                    click.secho("Async System Health", fg="cyan", bold=True)
                    click.echo(f"{'=' * 60}")
                    click.echo(f"Status: {click.style(status, fg=status_color, bold=True)}")
                    
                    components = data.get('components', {})
                    if components:
                        click.echo("\nComponents:")
                        for name, comp in components.items():
                            comp_status = comp.get('status', 'UNKNOWN')
                            comp_color = 'green' if comp_status == 'UP' else 'red'
                            click.echo(f"  {name}: {click.style(comp_status, fg=comp_color)}")
                            details = comp.get('details', {})
                            for k, v in details.items():
                                click.echo(f"    {k}: {v}")
                    
        except PermissionDeniedError:
            print_error("Permission denied. Admin role required.")
            sys.exit(1)
        except MubanError as e:
            print_error(str(e))
            sys.exit(1)

    @async_group.command('errors')
    @common_options
    @click.option('--since', help='Show errors since (ISO or relative like "1h", "24h")')
    @click.option('--page', '-p', type=int, default=1, help='Page number')
    @click.option('--size', '-n', type=int, default=20, help='Items per page')
    @pass_context
    @require_config
    def async_errors(
        ctx: MubanContext,
        verbose: bool,
        quiet: bool,
        output_format: str,
        truncate_length: int,
        since: Optional[str],
        page: int,
        size: int
    ):
        """
        Get async error log (requires admin role).
        
        Shows failed and timed-out async requests for troubleshooting.
        
        \b
        Examples:
          muban async errors
          muban async errors --since 24h
          muban async errors --since 2026-01-14T00:00:00
        """
        setup_logging(verbose, quiet)
        fmt = OutputFormat(output_format)
        
        since_dt = None
        if since:
            since_dt = parse_relative_time(since)
        
        try:
            with MubanAPIClient(ctx.config_manager.get()) as client:
                result = client.get_async_errors(since=since_dt, page=page, size=size)
                data = result.get('data', {})
                requests_list = data.get('items', [])
                
                if not quiet and fmt == OutputFormat.TABLE:
                    total = data.get('totalItems', 0)
                    total_pages = data.get('totalPages', 1)
                    click.echo(f"\nAsync Errors (Page {page}/{total_pages}, {total} total):\n")
                
                if fmt == OutputFormat.JSON:
                    print_json(requests_list)
                elif not requests_list:
                    print_info("No errors found.")
                else:
                    headers = ["Request ID", "Template", "Status", "Error", "Time"]
                    rows = []
                    # For CSV, don't truncate data
                    if fmt == OutputFormat.CSV:
                        for req in requests_list:
                            rows.append([
                                str(req.get("requestId", "-")),
                                str(req.get("templateId", "-")),
                                req.get("status", "-"),
                                req.get("errorMessage", "-"),
                                format_datetime(req.get("completedAt"))[:16] if req.get("completedAt") else "-",
                            ])
                        print_csv(headers, rows)
                    elif truncate_length > 0:
                        for req in requests_list:
                            rows.append([
                                truncate_string(str(req.get("requestId", "-")), 36),
                                truncate_string(str(req.get("templateId", "-")), truncate_length),
                                format_async_status(req.get("status", "-")),
                                truncate_string(req.get("errorMessage", "-"), truncate_length),
                                format_datetime(req.get("completedAt"))[:16] if req.get("completedAt") else "-",
                            ])
                        print_table(headers, rows)
                    else:
                        for req in requests_list:
                            rows.append([
                                str(req.get("requestId", "-")),
                                str(req.get("templateId", "-")),
                                format_async_status(req.get("status", "-")),
                                req.get("errorMessage", "-"),
                                format_datetime(req.get("completedAt"))[:16] if req.get("completedAt") else "-",
                            ])
                        print_table(headers, rows)
                    
        except PermissionDeniedError:
            print_error("Permission denied. Admin role required.")
            sys.exit(1)
        except MubanError as e:
            print_error(str(e))
            sys.exit(1)
