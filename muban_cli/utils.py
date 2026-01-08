"""
Utility functions for Muban CLI.

Provides helpers for output formatting, file operations, and common tasks.
"""

import json
import sys
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from enum import Enum

import click


class OutputFormat(str, Enum):
    """Output format options."""
    TABLE = "table"
    JSON = "json"
    YAML = "yaml"
    CSV = "csv"


class LogLevel(str, Enum):
    """Log level options."""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


def setup_logging(verbose: bool = False, quiet: bool = False) -> None:
    """
    Configure logging based on verbosity settings.
    
    Args:
        verbose: Enable verbose (debug) output
        quiet: Suppress all but error output
    """
    if quiet:
        level = logging.ERROR
    elif verbose:
        level = logging.DEBUG
    else:
        level = logging.INFO
    
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s' if verbose else '%(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Reduce noise from third-party libraries
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)


def format_datetime(dt: Union[str, datetime, None]) -> str:
    """
    Format a datetime for display.
    
    Args:
        dt: Datetime string or object
    
    Returns:
        Formatted datetime string
    """
    if dt is None:
        return "-"
    
    if isinstance(dt, str):
        try:
            dt = datetime.fromisoformat(dt.replace('Z', '+00:00'))
        except ValueError:
            return dt
    
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def format_file_size(size: Optional[int]) -> str:
    """
    Format file size in human-readable format.
    
    Args:
        size: Size in bytes
    
    Returns:
        Formatted size string
    """
    if size is None:
        return "-"
    
    size_float: float = float(size)
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_float < 1024:
            return f"{size_float:.1f} {unit}"
        size_float /= 1024
    return f"{size_float:.1f} TB"


def truncate_string(s: str, max_length: int = 50) -> str:
    """
    Truncate a string to maximum length.
    
    Args:
        s: String to truncate
        max_length: Maximum length
    
    Returns:
        Truncated string
    """
    if s is None:
        return "-"
    if len(s) <= max_length:
        return s
    return s[:max_length - 3] + "..."


def _strip_ansi(s: str) -> str:
    """Remove ANSI escape codes from string for length calculation."""
    import re
    return re.sub(r'\x1b\[[0-9;]*m', '', str(s))


def _visible_len(s: str) -> int:
    """Get visible length of string (excluding ANSI codes)."""
    return len(_strip_ansi(s))


def print_table(
    headers: List[str],
    rows: List[List[str]],
    widths: Optional[List[int]] = None
) -> None:
    """
    Print a formatted table.
    
    Args:
        headers: Column headers
        rows: Table rows
        widths: Optional column widths
    """
    if not widths:
        # Calculate column widths (accounting for ANSI codes)
        widths = [len(h) for h in headers]
        for row in rows:
            for i, cell in enumerate(row):
                if i < len(widths):
                    widths[i] = max(widths[i], _visible_len(str(cell)))
    
    # Print header
    header_line = " | ".join(h.ljust(widths[i]) for i, h in enumerate(headers))
    click.echo(header_line)
    click.echo("-" * len(header_line))
    
    # Print rows (pad based on visible length, not raw length)
    for row in rows:
        cells = []
        for i, cell in enumerate(row):
            cell_str = str(cell)
            visible_width = _visible_len(cell_str)
            padding = widths[i] - visible_width
            cells.append(cell_str + " " * padding)
        click.echo(" | ".join(cells))


def print_json(data: Any, indent: int = 2) -> None:
    """
    Print data as formatted JSON.
    
    Args:
        data: Data to print
        indent: Indentation level
    """
    click.echo(json.dumps(data, indent=indent, default=str))


def print_success(message: str) -> None:
    """Print a success message."""
    click.secho(f"✓ {message}", fg="green")


def print_error(message: str, details: Optional[str] = None) -> None:
    """Print an error message."""
    click.secho(f"✗ {message}", fg="red", err=True)
    if details:
        click.secho(f"  {details}", fg="red", dim=True, err=True)


def print_warning(message: str) -> None:
    """Print a warning message."""
    click.secho(f"⚠ {message}", fg="yellow")


def print_info(message: str) -> None:
    """Print an info message."""
    click.secho(f"ℹ {message}", fg="blue")


def confirm_action(message: str, default: bool = False) -> bool:
    """
    Confirm a potentially destructive action.
    
    Args:
        message: Confirmation message
        default: Default value if just Enter is pressed
    
    Returns:
        True if confirmed
    """
    return click.confirm(message, default=default)


def format_template_list(templates: List[Dict[str, Any]], output_format: OutputFormat) -> None:
    """
    Format and print template list.
    
    Args:
        templates: List of template dictionaries
        output_format: Output format
    """
    if output_format == OutputFormat.JSON:
        print_json(templates)
        return
    
    if not templates:
        print_info("No templates found.")
        return
    
    headers = ["ID", "Name", "Author", "Size", "Created"]
    rows = []
    
    for tpl in templates:
        rows.append([
            truncate_string(tpl.get("id", "-"), 36),
            truncate_string(tpl.get("name", "-"), 40),
            truncate_string(tpl.get("author", "-"), 20),
            format_file_size(tpl.get("fileSize")),
            format_datetime(tpl.get("created")),
        ])
    
    print_table(headers, rows)


def format_template_detail(template: Dict[str, Any], output_format: OutputFormat) -> None:
    """
    Format and print template details.
    
    Args:
        template: Template dictionary
        output_format: Output format
    """
    if output_format == OutputFormat.JSON:
        print_json(template)
        return
    
    click.echo(f"\n{'=' * 60}")
    click.secho(f"Template: {template.get('name', 'Unknown')}", fg="cyan", bold=True)
    click.echo(f"{'=' * 60}")
    click.echo(f"ID:        {template.get('id', '-')}")
    click.echo(f"Author:    {template.get('author', '-')}")
    click.echo(f"Size:      {format_file_size(template.get('fileSize'))}")
    click.echo(f"Created:   {format_datetime(template.get('created'))}")
    click.echo(f"Path:      {template.get('templatePath', '-')}")
    
    if template.get('metadata'):
        click.echo(f"\nMetadata:")
        click.echo(f"  {template.get('metadata')}")


def format_parameters(parameters: List[Dict[str, Any]], output_format: OutputFormat) -> None:
    """
    Format and print template parameters.
    
    Args:
        parameters: List of parameter dictionaries
        output_format: Output format
    """
    if output_format == OutputFormat.JSON:
        print_json(parameters)
        return
    
    if not parameters:
        print_info("No parameters defined.")
        return
    
    headers = ["Name", "Type", "Default", "Description"]
    rows = []
    
    for param in parameters:
        rows.append([
            param.get("name", "-"),
            param.get("type", "-"),
            truncate_string(str(param.get("defaultValue", "-")), 20),
            truncate_string(param.get("description", "-"), 40),
        ])
    
    print_table(headers, rows)


def format_fields(fields: List[Dict[str, Any]], output_format: OutputFormat) -> None:
    """
    Format and print template fields.
    
    Args:
        fields: List of field dictionaries
        output_format: Output format
    """
    if output_format == OutputFormat.JSON:
        print_json(fields)
        return
    
    if not fields:
        print_info("No fields defined.")
        return
    
    headers = ["Name", "Type", "Required", "Collection", "Description"]
    rows = []
    
    for field in fields:
        rows.append([
            field.get("name", "-"),
            field.get("type", "-"),
            "Yes" if field.get("required") else "No",
            field.get("collectionName", "-"),
            truncate_string(field.get("description", "-"), 30),
        ])
    
    print_table(headers, rows)


def format_audit_logs(logs: List[Dict[str, Any]], output_format: OutputFormat) -> None:
    """
    Format and print audit logs.
    
    Args:
        logs: List of audit log dictionaries
        output_format: Output format
    """
    if output_format == OutputFormat.JSON:
        print_json(logs)
        return
    
    if not logs:
        print_info("No audit logs found.")
        return
    
    headers = ["Timestamp", "Event", "Severity", "User", "Success", "IP"]
    rows = []
    
    for log in logs:
        severity = log.get("severity", "-")
        severity_color = {
            "CRITICAL": "red",
            "HIGH": "yellow",
            "MEDIUM": "blue",
            "LOW": "green"
        }.get(severity, "white")
        
        rows.append([
            format_datetime(log.get("timestamp")),
            truncate_string(log.get("eventType", "-"), 25),
            click.style(severity, fg=severity_color),
            truncate_string(log.get("username", "-"), 15),
            "✓" if log.get("success") else "✗",
            log.get("ipAddress", "-"),
        ])
    
    print_table(headers, rows)


def parse_parameters(param_strings: List[str]) -> List[Dict[str, Any]]:
    """
    Parse parameter strings in name=value format.
    
    Args:
        param_strings: List of "name=value" strings
    
    Returns:
        List of parameter dictionaries
    """
    parameters = []
    
    for param in param_strings:
        if '=' not in param:
            raise ValueError(f"Invalid parameter format: {param}. Use name=value")
        
        name, value = param.split('=', 1)
        name = name.strip()
        value = value.strip()
        
        # Try to parse as JSON for complex types
        try:
            parsed_value = json.loads(value)
        except json.JSONDecodeError:
            # Keep as string
            parsed_value = value
        
        parameters.append({"name": name, "value": parsed_value})
    
    return parameters


def load_json_file(file_path: Path) -> Dict[str, Any]:
    """
    Load JSON data from a file.
    
    Args:
        file_path: Path to JSON file
    
    Returns:
        Parsed JSON data
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in {file_path}: {e}")
    except OSError as e:
        raise ValueError(f"Cannot read file {file_path}: {e}")


def is_uuid(value: str) -> bool:
    """
    Check if a string is a valid UUID.
    
    Args:
        value: String to check
    
    Returns:
        True if valid UUID
    """
    import re
    uuid_pattern = re.compile(
        r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$',
        re.IGNORECASE
    )
    return bool(uuid_pattern.match(value))


def get_exit_code(success: bool) -> int:
    """
    Get appropriate exit code.
    
    Args:
        success: Whether operation was successful
    
    Returns:
        Exit code (0 for success, 1 for failure)
    """
    return 0 if success else 1
