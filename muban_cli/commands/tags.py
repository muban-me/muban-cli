"""
Template tag management commands for Muban CLI.

Commands:
- tags get: List tags for a template
- tags set: Replace all tags on a template
- tags add: Upsert tags on a template
- tags delete: Remove all tags from a template
"""

import sys
from typing import List, Optional, Tuple

import click

from ..api import MubanAPIClient
from ..exceptions import (
    MubanError,
    TemplateNotFoundError,
    PermissionDeniedError,
    ValidationError,
)
from ..utils import (
    OutputFormat,
    print_csv,
    print_error,
    print_json,
    print_success,
    print_table,
    setup_logging,
    confirm_action,
)
from . import common_options, pass_context, require_config, MubanContext


def _parse_tag_args(tag_args: Tuple[str, ...]) -> List[dict]:
    """Parse key=value tag arguments into API format.

    Args:
        tag_args: Tuple of 'key=value' strings.

    Returns:
        List of {'key': ..., 'value': ...} dicts.

    Raises:
        click.BadParameter on invalid format.
    """
    tags = []
    for arg in tag_args:
        if "=" not in arg:
            raise click.BadParameter(
                f"Invalid tag format: '{arg}'. Expected key=value."
            )
        key, _, value = arg.partition("=")
        key = key.strip()
        value = value.strip()
        if not key:
            raise click.BadParameter(f"Tag key cannot be empty in '{arg}'.")
        if not value:
            raise click.BadParameter(f"Tag value cannot be empty in '{arg}'.")
        tags.append({"key": key, "value": value})
    return tags


def _format_tags(tags: list, fmt: OutputFormat) -> None:
    """Display tags in the requested format."""
    if fmt == OutputFormat.JSON:
        print_json(tags)
        return

    if not tags:
        click.echo("No tags.")
        return

    headers = ["Key", "Value"]
    rows = [[t.get("key", ""), t.get("value", "")] for t in tags]

    if fmt == OutputFormat.CSV:
        print_csv(headers, rows)
    else:
        print_table(headers, rows)


def register_tags_commands(cli: click.Group) -> None:
    """Register tag management commands with the CLI."""

    @cli.group("tags")
    def tags():
        """Template tag management commands."""
        pass

    @tags.command("get")
    @common_options
    @click.argument("template_id")
    @pass_context
    @require_config
    def tags_get(
        ctx: MubanContext,
        verbose: bool,
        quiet: bool,
        output_format: str,
        truncate_length: int,
        template_id: str,
    ):
        """
        List tags for a template.

        \b
        Examples:
          muban tags get abc123-uuid
          muban tags get abc123-uuid --format json
        """
        setup_logging(verbose, quiet)
        fmt = OutputFormat(output_format)

        try:
            with MubanAPIClient(ctx.config_manager.get()) as client:
                result = client.get_template_tags(template_id)
                tags_data = result.get("data", [])
                _format_tags(tags_data, fmt)

        except TemplateNotFoundError:
            print_error(f"Template not found: {template_id}")
            sys.exit(1)
        except MubanError as e:
            print_error(str(e))
            sys.exit(1)

    @tags.command("set")
    @common_options
    @click.argument("template_id")
    @click.argument("tags_args", nargs=-1, required=True, metavar="KEY=VALUE...")
    @pass_context
    @require_config
    def tags_set(
        ctx: MubanContext,
        verbose: bool,
        quiet: bool,
        output_format: str,
        truncate_length: int,
        template_id: str,
        tags_args: Tuple[str, ...],
    ):
        """
        Replace all tags on a template.

        Sends the complete desired tag set — existing tags not in the
        list are removed. Requires manager role.

        \b
        Examples:
          muban tags set abc123 phase=prod department=finance
          muban tags set abc123 env=staging
        """
        setup_logging(verbose, quiet)
        fmt = OutputFormat(output_format)

        try:
            tag_list = _parse_tag_args(tags_args)
        except click.BadParameter as e:
            print_error(str(e))
            sys.exit(1)

        try:
            with MubanAPIClient(ctx.config_manager.get()) as client:
                result = client.replace_template_tags(template_id, tag_list)
                tags_data = result.get("data", [])

                if not quiet:
                    print_success(f"Tags replaced ({len(tags_data)} tags set).")
                _format_tags(tags_data, fmt)

        except TemplateNotFoundError:
            print_error(f"Template not found: {template_id}")
            sys.exit(1)
        except PermissionDeniedError:
            print_error("Permission denied. Manager role required.")
            sys.exit(1)
        except ValidationError as e:
            print_error(f"Validation error: {e}")
            sys.exit(1)
        except MubanError as e:
            print_error(str(e))
            sys.exit(1)

    @tags.command("add")
    @common_options
    @click.argument("template_id")
    @click.argument("tags_args", nargs=-1, required=True, metavar="KEY=VALUE...")
    @pass_context
    @require_config
    def tags_add(
        ctx: MubanContext,
        verbose: bool,
        quiet: bool,
        output_format: str,
        truncate_length: int,
        template_id: str,
        tags_args: Tuple[str, ...],
    ):
        """
        Add or update tags on a template.

        For each tag: if a tag with the same key exists, its value is
        updated; otherwise a new tag is created. Existing tags with other
        keys are not affected. Requires manager role.

        \b
        Examples:
          muban tags add abc123 phase=prod
          muban tags add abc123 department=finance region=eu
        """
        setup_logging(verbose, quiet)
        fmt = OutputFormat(output_format)

        try:
            tag_list = _parse_tag_args(tags_args)
        except click.BadParameter as e:
            print_error(str(e))
            sys.exit(1)

        try:
            with MubanAPIClient(ctx.config_manager.get()) as client:
                result = client.add_template_tags(template_id, tag_list)
                tags_data = result.get("data", [])

                if not quiet:
                    print_success(f"Tags updated ({len(tags_data)} total).")
                _format_tags(tags_data, fmt)

        except TemplateNotFoundError:
            print_error(f"Template not found: {template_id}")
            sys.exit(1)
        except PermissionDeniedError:
            print_error("Permission denied. Manager role required.")
            sys.exit(1)
        except ValidationError as e:
            print_error(f"Validation error: {e}")
            sys.exit(1)
        except MubanError as e:
            print_error(str(e))
            sys.exit(1)

    @tags.command("delete")
    @common_options
    @click.argument("template_id")
    @click.option("--yes", "-y", is_flag=True, help="Skip confirmation prompt")
    @pass_context
    @require_config
    def tags_delete(
        ctx: MubanContext,
        verbose: bool,
        quiet: bool,
        output_format: str,
        truncate_length: int,
        template_id: str,
        yes: bool,
    ):
        """
        Remove all tags from a template.

        Requires manager role.

        \b
        Examples:
          muban tags delete abc123
          muban tags delete abc123 --yes
        """
        setup_logging(verbose, quiet)

        if not yes:
            if not confirm_action(f"Remove all tags from template {template_id}?"):
                click.echo("Cancelled.")
                return

        try:
            with MubanAPIClient(ctx.config_manager.get()) as client:
                client.delete_template_tags(template_id)
                if not quiet:
                    print_success("All tags removed.")

        except TemplateNotFoundError:
            print_error(f"Template not found: {template_id}")
            sys.exit(1)
        except PermissionDeniedError:
            print_error("Permission denied. Manager role required.")
            sys.exit(1)
        except MubanError as e:
            print_error(str(e))
            sys.exit(1)
