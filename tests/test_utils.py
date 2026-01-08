"""
Tests for utility functions.
"""

from datetime import datetime

import pytest

from muban_cli.utils import (
    format_datetime,
    format_file_size,
    truncate_string,
    parse_parameters,
    load_json_file,
    is_uuid,
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
