"""
Tests for Muban CLI exceptions module.
"""

import pytest

from muban_cli.exceptions import (
    MubanError,
    ConfigurationError,
    AuthenticationError,
    APIError,
    ValidationError,
    TemplateNotFoundError,
    PermissionDeniedError,
)


class TestMubanError:
    """Test base MubanError exception."""
    
    def test_basic_error(self):
        """Test basic error creation."""
        error = MubanError("Something went wrong")
        assert str(error) == "Something went wrong"
        assert error.message == "Something went wrong"
        assert error.details is None
    
    def test_error_with_details(self):
        """Test error with details."""
        error = MubanError("Error occurred", details="Additional info here")
        assert error.message == "Error occurred"
        assert error.details == "Additional info here"
    
    def test_inheritance(self):
        """Test that MubanError is an Exception."""
        error = MubanError("test")
        assert isinstance(error, Exception)


class TestConfigurationError:
    """Test ConfigurationError exception."""
    
    def test_basic_config_error(self):
        """Test configuration error."""
        error = ConfigurationError("Missing configuration")
        assert isinstance(error, MubanError)
        assert error.message == "Missing configuration"
    
    def test_config_error_with_details(self):
        """Test config error with details."""
        error = ConfigurationError("Invalid config", details="server_url is required")
        assert error.details == "server_url is required"


class TestAuthenticationError:
    """Test AuthenticationError exception."""
    
    def test_auth_error(self):
        """Test authentication error."""
        error = AuthenticationError("Invalid credentials")
        assert isinstance(error, MubanError)
        assert error.message == "Invalid credentials"


class TestAPIError:
    """Test APIError exception."""
    
    def test_basic_api_error(self):
        """Test basic API error."""
        error = APIError("Request failed")
        assert isinstance(error, MubanError)
        assert error.status_code is None
        assert error.response_data == {}
    
    def test_api_error_with_status(self):
        """Test API error with status code."""
        error = APIError("Not found", status_code=404)
        assert error.status_code == 404
    
    def test_api_error_with_response_data(self):
        """Test API error with response data."""
        response = {"error": "Not found", "code": "TEMPLATE_NOT_FOUND"}
        error = APIError("Not found", status_code=404, response_data=response)
        assert error.response_data == response
        assert error.response_data["code"] == "TEMPLATE_NOT_FOUND"


class TestValidationError:
    """Test ValidationError exception."""
    
    def test_validation_error(self):
        """Test validation error."""
        error = ValidationError("Invalid input")
        assert isinstance(error, MubanError)
        assert error.message == "Invalid input"


class TestTemplateNotFoundError:
    """Test TemplateNotFoundError exception."""
    
    def test_template_not_found(self):
        """Test template not found error."""
        error = TemplateNotFoundError("Template does not exist", status_code=404)
        assert isinstance(error, APIError)
        assert error.status_code == 404


class TestPermissionDeniedError:
    """Test PermissionDeniedError exception."""
    
    def test_permission_denied(self):
        """Test permission denied error."""
        error = PermissionDeniedError("Admin access required", status_code=403)
        assert isinstance(error, APIError)
        assert error.status_code == 403


class TestExceptionHierarchy:
    """Test exception hierarchy and catching."""
    
    def test_catch_all_muban_errors(self):
        """Test catching all Muban errors with base class."""
        errors = [
            MubanError("base"),
            ConfigurationError("config"),
            AuthenticationError("auth"),
            APIError("api"),
            ValidationError("validation"),
            TemplateNotFoundError("template"),
            PermissionDeniedError("permission"),
        ]
        
        for error in errors:
            try:
                raise error
            except MubanError as e:
                assert e is error  # Should catch all
    
    def test_catch_api_errors(self):
        """Test catching API errors."""
        api_errors = [
            APIError("api"),
            TemplateNotFoundError("template"),
            PermissionDeniedError("permission"),
        ]
        
        for error in api_errors:
            try:
                raise error
            except APIError as e:
                assert e is error
