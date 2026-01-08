"""
Shared test fixtures and configuration for Muban CLI tests.
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from muban_cli.config import MubanConfig, ConfigManager


# ============================================================================
# CLI Runner Fixtures
# ============================================================================

@pytest.fixture
def runner():
    """Create CLI test runner."""
    return CliRunner()


@pytest.fixture
def isolated_runner():
    """Create CLI test runner with isolated filesystem."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        yield runner


# ============================================================================
# Configuration Fixtures
# ============================================================================

@pytest.fixture
def temp_config_dir(tmp_path):
    """Create temporary configuration directory."""
    config_dir = tmp_path / ".muban"
    config_dir.mkdir()
    return config_dir


@pytest.fixture
def test_config():
    """Create test configuration object."""
    return MubanConfig(
        token="test-jwt-token-eyJhbGciOiJIUzUxMiJ9.test",
        refresh_token="test-refresh-token",
        server_url="https://test.muban.me",
        timeout=30,
        verify_ssl=True
    )


@pytest.fixture
def unconfigured_config():
    """Create unconfigured configuration object."""
    return MubanConfig(
        token="",
        server_url="https://api.muban.me",
    )


@pytest.fixture
def config_manager(temp_config_dir, test_config):
    """Create ConfigManager with test configuration."""
    manager = ConfigManager(temp_config_dir)
    manager.save(test_config)
    return manager


# ============================================================================
# Mock Fixtures
# ============================================================================

@pytest.fixture
def mock_config_manager(test_config):
    """Mock get_config_manager to return configured state.
    
    Patches all locations where config is accessed to prevent real API calls.
    """
    with patch('muban_cli.cli.get_config_manager') as mock_cli, \
         patch('muban_cli.config.get_config_manager') as mock_config, \
         patch('muban_cli.api.get_config') as mock_api_config, \
         patch('muban_cli.api.get_config_manager') as mock_api_cm:
        
        config_manager = MagicMock(spec=ConfigManager)
        config_manager.get.return_value = test_config
        config_manager.load.return_value = test_config
        
        # Set up all mocks to return same config
        mock_cli.return_value = config_manager
        mock_config.return_value = config_manager
        mock_api_config.return_value = test_config
        mock_api_cm.return_value = config_manager
        
        yield config_manager


@pytest.fixture
def mock_unconfigured():
    """Mock get_config_manager to return unconfigured state."""
    with patch('muban_cli.cli.get_config_manager') as mock_cli, \
         patch('muban_cli.config.get_config_manager') as mock_config, \
         patch('muban_cli.api.get_config') as mock_api_config, \
         patch('muban_cli.api.get_config_manager') as mock_api_cm:
        
        config_manager = MagicMock(spec=ConfigManager)
        config = MubanConfig(token="", server_url="")
        config_manager.get.return_value = config
        
        mock_cli.return_value = config_manager
        mock_config.return_value = config_manager
        mock_api_config.return_value = config
        mock_api_cm.return_value = config_manager
        
        yield config_manager


@pytest.fixture
def mock_api_client():
    """Create a mock API client."""
    mock_client = MagicMock()
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)
    return mock_client


# ============================================================================
# Sample Data Fixtures
# ============================================================================

@pytest.fixture
def sample_template():
    """Sample template data."""
    return {
        'id': '550e8400-e29b-41d4-a716-446655440000',
        'name': 'Test Template',
        'description': 'A test template for unit testing',
        'author': 'Test Author',
        'fileSize': 1024 * 1024,  # 1 MB
        'created': '2025-01-08T10:00:00Z',
        'updated': '2025-01-08T12:00:00Z',
        'integrityVerified': True,
    }


@pytest.fixture
def sample_templates_response(sample_template):
    """Sample list templates response."""
    return {
        'data': {
            'items': [sample_template],
            'totalItems': 1,
            'totalPages': 1,
            'currentPage': 0,
        }
    }


@pytest.fixture
def sample_user():
    """Sample user data."""
    return {
        'id': 'user-123',
        'username': 'testuser',
        'email': 'test@example.com',
        'firstName': 'Test',
        'lastName': 'User',
        'roles': ['ROLE_USER', 'ROLE_MANAGER'],
        'enabled': True,
        'createdAt': '2025-01-01T00:00:00Z',
    }


@pytest.fixture
def sample_users_response(sample_user):
    """Sample list users response."""
    return {
        'data': {
            'items': [sample_user],
            'totalItems': 1,
            'totalPages': 1,
        }
    }


@pytest.fixture
def sample_audit_log():
    """Sample audit log entry."""
    return {
        'id': 'audit-123',
        'eventType': 'LOGIN_SUCCESS',
        'severity': 'LOW',
        'userId': 'user-123',
        'username': 'testuser',
        'ipAddress': '192.168.1.1',
        'success': True,
        'timestamp': '2025-01-08T10:00:00Z',
        'details': 'User logged in successfully',
    }


@pytest.fixture
def sample_login_response():
    """Sample login response."""
    return {
        'data': {
            'accessToken': 'new-jwt-access-token',
            'refreshToken': 'new-jwt-refresh-token',
            'tokenType': 'Bearer',
            'expiresIn': 3600,
        }
    }


# ============================================================================
# File Fixtures
# ============================================================================

@pytest.fixture
def sample_zip_file(tmp_path):
    """Create a sample ZIP file for testing."""
    import zipfile
    
    zip_path = tmp_path / "test_template.zip"
    with zipfile.ZipFile(zip_path, 'w') as zf:
        zf.writestr("template.jrxml", "<jasperReport></jasperReport>")
        zf.writestr("manifest.json", '{"name": "Test", "version": "1.0"}')
    
    return zip_path


@pytest.fixture
def sample_json_file(tmp_path):
    """Create a sample JSON file for testing."""
    json_path = tmp_path / "params.json"
    json_path.write_text(json.dumps({
        "title": "Test Report",
        "year": 2025,
        "items": ["a", "b", "c"]
    }))
    return json_path


@pytest.fixture
def sample_request_body_file(tmp_path):
    """Create a sample request body JSON file."""
    json_path = tmp_path / "request.json"
    json_path.write_text(json.dumps({
        "parameters": [
            {"name": "title", "value": "Test"},
            {"name": "count", "value": 10}
        ],
        "data": {"items": []},
        "documentLocale": "en_US"
    }))
    return json_path
