"""
Template packaging commands.

This module provides commands for packaging JRXML templates into
deployable ZIP packages.
"""

import click
from pathlib import Path
from typing import Optional, Tuple, List

from ..packager import JRXMLPackager, PackageResult, FontSpec
from ..utils import print_success, print_error, print_warning, print_info
from ..config import get_config_manager


def validate_font_options(ctx, param, value):
    """Callback to validate font options are provided in matching sets."""
    return value


@click.command('package')
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
@click.option(
    '--upload', '-u',
    is_flag=True,
    help='Upload the package after creation'
)
@click.option(
    '--name', '-n',
    help='Template name for upload (default: filename without extension)'
)
@click.option(
    '--author', '-a',
    help='Template author for upload (uses default_author from config if set)'
)
@click.option(
    '--font-file',
    multiple=True,
    type=click.Path(exists=True, path_type=Path),
    help='Path to font file (TTF/OTF). Can be repeated for multiple fonts.'
)
@click.option(
    '--font-name',
    multiple=True,
    type=str,
    help='Font family name as used in JRXML. Can be repeated.'
)
@click.option(
    '--font-face',
    multiple=True,
    type=click.Choice(['normal', 'bold', 'italic', 'boldItalic']),
    help='Font face type. Can be repeated.'
)
@click.option(
    '--embedded/--no-embedded',
    'font_embedded',
    multiple=True,
    default=None,
    help='Whether font should be embedded in PDF. Can be repeated.'
)
@click.option(
    '--fonts-xml',
    type=click.Path(exists=True, path_type=Path),
    help='Path to existing fonts.xml file to include in package.'
)
def package_cmd(
    jrxml_file: Path,
    output: Optional[Path],
    dry_run: bool,
    verbose: bool,
    reports_dir_param: str,
    upload: bool,
    name: Optional[str],
    author: Optional[str],
    font_file: Tuple[Path, ...],
    font_name: Tuple[str, ...],
    font_face: Tuple[str, ...],
    font_embedded: Tuple[bool, ...],
    fonts_xml: Optional[Path]
):
    """
    Package a JRXML template into a deployable ZIP package.
    
    This command analyzes the JRXML file to find all referenced assets
    (images, subreports) and packages them together in a ZIP file
    that can be uploaded to the Muban service.
    
    \b
    Examples:
      # Basic packaging (creates template.zip)
      muban package template.jrxml
      
      # Specify output file
      muban package template.jrxml -o my-package.zip
      
      # Preview what would be included (no ZIP created)
      muban package template.jrxml --dry-run
      
      # Use custom path parameter name
      muban package template.jrxml --reports-dir-param BASE_PATH
      
      # Package and upload in one step
      muban package template.jrxml --upload
      muban package template.jrxml -u --name "My Report" --author "John"
      
      # Include custom fonts in the package
      muban package template.jrxml \\
        --font-file Arial.ttf --font-name Arial --font-face normal --embedded \\
        --font-file Arial_Bold.ttf --font-name Arial --font-face bold --embedded
    
    \b
    The packager automatically:
      - Detects image references (PNG, JPG, SVG, etc.)
      - Detects dynamic directories (includes all files)
      - Preserves the asset directory structure
      - Warns about missing assets
      
    \b
    Font options (--font-file, --font-name, --font-face, --embedded) must be
    provided in matching sets. Multiple fonts with the same name are grouped
    into a single font family with multiple faces.
    """
    # Resolve paths
    jrxml_file = jrxml_file.resolve()
    
    if verbose:
        print_info(f"Packaging: {jrxml_file.name}")
        print_info(f"Working directory: {jrxml_file.parent}")
    
    # Parse font options
    fonts: List[FontSpec] = []
    if font_file:
        # Validate matching counts
        counts = [len(font_file), len(font_name), len(font_face)]
        if len(set(counts)) != 1:
            print_error(
                f"Font options count mismatch: "
                f"--font-file ({len(font_file)}), "
                f"--font-name ({len(font_name)}), "
                f"--font-face ({len(font_face)})"
            )
            raise SystemExit(1)
        
        # Handle embedded flag - use True as default if not specified enough times
        embedded_values = list(font_embedded) if font_embedded else []
        while len(embedded_values) < len(font_file):
            embedded_values.append(True)  # Default to embedded
        
        for i, (f_file, f_name, f_face) in enumerate(zip(font_file, font_name, font_face)):
            fonts.append(FontSpec(
                file_path=Path(f_file).resolve(),
                name=f_name,
                face=f_face,
                embedded=embedded_values[i]
            ))
        
        if verbose:
            print_info(f"Including {len(fonts)} font file(s)")
    
    # Create packager and run
    packager = JRXMLPackager(reports_dir_param=reports_dir_param)
    result = packager.package(jrxml_file, output, dry_run=dry_run, fonts=fonts, fonts_xml_path=fonts_xml)
    
    # Display results
    _display_result(result, verbose, dry_run, fonts)
    
    # Exit with appropriate code
    if not result.success:
        raise SystemExit(1)
    
    # Upload if requested
    if upload and result.success and not dry_run:
        _upload_package(result.output_path, name, author, verbose)


def _upload_package(output_path: Path, name: Optional[str], author: Optional[str], verbose: bool):
    """Upload the packaged template to the server."""
    from ..api import MubanAPIClient
    from ..exceptions import MubanError, PermissionDeniedError, AuthenticationError
    
    config = get_config_manager().get()
    
    if not config.is_authenticated():
        print_error("Not authenticated. Run 'muban login' first.")
        raise SystemExit(1)
    
    # Use filename stem as default name
    template_name = name or output_path.stem
    # Use config default_author if author not specified
    template_author = author or config.default_author
    
    if not template_author:
        print_error("Author is required. Use --author or set default_author in config.")
        raise SystemExit(1)
    
    click.echo()
    print_info(f"Uploading package to server...")
    if verbose:
        print_info(f"  Name: {template_name}")
        print_info(f"  Author: {template_author}")
    
    try:
        with MubanAPIClient(config) as client:
            result = client.upload_template(
                file_path=output_path,
                name=template_name,
                author=template_author,
            )
            
            template = result.get('data', {})
            print_success("Template uploaded successfully!")
            click.echo(f"  ID: {template.get('id')}")
            click.echo(f"  Name: {template.get('name')}")
            
    except AuthenticationError:
        print_error("Authentication failed. Run 'muban login' to re-authenticate.")
        raise SystemExit(1)
    except PermissionDeniedError:
        print_error("Permission denied. Manager role required for upload.")
        raise SystemExit(1)
    except MubanError as e:
        print_error(f"Upload failed: {e}")
        raise SystemExit(1)


def _display_result(result: PackageResult, verbose: bool, dry_run: bool, fonts: Optional[List[FontSpec]] = None):
    """Display packaging results to the user."""
    
    fonts = fonts or []
    
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
    # Show fonts info
    if fonts:
        click.echo()
        # Group by font family name
        font_families = {}
        for font in fonts:
            if font.name not in font_families:
                font_families[font.name] = []
            font_families[font.name].append(font)
        
        unique_files = len({f.file_path for f in fonts})
        click.echo(click.style(f"Fonts included: {len(font_families)} family(ies), {unique_files} file(s)", bold=True))
        if verbose:
            for family_name, family_fonts in font_families.items():
                faces = [f.face for f in family_fonts]
                embedded = family_fonts[0].embedded
                click.echo(f"  ✓ {family_name} ({', '.join(faces)}) - {'embedded' if embedded else 'not embedded'}")
    
    # Final status
    click.echo()
    if result.success:
        if dry_run:
            print_info(f"Dry run complete. Would create: {result.output_path}")
            if fonts:
                unique_font_files = len({f.file_path for f in fonts})
                print_info(f"Would include fonts.xml + {unique_font_files} font file(s)")
        else:
            total_assets = len(result.assets_included)
            unique_font_count = len({f.file_path for f in fonts}) if fonts else 0
            font_info = f" + {unique_font_count} fonts" if fonts else ""
            print_success(f"Package created: {result.output_path}")
            click.echo(f"  Contents: 1 JRXML + {total_assets} assets{font_info}")
            
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
        print_error("Packaging failed.")


def register_package_commands(cli):
    """Register package commands with the CLI."""
    cli.add_command(package_cmd)
