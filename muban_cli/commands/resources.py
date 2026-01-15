"""
Resource commands (fonts, ICC profiles) for Muban CLI.
"""
import sys

import click

from ..api import MubanAPIClient
from ..exceptions import MubanError
from ..utils import (
    OutputFormat,
    print_error,
    print_json,
    print_table,
    setup_logging,
)
from . import common_options, pass_context, require_config, MubanContext


def register_resource_commands(cli: click.Group) -> None:
    """Register resource commands with the CLI."""
    
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
                    total = len(fonts)
                    click.echo(f"\nFonts ({total} total):\n")
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
                    total = len(profiles)
                    click.echo(f"\nICC Profiles ({total} total):\n")
                    for profile in profiles:
                        click.echo(f"  • {profile}")
                    
        except MubanError as e:
            print_error(str(e))
            sys.exit(1)
