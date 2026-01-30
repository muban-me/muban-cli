"""
Template compilation commands.

This module provides commands for compiling JRXML templates into
deployable ZIP packages.
"""

import click
from pathlib import Path
from typing import Optional

from ..compiler import JRXMLCompiler, CompilationResult
from ..utils import print_success, print_error, print_warning, print_info


@click.command('compile')
@click.argument('jrxml_file', type=click.Path(exists=True, path_type=Path))
@click.option(
    '-o', '--output',
    type=click.Path(path_type=Path),
    help='Output ZIP file path (default: <jrxml-name>.zip)'
)
@click.option(
    '--dry-run',
    is_flag=True,
    help='Analyze dependencies without creating ZIP'
)
@click.option(
    '-v', '--verbose',
    is_flag=True,
    help='Show detailed progress'
)
@click.option(
    '--reports-dir-param',
    default='REPORTS_DIR',
    help='Name of the path parameter in JRXML (default: REPORTS_DIR)'
)
def compile_cmd(
    jrxml_file: Path,
    output: Optional[Path],
    dry_run: bool,
    verbose: bool,
    reports_dir_param: str
):
    """
    Compile a JRXML template into a deployable ZIP package.
    
    This command analyzes the JRXML file to find all referenced assets
    (images, subreports) and packages them together in a ZIP file
    that can be uploaded to the Muban service.
    
    \b
    Examples:
      # Basic compilation (creates template.zip)
      muban compile template.jrxml
      
      # Specify output file
      muban compile template.jrxml -o my-package.zip
      
      # Preview what would be included (no ZIP created)
      muban compile template.jrxml --dry-run
      
      # Use custom path parameter name
      muban compile template.jrxml --reports-dir-param BASE_PATH
    
    \b
    The compiler automatically:
      - Detects image references (PNG, JPG, SVG, etc.)
      - Detects dynamic directories (includes all files)
      - Preserves the asset directory structure
      - Warns about missing assets
    """
    # Resolve paths
    jrxml_file = jrxml_file.resolve()
    
    if verbose:
        print_info(f"Compiling: {jrxml_file.name}")
        print_info(f"Working directory: {jrxml_file.parent}")
    
    # Create compiler and run
    compiler = JRXMLCompiler(reports_dir_param=reports_dir_param)
    result = compiler.compile(jrxml_file, output, dry_run=dry_run)
    
    # Display results
    _display_result(result, verbose, dry_run)
    
    # Exit with appropriate code
    if not result.success:
        raise SystemExit(1)


def _display_result(result: CompilationResult, verbose: bool, dry_run: bool):
    """Display compilation results to the user."""
    
    # Build a set of included asset paths for quick lookup
    included_paths = set()
    if result.main_jrxml:
        for p in result.assets_included:
            try:
                rel = p.relative_to(result.main_jrxml.parent)
                included_paths.add(str(rel).replace('\\', '/'))
            except ValueError:
                included_paths.add(str(p))
    
    # Show main JRXML
    if verbose and result.main_jrxml:
        click.echo()
        click.echo(click.style("Main template:", bold=True))
        click.echo(f"  {result.main_jrxml.name}")
    
    # Show found assets
    if result.assets_found:
        click.echo()
        click.echo(click.style(f"Assets found: {len(result.assets_found)}", bold=True))
        
        if verbose:
            for asset in result.assets_found:
                # Build source indicator for nested assets
                source_indicator = ""
                if asset.subreport_source:
                    source_indicator = f" [from {asset.subreport_source}]"
                
                # Calculate effective path by simulating cd to source file's dir
                # then applying REPORTS_DIR + asset path, normalized to main template root
                # Use string concatenation (POSIX: "../" + "/path" = "..//path" = "../path")
                if result.main_jrxml:
                    source_dir = asset.source_file.parent
                    combined = asset.reports_dir_value + asset.path
                    # Normalize double slashes (POSIX semantics)
                    while '//' in combined:
                        combined = combined.replace('//', '/')
                    resolved_abs = (source_dir / combined).resolve()
                    try:
                        effective_path = str(resolved_abs.relative_to(result.main_jrxml.parent)).replace('\\', '/')
                    except ValueError:
                        # Path is outside main template dir
                        effective_path = str(resolved_abs).replace('\\', '/')
                else:
                    effective_path = (asset.reports_dir_value + asset.path).replace('\\', '/')
                
                if asset.is_dynamic_dir:
                    # Count files included from this directory
                    files_from_dir = [p for p in included_paths if p.startswith(effective_path)]
                    if files_from_dir:
                        click.echo(click.style(
                            f"  ✓ {effective_path}* (dynamic: {asset.dynamic_param}, {len(files_from_dir)} files included){source_indicator}",
                            fg='cyan'
                        ))
                    else:
                        click.echo(click.style(f"  ✗ {effective_path} (directory not found){source_indicator}", fg='yellow'))
                else:
                    # Check if effective path is in included paths
                    if effective_path in included_paths:
                        click.echo(f"  ✓ {effective_path}{source_indicator}")
                    else:
                        click.echo(click.style(f"  ✗ {effective_path} (missing){source_indicator}", fg='yellow'))
        else:
            # Brief summary
            included_count = len(result.assets_included)
            missing_count = len(result.assets_missing)
            click.echo(f"  Included: {included_count}")
            if missing_count > 0:
                click.echo(click.style(f"  Missing: {missing_count}", fg='yellow'))
    else:
        click.echo()
        print_info("No external assets referenced in the template.")
    
    # Show skipped remote URLs (verbose only)
    if verbose and result.skipped_urls:
        click.echo()
        click.echo(click.style(f"Skipped remote URLs: {len(result.skipped_urls)}", bold=True))
        for url in result.skipped_urls:
            click.echo(click.style(f"  ⊘ {url}", fg='blue'))
    
    # Show skipped fully dynamic expressions (verbose only)
    if verbose and result.skipped_dynamic:
        click.echo()
        click.echo(click.style(f"Skipped dynamic expressions: {len(result.skipped_dynamic)}", bold=True))
        click.echo(click.style("  (Fully runtime-determined paths cannot be resolved at compile time)", fg='bright_black'))
        for expr in result.skipped_dynamic:
            click.echo(click.style(f"  ⊘ {expr}", fg='magenta'))
    
    # Show warnings
    if result.warnings:
        click.echo()
        for warning in result.warnings:
            print_warning(warning)
    
    # Show errors
    if result.errors:
        click.echo()
        for error in result.errors:
            print_error(error)
    
    # Final status
    click.echo()
    if result.success:
        if dry_run:
            print_info(f"Dry run complete. Would create: {result.output_path}")
        else:
            total_assets = len(result.assets_included)
            print_success(f"Package created: {result.output_path}")
            click.echo(f"  Contents: 1 JRXML + {total_assets} assets")
            
            # Show file size
            if result.output_path and result.output_path.exists():
                size = result.output_path.stat().st_size
                if size < 1024:
                    size_str = f"{size} B"
                elif size < 1024 * 1024:
                    size_str = f"{size / 1024:.1f} KB"
                else:
                    size_str = f"{size / (1024 * 1024):.1f} MB"
                click.echo(f"  Size: {size_str}")
    else:
        print_error("Compilation failed.")


def register_compile_commands(cli):
    """Register compile commands with the CLI."""
    cli.add_command(compile_cmd)
