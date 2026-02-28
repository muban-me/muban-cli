"""
Tests for utility functions.
"""

from datetime import datetime

import click
import pytest

from muban_cli.utils import (
    format_datetime,
    format_file_size,
    truncate_string,
    parse_parameters,
    load_json_file,
    is_uuid,
    print_csv,
)


class TestFormatDatetime:
    """Tests for format_datetime function."""
    
    def test_format_none(self):
        """Test formatting None."""
        assert format_datetime(None) == "-"
    
    def test_format_string(self):
        """Test formatting ISO string."""
        result = format_datetime("2025-01-08T10:30:00Z")
        assert "2025" in result
        assert "01" in result
        assert "08" in result
    
    def test_format_datetime_object(self):
        """Test formatting datetime object."""
        dt = datetime(2025, 1, 8, 10, 30, 0)
        result = format_datetime(dt)
        assert "2025-01-08" in result
        assert "10:30:00" in result


class TestFormatFileSize:
    """Tests for format_file_size function."""
    
    def test_format_none(self):
        """Test formatting None."""
        assert format_file_size(None) == "-"
    
    def test_format_bytes(self):
        """Test formatting bytes."""
        assert "B" in format_file_size(500)
    
    def test_format_kilobytes(self):
        """Test formatting kilobytes."""
        result = format_file_size(2048)
        assert "KB" in result
    
    def test_format_megabytes(self):
        """Test formatting megabytes."""
        result = format_file_size(5 * 1024 * 1024)
        assert "MB" in result


class TestTruncateString:
    """Tests for truncate_string function."""
    
    def test_no_truncation_needed(self):
        """Test string shorter than max length."""
        result = truncate_string("Hello", 10)
        assert result == "Hello"
    
    def test_truncation(self):
        """Test string truncation."""
        result = truncate_string("Hello World!", 8)
        assert len(result) == 8
        assert result.endswith("...")


class TestParseParameters:
    """Tests for parse_parameters function."""
    
    def test_simple_parameter(self):
        """Test parsing simple parameter."""
        result = parse_parameters(["name=value"])
        assert len(result) == 1
        assert result[0]["name"] == "name"
        assert result[0]["value"] == "value"
    
    def test_numeric_value(self):
        """Test parsing numeric value."""
        result = parse_parameters(["count=42"])
        assert result[0]["value"] == 42
    
    def test_json_value(self):
        """Test parsing JSON value."""
        result = parse_parameters(['items=["a", "b"]'])
        assert result[0]["value"] == ["a", "b"]
    
    def test_invalid_format(self):
        """Test invalid parameter format."""
        with pytest.raises(ValueError):
            parse_parameters(["invalid"])


class TestLoadJsonFile:
    """Tests for load_json_file function."""
    
    def test_load_valid_json(self, tmp_path):
        """Test loading valid JSON file."""
        json_file = tmp_path / "test.json"
        json_file.write_text('{"key": "value"}')
        
        result = load_json_file(json_file)
        
        assert result["key"] == "value"
    
    def test_load_invalid_json(self, tmp_path):
        """Test loading invalid JSON file."""
        json_file = tmp_path / "invalid.json"
        json_file.write_text("not valid json")
        
        with pytest.raises(ValueError) as exc_info:
            load_json_file(json_file)
        
        assert "Invalid JSON" in str(exc_info.value)
    
    def test_load_nonexistent_file(self, tmp_path):
        """Test loading nonexistent file."""
        with pytest.raises(ValueError) as exc_info:
            load_json_file(tmp_path / "nonexistent.json")
        
        assert "Cannot read file" in str(exc_info.value)


class TestIsUuid:
    """Tests for is_uuid function."""
    
    def test_valid_uuid(self):
        """Test valid UUID."""
        assert is_uuid("550e8400-e29b-41d4-a716-446655440000") is True
    
    def test_invalid_uuid(self):
        """Test invalid UUID."""
        assert is_uuid("not-a-uuid") is False
        assert is_uuid("12345") is False
        assert is_uuid("") is False
    
    def test_uuid_case_insensitive(self):
        """Test UUID case insensitivity."""
        assert is_uuid("550E8400-E29B-41D4-A716-446655440000") is True


class TestPrintCsv:
    """Tests for print_csv function."""
    
    def test_basic_csv_output(self, capsys):
        """Test basic CSV output."""
        headers = ["Name", "Value"]
        rows = [["foo", "bar"], ["baz", "qux"]]
        print_csv(headers, rows)
        captured = capsys.readouterr()
        assert "Name,Value" in captured.out
        assert "foo,bar" in captured.out
        assert "baz,qux" in captured.out
    
    def test_csv_with_special_characters(self, capsys):
        """Test CSV output with commas and quotes."""
        headers = ["Name", "Description"]
        rows = [["test", "has, comma"], ["other", 'has "quotes"']]
        print_csv(headers, rows)
        captured = capsys.readouterr()
        # CSV should properly quote fields with special characters
        assert "Name,Description" in captured.out
        assert '"has, comma"' in captured.out
    
    def test_csv_strips_ansi_codes(self, capsys):
        """Test CSV output strips ANSI color codes."""
        headers = ["Status"]
        colored_text = click.style("Active", fg="green")
        rows = [[colored_text]]
        print_csv(headers, rows)
        captured = capsys.readouterr()
        # Should contain "Active" without ANSI codes
        assert "Active" in captured.out
        assert "\x1b[" not in captured.out  # No ANSI escape codes
    
    def test_empty_rows(self, capsys):
        """Test CSV output with no rows."""
        headers = ["Col1", "Col2"]
        rows = []
        print_csv(headers, rows)
        captured = capsys.readouterr()
        assert "Col1,Col2" in captured.out


class TestPrintFunctions:
    """Tests for print_* utility functions."""
    
    def test_print_success(self, capsys):
        """Test print_success output."""
        from muban_cli.utils import print_success
        print_success("Operation completed")
        captured = capsys.readouterr()
        assert "Operation completed" in captured.out
    
    def test_print_error_simple(self, capsys):
        """Test print_error without details."""
        from muban_cli.utils import print_error
        print_error("Something went wrong")
        captured = capsys.readouterr()
        assert "Something went wrong" in captured.err
    
    def test_print_error_with_details(self, capsys):
        """Test print_error with details."""
        from muban_cli.utils import print_error
        print_error("Error occurred", details="Additional info here")
        captured = capsys.readouterr()
        assert "Error occurred" in captured.err
        assert "Additional info here" in captured.err
    
    def test_print_warning(self, capsys):
        """Test print_warning output."""
        from muban_cli.utils import print_warning
        print_warning("Watch out!")
        captured = capsys.readouterr()
        assert "Watch out!" in captured.out
    
    def test_print_info(self, capsys):
        """Test print_info output."""
        from muban_cli.utils import print_info
        print_info("Just so you know")
        captured = capsys.readouterr()
        assert "Just so you know" in captured.out


class TestPrintTable:
    """Tests for print_table function."""
    
    def test_print_basic_table(self, capsys):
        """Test basic table output."""
        from muban_cli.utils import print_table
        headers = ["Name", "Age"]
        rows = [["Alice", "30"], ["Bob", "25"]]
        print_table(headers, rows)
        captured = capsys.readouterr()
        assert "Name" in captured.out
        assert "Age" in captured.out
        assert "Alice" in captured.out
        assert "Bob" in captured.out
    
    def test_print_empty_table(self, capsys):
        """Test table with no rows."""
        from muban_cli.utils import print_table
        headers = ["X", "Y"]
        rows = []
        print_table(headers, rows)
        captured = capsys.readouterr()
        # Should at least print headers
        assert "X" in captured.out
        assert "Y" in captured.out


class TestPrintJson:
    """Tests for print_json function."""
    
    def test_print_dict(self, capsys):
        """Test printing dictionary as JSON."""
        from muban_cli.utils import print_json
        data = {"name": "Test", "count": 42}
        print_json(data)
        captured = capsys.readouterr()
        assert '"name"' in captured.out
        assert '"Test"' in captured.out
        assert "42" in captured.out
    
    def test_print_list(self, capsys):
        """Test printing list as JSON."""
        from muban_cli.utils import print_json
        data = [1, 2, 3]
        print_json(data)
        captured = capsys.readouterr()
        assert "1" in captured.out
        assert "2" in captured.out
        assert "3" in captured.out
    
    def test_print_with_custom_indent(self, capsys):
        """Test printing JSON with custom indentation."""
        from muban_cli.utils import print_json
        data = {"key": "value"}
        print_json(data, indent=4)
        captured = capsys.readouterr()
        # 4-space indent
        assert '    "key"' in captured.out


class TestParseTypedValue:
    """Tests for parse_typed_value function."""
    
    def test_parse_quoted_string_double(self):
        """Test parsing double-quoted string."""
        from muban_cli.utils import parse_typed_value
        assert parse_typed_value('"Hello World"') == "Hello World"
        assert parse_typed_value('"123"') == "123"
        assert parse_typed_value('""') == ""
    
    def test_parse_quoted_string_single(self):
        """Test parsing single-quoted string."""
        from muban_cli.utils import parse_typed_value
        assert parse_typed_value("'Hello'") == "Hello"
        assert parse_typed_value("'123'") == "123"
    
    def test_parse_integer(self):
        """Test parsing integers."""
        from muban_cli.utils import parse_typed_value
        assert parse_typed_value("123") == 123
        assert parse_typed_value("-456") == -456
        assert parse_typed_value("0") == 0
    
    def test_parse_float(self):
        """Test parsing floats."""
        from muban_cli.utils import parse_typed_value
        assert parse_typed_value("12.5") == 12.5
        assert parse_typed_value("-3.14") == -3.14
        assert parse_typed_value("0.5") == 0.5
    
    def test_parse_boolean(self):
        """Test parsing booleans."""
        from muban_cli.utils import parse_typed_value
        assert parse_typed_value("true") is True
        assert parse_typed_value("false") is False
        assert parse_typed_value("TRUE") is True
        assert parse_typed_value("False") is False
    
    def test_parse_null(self):
        """Test parsing null."""
        from muban_cli.utils import parse_typed_value
        assert parse_typed_value("null") is None
        assert parse_typed_value("NULL") is None
    
    def test_parse_unquoted_string(self):
        """Test parsing unquoted text as string."""
        from muban_cli.utils import parse_typed_value
        assert parse_typed_value("Hello World") == "Hello World"
        assert parse_typed_value("abc") == "abc"
    
    def test_parse_empty(self):
        """Test parsing empty string."""
        from muban_cli.utils import parse_typed_value
        assert parse_typed_value("") == ""
        assert parse_typed_value("   ") == ""
    
    def test_parse_with_whitespace(self):
        """Test parsing with surrounding whitespace."""
        from muban_cli.utils import parse_typed_value
        assert parse_typed_value("  123  ") == 123
        assert parse_typed_value('  "test"  ') == "test"


class TestFormatTypedValue:
    """Tests for format_typed_value function."""
    
    def test_format_string(self):
        """Test formatting string values."""
        from muban_cli.utils import format_typed_value
        assert format_typed_value("Hello") == '"Hello"'
        assert format_typed_value("123") == '"123"'
        assert format_typed_value("") == '""'
    
    def test_format_integer(self):
        """Test formatting integer values."""
        from muban_cli.utils import format_typed_value
        assert format_typed_value(123) == "123"
        assert format_typed_value(-456) == "-456"
        assert format_typed_value(0) == "0"
    
    def test_format_float(self):
        """Test formatting float values."""
        from muban_cli.utils import format_typed_value
        assert format_typed_value(12.5) == "12.5"
        assert format_typed_value(-3.14) == "-3.14"
    
    def test_format_boolean(self):
        """Test formatting boolean values."""
        from muban_cli.utils import format_typed_value
        assert format_typed_value(True) == "true"
        assert format_typed_value(False) == "false"
    
    def test_format_null(self):
        """Test formatting None as null."""
        from muban_cli.utils import format_typed_value
        assert format_typed_value(None) == "null"
    
    def test_roundtrip(self):
        """Test parse/format roundtrip preserves values."""
        from muban_cli.utils import parse_typed_value, format_typed_value
        test_cases = ['"Hello"', "123", "12.5", "true", "false", "null"]
        for original in test_cases:
            parsed = parse_typed_value(original)
            formatted = format_typed_value(parsed)
            reparsed = parse_typed_value(formatted)
            assert parsed == reparsed, f"Roundtrip failed for {original}"