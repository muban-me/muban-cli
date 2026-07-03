"""
Document generation commands for Muban CLI.
"""
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import click

from ..api import MubanAPIClient
from ..exceptions import MubanError, TemplateNotFoundError, ValidationError
from ..utils import (
    load_json_file,
    parse_parameters,
    print_error,
    print_info,
    print_success,
    setup_logging,
)
from . import common_options, pass_context, require_config, MubanContext


def register_generate_commands(cli: click.Group) -> None:
    """Register document generation commands with the CLI."""
    
    @cli.command('generate')
    @common_options
    @click.argument('template_id')
    @click.option(
        '--output-format', '-F',
        'doc_format',
        type=click.Choice(['pdf', 'xlsx', 'docx', 'rtf', 'html', 'txt', 'png'], case_sensitive=False),
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
    @click.option('--pdf-duplex-padding', is_flag=True, help='Pad PDF to even page count for duplex printing')
    @click.option('--pdf-image-compression', type=float, help='JPEG re-compression quality (0.0-1.0)')
    @click.option('--pdf-flatten-transparency', is_flag=True, help='Strip redundant transparency groups from PDF')
    @click.option('--pdf-font-substitute', help='Font family to substitute for non-embedded base-14 fonts')
    @click.option('--pdf-cmyk-profile', help='ICC profile name for RGB to CMYK conversion')
    @click.option('--txt-char-width', type=float, help='TXT character cell width in pixels (default: 8.0)')
    @click.option('--txt-char-height', type=float, help='TXT character cell height in pixels (default: 13.948)')
    @click.option('--txt-page-width-chars', type=int, help='TXT page width in characters (overrides char width)')
    @click.option('--txt-page-height-chars', type=int, help='TXT page height in character rows (overrides char height)')
    @click.option('--txt-trim-line-right', is_flag=True, help='Trim trailing whitespace from TXT lines')
    @click.option('--png-zoom', type=float, help='PNG zoom ratio for output resolution (0.5-4.0, default: 1.0)')
    @pass_context
    @require_config
    def generate_document(
        ctx: MubanContext,
        verbose: bool,
        quiet: bool,
        output_format: str,
        truncate_length: int,
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
        pdf_owner_password: Optional[str],
        pdf_duplex_padding: bool,
        pdf_image_compression: Optional[float],
        pdf_flatten_transparency: bool,
        pdf_font_substitute: Optional[str],
        pdf_cmyk_profile: Optional[str],
        txt_char_width: Optional[float],
        txt_char_height: Optional[float],
        txt_page_width_chars: Optional[int],
        txt_page_height_chars: Optional[int],
        txt_trim_line_right: bool,
        png_zoom: Optional[float],
    ):
        """
        Generate a document from a template.
        
        \b
        Examples:
          muban generate abc123 -p title="Sales Report" -p year=2025
          muban generate abc123 --params-file params.json -F xlsx
          muban generate abc123 --data-file data.json -o report.pdf
          muban generate abc123 --pdf-pdfa PDF/A-1b --locale pl_PL
          muban generate abc123 -F txt --txt-page-width-chars 80 --txt-trim-line-right
          muban generate abc123 -F png --png-zoom 2.0 -o pages.zip
          muban generate abc123 --pdf-image-compression 0.75 --pdf-flatten-transparency
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
        if any([pdf_pdfa, pdf_password, pdf_owner_password, pdf_duplex_padding,
                pdf_image_compression, pdf_flatten_transparency, pdf_font_substitute, pdf_cmyk_profile]):
            pdf_options = {}
            if pdf_pdfa:
                pdf_options['pdfaConformance'] = pdf_pdfa
            if pdf_password:
                pdf_options['userPassword'] = pdf_password
            if pdf_owner_password:
                pdf_options['ownerPassword'] = pdf_owner_password
            if pdf_duplex_padding:
                pdf_options['duplexPadding'] = True
            if pdf_image_compression is not None:
                pdf_options['imageCompressionQuality'] = pdf_image_compression
            if pdf_flatten_transparency:
                pdf_options['flattenTransparency'] = True
            if pdf_font_substitute:
                pdf_options['fontEmbeddingSubstitute'] = pdf_font_substitute
            if pdf_cmyk_profile:
                pdf_options['cmykConversionProfile'] = pdf_cmyk_profile
        
        # Build TXT options
        txt_options = None
        if any([txt_char_width, txt_char_height, txt_page_width_chars, txt_page_height_chars, txt_trim_line_right]):
            txt_options = {}
            if txt_char_width is not None:
                txt_options['characterWidth'] = txt_char_width
            if txt_char_height is not None:
                txt_options['characterHeight'] = txt_char_height
            if txt_page_width_chars is not None:
                txt_options['pageWidthInChars'] = txt_page_width_chars
            if txt_page_height_chars is not None:
                txt_options['pageHeightInChars'] = txt_page_height_chars
            if txt_trim_line_right:
                txt_options['trimLineRight'] = True
        
        # Build PNG options
        png_options = None
        if png_zoom is not None:
            png_options = {'zoomRatio': png_zoom}
        
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
                    txt_export_options=txt_options,
                    png_export_options=png_options,
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
