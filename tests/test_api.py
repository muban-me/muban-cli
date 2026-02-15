"""
Tests for API client.
"""

from pathlib import Path

import pytest
import responses

from muban_cli.api import MubanAPIClient
from muban_cli.config import MubanConfig
from muban_cli.exceptions import (
    APIError,
    AuthenticationError,
    PermissionDeniedError,
    TemplateNotFoundError,
    ValidationError,
)


@pytest.fixture
def config():
    """Create test configuration."""
    return MubanConfig(
        token="test-jwt-token",
        server_url="https://test.muban.me",
        timeout=30,
        verify_ssl=True
    )


@pytest.fixture
def client(config):
    """Create API client with test configuration."""
    return MubanAPIClient(config)


class TestMubanAPIClient:
    """Tests for MubanAPIClient."""
    
    def test_init(self, client, config):
        """Test client initialization."""
        assert client.config == config
        assert client.base_url == "https://test.muban.me/api/v1/"
    
    def test_headers(self, client):
        """Test request headers."""
        headers = client._get_headers()
        assert headers["Authorization"] == "Bearer test-jwt-token"
    
    @responses.activate
    def test_list_templates(self, client):
        """Test listing templates."""
        mock_response = {
            "data": {
                "items": [
                    {"id": "1", "name": "Template 1"},
                    {"id": "2", "name": "Template 2"}
                ],
                "totalItems": 2,
                "totalPages": 1
            }
        }
        
        responses.add(
            responses.GET,
            "https://test.muban.me/api/v1/templates",
            json=mock_response,
            status=200
        )
        
        result = client.list_templates()
        
        assert result["data"]["totalItems"] == 2
        assert len(result["data"]["items"]) == 2
    
    @responses.activate
    def test_get_template(self, client):
        """Test getting template details."""
        template_id = "test-uuid-123"
        mock_response = {
            "data": {
                "id": template_id,
                "name": "Test Template",
                "author": "Test Author"
            }
        }
        
        responses.add(
            responses.GET,
            f"https://test.muban.me/api/v1/templates/{template_id}",
            json=mock_response,
            status=200
        )
        
        result = client.get_template(template_id)
        
        assert result["data"]["id"] == template_id
        assert result["data"]["name"] == "Test Template"
    
    @responses.activate
    def test_template_not_found(self, client):
        """Test handling of 404 response."""
        responses.add(
            responses.GET,
            "https://test.muban.me/api/v1/templates/nonexistent",
            json={"errors": [{"message": "Not found"}]},
            status=404
        )
        
        with pytest.raises(TemplateNotFoundError):
            client.get_template("nonexistent")
    
    @responses.activate
    def test_authentication_error(self, client):
        """Test handling of 401 response."""
        responses.add(
            responses.GET,
            "https://test.muban.me/api/v1/templates",
            json={"errors": [{"message": "Unauthorized"}]},
            status=401
        )
        
        with pytest.raises(AuthenticationError):
            client.list_templates()
    
    @responses.activate
    def test_permission_denied(self, client):
        """Test handling of 403 response."""
        responses.add(
            responses.DELETE,
            "https://test.muban.me/api/v1/templates/test-id",
            json={"errors": [{"message": "Forbidden"}]},
            status=403
        )
        
        with pytest.raises(PermissionDeniedError):
            client.delete_template("test-id")
    
    @responses.activate
    def test_validation_error(self, client):
        """Test handling of 400 response."""
        responses.add(
            responses.POST,
            "https://test.muban.me/api/v1/templates/test-id/generate/pdf",
            json={"errors": [{"message": "Invalid parameters"}]},
            status=400
        )
        
        with pytest.raises(ValidationError):
            client.generate_document(
                template_id="test-id",
                output_format="pdf",
                parameters=[],
                output_path=Path("test.pdf")
            )
    
    @responses.activate
    def test_delete_template(self, client):
        """Test deleting a template."""
        template_id = "delete-me"
        
        responses.add(
            responses.DELETE,
            f"https://test.muban.me/api/v1/templates/{template_id}",
            status=204
        )
        
        result = client.delete_template(template_id)
        assert result["success"] is True
    
    @responses.activate
    def test_get_fonts(self, client):
        """Test getting available fonts."""
        mock_response = {
            "data": [
                {"name": "DejaVu Sans", "faces": ["normal", "bold"]},
                {"name": "Arial", "faces": ["normal"]}
            ]
        }
        
        responses.add(
            responses.GET,
            "https://test.muban.me/api/v1/templates/fonts",
            json=mock_response,
            status=200
        )
        
        result = client.get_fonts()
        
        assert len(result["data"]) == 2
        assert result["data"][0]["name"] == "DejaVu Sans"
    
    @responses.activate
    def test_audit_health(self, client):
        """Test audit health check."""
        responses.add(
            responses.GET,
            "https://test.muban.me/api/v1/audit/health",
            json={"data": "OK"},
            status=200
        )
        
        result = client.get_audit_health()
        assert result["data"] == "OK"
    
    def test_context_manager(self, config):
        """Test client as context manager."""
        with MubanAPIClient(config) as client:
            assert client._session is None  # Not created yet
        # Session should be closed after context exit


class TestAPIErrorHandling:
    """Tests for API error handling."""
    
    @responses.activate
    def test_extract_error_message_from_errors(self, client):
        """Test error message extraction from errors array."""
        responses.add(
            responses.GET,
            "https://test.muban.me/api/v1/templates",
            json={"errors": [{"message": "Specific error message"}]},
            status=400
        )
        
        with pytest.raises(ValidationError) as exc_info:
            client.list_templates()
        
        assert "Specific error message" in str(exc_info.value)
    
    @responses.activate
    def test_extract_error_message_from_message(self, client):
        """Test error message extraction from message field."""
        responses.add(
            responses.GET,
            "https://test.muban.me/api/v1/templates",
            json={"message": "Direct error message"},
            status=400
        )
        
        with pytest.raises(ValidationError) as exc_info:
            client.list_templates()
        
        assert "Direct error message" in str(exc_info.value)


class TestUploadTemplate:
    """Tests for uploading templates."""
    
    @responses.activate
    def test_upload_template_success(self, client, tmp_path):
        """Test uploading a template successfully."""
        # Create a test ZIP file
        zip_file = tmp_path / "test-template.zip"
        zip_file.write_bytes(b"PK\x03\x04fake zip content")
        
        mock_response = {
            "data": {
                "id": "uploaded-template-123",
                "name": "Test Template",
                "author": "Test Author",
                "fileSize": 100
            }
        }
        
        responses.add(
            responses.POST,
            "https://test.muban.me/api/v1/templates/upload",
            json=mock_response,
            status=200
        )
        
        result = client.upload_template(
            file_path=zip_file,
            name="Test Template",
            author="Test Author"
        )
        
        assert result["data"]["id"] == "uploaded-template-123"
        assert result["data"]["name"] == "Test Template"
    
    @responses.activate
    def test_upload_template_with_metadata(self, client, tmp_path):
        """Test uploading a template with metadata."""
        zip_file = tmp_path / "test-template.zip"
        zip_file.write_bytes(b"PK\x03\x04fake zip content")
        
        mock_response = {
            "data": {
                "id": "uploaded-template-456",
                "name": "Template With Metadata",
                "author": "Author",
                "metadata": '{"key": "value"}'
            }
        }
        
        responses.add(
            responses.POST,
            "https://test.muban.me/api/v1/templates/upload",
            json=mock_response,
            status=200
        )
        
        result = client.upload_template(
            file_path=zip_file,
            name="Template With Metadata",
            author="Author",
            metadata='{"key": "value"}'
        )
        
        assert result["data"]["id"] == "uploaded-template-456"
    
    def test_upload_nonexistent_file(self, client, tmp_path):
        """Test uploading a nonexistent file raises ValidationError."""
        nonexistent_path = tmp_path / "nonexistent.zip"
        
        with pytest.raises(ValidationError) as exc_info:
            client.upload_template(
                file_path=nonexistent_path,
                name="Test",
                author="Author"
            )
        
        assert "not found" in str(exc_info.value).lower()
    
    def test_upload_non_zip_file(self, client, tmp_path):
        """Test uploading a non-ZIP file raises ValidationError."""
        txt_file = tmp_path / "test.txt"
        txt_file.write_text("not a zip file")
        
        with pytest.raises(ValidationError) as exc_info:
            client.upload_template(
                file_path=txt_file,
                name="Test",
                author="Author"
            )
        
        assert "zip" in str(exc_info.value).lower()


class TestDownloadTemplate:
    """Tests for downloading templates."""
    
    @responses.activate
    def test_download_template_success(self, client, tmp_path):
        """Test downloading a template successfully."""
        template_id = "download-me-123"
        output_path = tmp_path / "downloaded.zip"
        
        # Mock the download endpoint
        responses.add(
            responses.GET,
            f"https://test.muban.me/api/v1/templates/{template_id}/download",
            body=b"PK\x03\x04fake zip content",
            status=200,
            content_type="application/zip"
        )
        
        result_path = client.download_template(
            template_id=template_id,
            output_path=output_path
        )
        
        assert result_path == output_path
        assert output_path.exists()
        assert output_path.read_bytes() == b"PK\x03\x04fake zip content"
    
    @responses.activate
    def test_download_template_default_path(self, client, tmp_path, monkeypatch):
        """Test downloading a template with default output path."""
        template_id = "download-default-456"
        
        # Change to temp directory so default file is created there
        monkeypatch.chdir(tmp_path)
        
        responses.add(
            responses.GET,
            f"https://test.muban.me/api/v1/templates/{template_id}/download",
            body=b"PK\x03\x04fake zip content",
            status=200,
            content_type="application/zip"
        )
        
        result_path = client.download_template(template_id=template_id)
        
        assert result_path.name == f"{template_id}.zip"
        assert result_path.exists()
    
    @responses.activate
    def test_download_nonexistent_template(self, client, tmp_path):
        """Test downloading a nonexistent template raises error."""
        template_id = "nonexistent-id"
        output_path = tmp_path / "output.zip"
        
        responses.add(
            responses.GET,
            f"https://test.muban.me/api/v1/templates/{template_id}/download",
            json={"errors": [{"message": "Template not found"}]},
            status=404
        )
        
        with pytest.raises(TemplateNotFoundError):
            client.download_template(
                template_id=template_id,
                output_path=output_path
            )
