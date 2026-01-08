"""
Template management commands for Muban CLI.

Commands:
- list: List available templates
- get: Get template details
- push: Upload a template
- pull: Download a template
- delete: Delete a template
- search: Search templates
"""

import sys
from pathlib import Path
from typing import Optional

import click

from . import (
    MubanContext,
    pass_context,
    common_options,
    require_config,
    setup_logging,
    print_success,
    print_error,
    print_info,
    print_json,
)
from ..api import MubanAPIClient
from ..exceptions import (
    MubanError,
    ValidationError,
    TemplateNotFoundError,
    PermissionDeniedError,
)
from ..utils import (
    format_template_list,
    format_template_detail,
    format_parameters,
    format_fields,
    confirm_action,
    OutputFormat,
)


def register_template_commands(cli: click.Group) -> None:
    """Register template management commands with the CLI."""
    
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
