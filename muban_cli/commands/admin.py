"""
Admin commands for Muban CLI.
"""
import sys

import click

from ..api import MubanAPIClient
from ..exceptions import MubanError, PermissionDeniedError, ValidationError
from ..utils import (
    OutputFormat,
    confirm_action,
    print_error,
    print_info,
    print_json,
    print_success,
    setup_logging,
)
from . import common_options, pass_context, require_config, MubanContext


def register_admin_commands(cli: click.Group) -> None:
    """Register admin commands with the CLI."""
    
    @cli.group('admin')
    def admin():
        """Administrative commands (requires admin role)."""
        pass

    @admin.command('verify-integrity')
    @common_options
    @click.argument('template_id')
    @pass_context
    @require_config
    def verify_integrity(
        ctx: MubanContext,
        verbose: bool,
        quiet: bool,
        output_format: str,
        truncate_length: int,
        template_id: str
    ):
        """Verify template file integrity."""
        setup_logging(verbose, quiet)
        fmt = OutputFormat(output_format)
        
        try:
            with MubanAPIClient(ctx.config_manager.get()) as client:
                result = client.verify_template_integrity(template_id)
                
                if fmt == OutputFormat.JSON:
                    print_json(result)
                else:
                    print_success("Template integrity verified.")
                    
        except ValidationError as e:
            print_error(f"Integrity check failed: {e}")
            sys.exit(1)
        except PermissionDeniedError:
            print_error("Permission denied. Admin role required.")
            sys.exit(1)
        except MubanError as e:
            print_error(str(e))
            sys.exit(1)

    @admin.command('regenerate-digest')
    @common_options
    @click.argument('template_id')
    @pass_context
    @require_config
    def regenerate_digest(
        ctx: MubanContext,
        verbose: bool,
        quiet: bool,
        output_format: str,
        truncate_length: int,
        template_id: str
    ):
        """Regenerate integrity digest for a template."""
        setup_logging(verbose, quiet)
        fmt = OutputFormat(output_format)
        
        try:
            with MubanAPIClient(ctx.config_manager.get()) as client:
                result = client.regenerate_template_digest(template_id)
                
                if fmt == OutputFormat.JSON:
                    print_json(result)
                else:
                    print_success("Digest regenerated successfully.")
                    
        except PermissionDeniedError:
            print_error("Permission denied. Admin role required.")
            sys.exit(1)
        except MubanError as e:
            print_error(str(e))
            sys.exit(1)

    @admin.command('regenerate-all-digests')
    @common_options
    @click.option('--yes', '-y', is_flag=True, help='Skip confirmation')
    @pass_context
    @require_config
    def regenerate_all_digests(
        ctx: MubanContext,
        verbose: bool,
        quiet: bool,
        output_format: str,
        truncate_length: int,
        yes: bool
    ):
        """Regenerate integrity digests for all templates."""
        setup_logging(verbose, quiet)
        fmt = OutputFormat(output_format)
        
        if not yes:
            if not confirm_action("Regenerate digests for ALL templates?"):
                print_info("Cancelled.")
                return
        
        try:
            with MubanAPIClient(ctx.config_manager.get()) as client:
                result = client.regenerate_all_digests()
                
                if fmt == OutputFormat.JSON:
                    print_json(result)
                else:
                    print_success("All digests regenerated.")
                    
        except PermissionDeniedError:
            print_error("Permission denied. Admin role required.")
            sys.exit(1)
        except MubanError as e:
            print_error(str(e))
            sys.exit(1)

    @admin.command('server-config')
    @common_options
    @pass_context
    @require_config
    def server_config(ctx: MubanContext, verbose: bool, quiet: bool, output_format: str, truncate_length: int):
        """Get server configuration."""
        setup_logging(verbose, quiet)
        
        try:
            with MubanAPIClient(ctx.config_manager.get()) as client:
                result = client.get_server_config()
                print_json(result.get('data', {}))
                    
        except PermissionDeniedError:
            print_error("Permission denied. Admin role required.")
            sys.exit(1)
        except MubanError as e:
            print_error(str(e))
            sys.exit(1)
