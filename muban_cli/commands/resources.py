"""
Resource commands (fonts, ICC profiles) for Muban CLI.
"""
import sys

import click

from ..api import MubanAPIClient
from ..exceptions import MubanError
from ..utils import (
    OutputFormat,
    print_csv,
    print_error,
    print_json,
    print_table,
    setup_logging,
)
from . import common_options, pass_context, require_config, MubanContext


def register_resource_commands(cli: click.Group) -> None:
    """Register resource commands with the CLI."""
    
    @cli.command('fonts')
    @click.option(
        '--show-all', '-a',
        is_flag=True,
        help='Show all fonts including template-bundled ones (default: only server fonts)'
    )
    @common_options
    @pass_context
    @require_config
    def list_fonts(ctx: MubanContext, show_all: bool, verbose: bool, quiet: bool, output_format: str, truncate_length: int):
        """List available fonts for document generation.
        
        By default, shows only server-installed fonts (source=SERVER).
        Use --show-all to include fonts bundled with templates.
        """
        setup_logging(verbose, quiet)
        fmt = OutputFormat(output_format)
        
        try:
            with MubanAPIClient(ctx.config_manager.get()) as client:
                result = client.get_fonts()
                fonts = result.get('data', [])
                
                # Filter by source unless --show-all is specified
                if not show_all:
                    fonts = [f for f in fonts if f.get('source') == 'SERVER']
                
                if fmt == OutputFormat.JSON:
                    print_json(fonts)
                else:
                    total = len(fonts)
                    # Only show Source column when displaying all fonts (mixed sources)
                    if show_all:
                        headers = ["Name", "Faces", "PDF Embedded", "Source"]
                        rows = [
                            [
                                font.get('name', '-'),
                                ', '.join(font.get('faces', [])),
                                'Yes' if font.get('pdfEmbedded') else 'No',
                                font.get('source', '-')
                            ]
                            for font in fonts
                        ]
                    else:
                        headers = ["Name", "Faces", "PDF Embedded"]
                        rows = [
                            [
                                font.get('name', '-'),
                                ', '.join(font.get('faces', [])),
                                'Yes' if font.get('pdfEmbedded') else 'No'
                            ]
                            for font in fonts
                        ]
                    if fmt == OutputFormat.CSV:
                        print_csv(headers, rows)
                    else:
                        filter_note = "" if show_all else " (server fonts only, use --show-all for all)"
                        click.echo(f"\nFonts ({total} total){filter_note}:\n")
                        print_table(headers, rows)
                    
        except MubanError as e:
            print_error(str(e))
            sys.exit(1)

    @cli.command('icc-profiles')
    @common_options
    @pass_context
    @require_config
    def list_icc_profiles(ctx: MubanContext, verbose: bool, quiet: bool, output_format: str, truncate_length: int):
        """List available ICC color profiles for PDF export."""
        setup_logging(verbose, quiet)
        fmt = OutputFormat(output_format)
        
        try:
            with MubanAPIClient(ctx.config_manager.get()) as client:
                result = client.get_icc_profiles()
                profiles = result.get('data', [])
                
                if fmt == OutputFormat.JSON:
                    print_json(profiles)
                elif fmt == OutputFormat.CSV:
                    headers = ["Profile Name"]
                    rows = [[profile] for profile in profiles]
                    print_csv(headers, rows)
                else:
                    total = len(profiles)
                    click.echo(f"\nICC Profiles ({total} total):\n")
                    for profile in profiles:
                        click.echo(f"  • {profile}")
                    
        except MubanError as e:
            print_error(str(e))
            sys.exit(1)
