"""
Tests for configuration management.
"""

import json
import tempfile
from pathlib import Path

import pytest

from muban_cli.config import (
    ConfigManager,
    MubanConfig,
    DEFAULT_SERVER_URL,
    ENV_TOKEN,
    ENV_SERVER_URL,
)


class TestMubanConfig:
    """Tests for MubanConfig dataclass."""
    
    def test_default_values(self):
        """Test default configuration values."""
        config = MubanConfig()
        
        assert config.server_url == DEFAULT_SERVER_URL
        assert config.token == ""
        assert config.timeout == 30
        assert config.verify_ssl is True
        assert config.verbose is False
    
    def test_custom_values(self):
        """Test configuration with custom values."""
        config = MubanConfig(
            server_url="https://custom.server.com",
            token="test-token",
            timeout=60,
            verify_ssl=False
        )
        
        assert config.server_url == "https://custom.server.com"
        assert config.token == "test-token"
        assert config.timeout == 60
        assert config.verify_ssl is False
    
    def test_is_configured(self):
        """Test is_configured method (requires server URL only)."""
        # Not configured (no server URL)
        config = MubanConfig(server_url="")
        assert config.is_configured() is False
        
        # Configured (has server URL, no token is OK)
        config = MubanConfig(server_url="https://api.muban.me")
        assert config.is_configured() is True
    
    def test_is_authenticated(self):
        """Test is_authenticated method."""
        # Not authenticated (no token)
        config = MubanConfig()
        assert config.is_authenticated() is False
        
        # Authenticated
        config = MubanConfig(token="test-token")
        assert config.is_authenticated() is True
    
    def test_to_dict(self):
        """Test configuration serialization."""
        config = MubanConfig(token="test-token", timeout=45)
        data = config.to_dict()
        
        assert data["token"] == "test-token"
        assert data["timeout"] == 45
        assert "server_url" in data
    
    def test_from_dict(self):
        """Test configuration deserialization."""
        data = {
            "token": "from-dict-token",
            "server_url": "https://test.com",
            "timeout": 120,
            "unknown_field": "ignored"  # Should be ignored
        }
        
        config = MubanConfig.from_dict(data)
        
        assert config.token == "from-dict-token"
        assert config.server_url == "https://test.com"
        assert config.timeout == 120


class TestConfigManager:
    """Tests for ConfigManager."""
    
    @pytest.fixture
    def temp_config_dir(self):
        """Create temporary config directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)
    
    def test_save_and_load(self, temp_config_dir):
        """Test saving and loading configuration."""
        manager = ConfigManager(temp_config_dir)
        
        config = MubanConfig(
            token="saved-token",
            server_url="https://saved.server.com",
            timeout=90
        )
        
        manager.save(config)
        loaded = manager.load()
        
        assert loaded.token == "saved-token"
        assert loaded.server_url == "https://saved.server.com"
        assert loaded.timeout == 90
    
    def test_credentials_stored_separately(self, temp_config_dir):
        """Test that credentials are stored in separate file."""
        manager = ConfigManager(temp_config_dir)
        
        config = MubanConfig(token="secret-token")
        manager.save(config)
        
        # Check that credentials file exists
        credentials_file = temp_config_dir / "credentials.json"
        assert credentials_file.exists()
        
        # Check credentials content
        with open(credentials_file) as f:
            creds = json.load(f)
        assert creds["token"] == "secret-token"
        
        # Check that main config doesn't contain token
        config_file = temp_config_dir / "config.json"
        with open(config_file) as f:
            main_config = json.load(f)
        assert "token" not in main_config
    
    def test_update(self, temp_config_dir):
        """Test updating specific configuration values."""
        manager = ConfigManager(temp_config_dir)
        
        # Initial save
        config = MubanConfig(token="initial", timeout=30)
        manager.save(config)
        
        # Update
        updated = manager.update(timeout=60, verify_ssl=False)
        
        assert updated.token == "initial"  # Preserved
        assert updated.timeout == 60  # Updated
        assert updated.verify_ssl is False  # Updated
    
    def test_clear(self, temp_config_dir):
        """Test clearing configuration."""
        manager = ConfigManager(temp_config_dir)
        
        config = MubanConfig(token="to-be-cleared")
        manager.save(config)
        
        manager.clear()
        
        assert not (temp_config_dir / "config.json").exists()
        assert not (temp_config_dir / "credentials.json").exists()
    
    def test_env_variables_override(self, temp_config_dir, monkeypatch):
        """Test that environment variables override file config."""
        manager = ConfigManager(temp_config_dir)
        
        # Save file config
        config = MubanConfig(
            token="file-token",
            server_url="https://file.server.com"
        )
        manager.save(config)
        
        # Set environment variables
        monkeypatch.setenv(ENV_TOKEN, "env-token")
        monkeypatch.setenv(ENV_SERVER_URL, "https://env.server.com")
        
        # Load should use env vars
        loaded = manager.load()
        
        assert loaded.token == "env-token"
        assert loaded.server_url == "https://env.server.com"
