"""
Configuration management for Muban CLI.

Handles API credentials, server URLs, and persistent configuration storage.
Supports both file-based configuration and environment variables.
"""

import os
import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any
from dataclasses import dataclass, field, asdict

from .exceptions import ConfigurationError

logger = logging.getLogger(__name__)

# Default configuration file locations
CONFIG_DIR_NAME = ".muban"
CONFIG_FILE_NAME = "config.json"
CREDENTIALS_FILE_NAME = "credentials.json"

# Environment variable names
ENV_TOKEN = "MUBAN_TOKEN"
ENV_SERVER_URL = "MUBAN_SERVER_URL"
ENV_AUTH_SERVER_URL = "MUBAN_AUTH_SERVER_URL"
ENV_TIMEOUT = "MUBAN_TIMEOUT"
ENV_VERIFY_SSL = "MUBAN_VERIFY_SSL"

# Default values
DEFAULT_SERVER_URL = "https://api.muban.me"
DEFAULT_TIMEOUT = 30
DEFAULT_PAGE_SIZE = 20


@dataclass
class MubanConfig:
    """Muban CLI configuration."""
    
    server_url: str = DEFAULT_SERVER_URL
    auth_server_url: str = ""  # OAuth2/Auth server URL (if different from API server)
    token: str = ""  # JWT Bearer token
    refresh_token: str = ""  # Refresh token for obtaining new access tokens
    token_expires_at: int = 0  # Token expiration timestamp (Unix epoch)
    timeout: int = DEFAULT_TIMEOUT
    verify_ssl: bool = True
    default_output_dir: str = "."
    default_format: str = "pdf"
    verbose: bool = False
    page_size: int = DEFAULT_PAGE_SIZE
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MubanConfig":
        """Create configuration from dictionary."""
        # Filter only valid fields
        valid_fields = {
            'server_url', 'auth_server_url', 'token', 'refresh_token', 'token_expires_at',
            'timeout', 'verify_ssl', 'default_output_dir', 'default_format', 'verbose', 'page_size'
        }
        filtered_data = {k: v for k, v in data.items() if k in valid_fields}
        return cls(**filtered_data)
    
    def is_configured(self) -> bool:
        """Check if the configuration has required settings."""
        return bool(self.token and self.server_url)
    
    def is_token_expired(self) -> bool:
        """Check if the access token is expired or about to expire."""
        import time
        if not self.token_expires_at:
            return False  # No expiry info, assume valid
        # Consider expired if less than 60 seconds remaining
        return time.time() > (self.token_expires_at - 60)
    
    def has_refresh_token(self) -> bool:
        """Check if a refresh token is available."""
        return bool(self.refresh_token)
    
    def get_auth_server_url(self) -> str:
        """Get auth server URL, defaults to server_url if not set."""
        return self.auth_server_url or self.server_url


class ConfigManager:
    """Manages Muban CLI configuration."""
    
    def __init__(self, config_dir: Optional[Path] = None):
        """
        Initialize configuration manager.
        
        Args:
            config_dir: Custom configuration directory. Defaults to ~/.muban
        """
        if config_dir:
            self.config_dir = Path(config_dir)
        else:
            self.config_dir = Path.home() / CONFIG_DIR_NAME
        
        self.config_file = self.config_dir / CONFIG_FILE_NAME
        self.credentials_file = self.config_dir / CREDENTIALS_FILE_NAME
        self._config: Optional[MubanConfig] = None
    
    def _ensure_config_dir(self) -> None:
        """Ensure configuration directory exists."""
        self.config_dir.mkdir(parents=True, exist_ok=True)
    
    def _load_from_file(self) -> Dict[str, Any]:
        """Load configuration from file."""
        config_data = {}
        
        # Load main config
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config_data.update(json.load(f))
            except json.JSONDecodeError as e:
                logger.warning(f"Invalid config file: {e}")
            except OSError as e:
                logger.warning(f"Cannot read config file: {e}")
        
        # Load credentials (kept separate for security)
        if self.credentials_file.exists():
            try:
                with open(self.credentials_file, 'r', encoding='utf-8') as f:
                    creds = json.load(f)
                    if 'token' in creds:
                        config_data['token'] = creds['token']
                    if 'refresh_token' in creds:
                        config_data['refresh_token'] = creds['refresh_token']
                    if 'token_expires_at' in creds:
                        config_data['token_expires_at'] = creds['token_expires_at']
            except json.JSONDecodeError as e:
                logger.warning(f"Invalid credentials file: {e}")
            except OSError as e:
                logger.warning(f"Cannot read credentials file: {e}")
        
        return config_data
    
    def _load_from_env(self) -> Dict[str, Any]:
        """Load configuration from environment variables."""
        env_config = {}
        
        if os.getenv(ENV_TOKEN):
            env_config['token'] = os.getenv(ENV_TOKEN)
        
        if os.getenv(ENV_SERVER_URL):
            env_config['server_url'] = os.getenv(ENV_SERVER_URL)
        
        if os.getenv(ENV_AUTH_SERVER_URL):
            env_config['auth_server_url'] = os.getenv(ENV_AUTH_SERVER_URL)
        
        if os.getenv(ENV_TIMEOUT):
            try:
                env_config['timeout'] = int(os.getenv(ENV_TIMEOUT, ''))
            except ValueError:
                pass
        
        if os.getenv(ENV_VERIFY_SSL):
            env_config['verify_ssl'] = os.getenv(ENV_VERIFY_SSL, '').lower() in ('true', '1', 'yes')
        
        return env_config
    
    def load(self) -> MubanConfig:
        """
        Load configuration from all sources.
        
        Priority (highest to lowest):
        1. Environment variables
        2. Configuration files
        3. Default values
        
        Returns:
            MubanConfig: The loaded configuration
        """
        # Start with file config
        config_data = self._load_from_file()
        
        # Override with environment variables
        env_config = self._load_from_env()
        config_data.update(env_config)
        
        # Create config object
        self._config = MubanConfig.from_dict(config_data)
        return self._config
    
    def save(self, config: MubanConfig) -> None:
        """
        Save configuration to files.
        
        Args:
            config: Configuration to save
        """
        self._ensure_config_dir()
        
        # Separate credentials from other config
        config_dict = config.to_dict()
        token = config_dict.pop('token', '')
        refresh_token = config_dict.pop('refresh_token', '')
        token_expires_at = config_dict.pop('token_expires_at', 0)
        
        # Save main config
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config_dict, f, indent=2)
            logger.debug(f"Saved config to {self.config_file}")
        except OSError as e:
            raise ConfigurationError(f"Cannot save config file: {e}")
        
        # Save credentials separately
        if token:
            try:
                creds = {'token': token}
                if refresh_token:
                    creds['refresh_token'] = refresh_token
                if token_expires_at:
                    creds['token_expires_at'] = token_expires_at
                with open(self.credentials_file, 'w', encoding='utf-8') as f:
                    json.dump(creds, f, indent=2)
                # Set restrictive permissions on credentials file
                try:
                    os.chmod(self.credentials_file, 0o600)
                except OSError:
                    pass  # May fail on Windows, that's okay
                logger.debug(f"Saved credentials to {self.credentials_file}")
            except OSError as e:
                raise ConfigurationError(f"Cannot save credentials file: {e}")
        
        self._config = config
    
    def get(self) -> MubanConfig:
        """
        Get current configuration.
        
        Returns:
            MubanConfig: Current configuration (loads if not already loaded)
        """
        if self._config is None:
            self.load()
        return self._config  # type: ignore
    
    def update(self, **kwargs: Any) -> MubanConfig:
        """
        Update specific configuration values.
        
        Args:
            **kwargs: Configuration values to update
        
        Returns:
            MubanConfig: Updated configuration
        """
        config = self.get()
        config_dict = config.to_dict()
        config_dict.update(kwargs)
        new_config = MubanConfig.from_dict(config_dict)
        self.save(new_config)
        return new_config
    
    def clear(self) -> None:
        """Clear all configuration."""
        if self.config_file.exists():
            self.config_file.unlink()
        if self.credentials_file.exists():
            self.credentials_file.unlink()
        self._config = None
    
    def get_config_path(self) -> Path:
        """Get the configuration directory path."""
        return self.config_dir


# Global config manager instance
_config_manager: Optional[ConfigManager] = None


def get_config_manager(config_dir: Optional[Path] = None) -> ConfigManager:
    """
    Get the global configuration manager.
    
    Args:
        config_dir: Optional custom configuration directory
    
    Returns:
        ConfigManager: The configuration manager instance
    """
    global _config_manager
    if _config_manager is None or config_dir is not None:
        _config_manager = ConfigManager(config_dir)
    return _config_manager


def get_config() -> MubanConfig:
    """
    Get the current configuration.
    
    Returns:
        MubanConfig: Current configuration
    """
    return get_config_manager().get()
