"""
Tests for Muban CLI authentication module.
"""

import pytest
from unittest.mock import MagicMock, patch, Mock, PropertyMock
import requests

from muban_cli.auth import MubanAuthClient
from muban_cli.config import MubanConfig
from muban_cli.exceptions import AuthenticationError, APIError


@pytest.fixture
def auth_config():
    """Create test configuration for auth."""
    return MubanConfig(
        server_url="https://api.muban.me",
        auth_server_url="https://auth.muban.me",
        timeout=30,
        verify_ssl=True
    )


@pytest.fixture
def auth_client(auth_config):
    """Create auth client with test config."""
    return MubanAuthClient(auth_config)


@pytest.fixture
def mock_session():
    """Create a mock requests session."""
    session = MagicMock(spec=requests.Session)
    return session


class TestMubanAuthClientInit:
    """Test MubanAuthClient initialization."""
    
    def test_init_with_config(self, auth_config):
        """Test client initialization."""
        client = MubanAuthClient(auth_config)
        assert client.config == auth_config
        assert client._session is None
    
    def test_session_created_on_access(self, auth_client):
        """Test session is created lazily."""
        assert auth_client._session is None
        session = auth_client.session
        assert session is not None
        assert auth_client._session is session
    
    def test_session_reused(self, auth_client):
        """Test same session is reused."""
        session1 = auth_client.session
        session2 = auth_client.session
        assert session1 is session2
    
    def test_auth_base_url(self, auth_client):
        """Test auth base URL resolution."""
        assert auth_client.auth_base_url == "https://auth.muban.me"
    
    def test_auth_base_url_fallback(self):
        """Test auth URL falls back to server URL."""
        config = MubanConfig(server_url="https://api.muban.me")
        client = MubanAuthClient(config)
        assert client.auth_base_url == "https://api.muban.me"


class TestLogin:
    """Test login functionality."""
    
    def test_login_success_json_format(self, auth_config, mock_session):
        """Test successful login with JSON response."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "accessToken": "test-jwt-token",
            "refreshToken": "test-refresh-token",
            "expiresIn": 3600,
            "tokenType": "Bearer"
        }
        mock_session.post.return_value = mock_response
        
        client = MubanAuthClient(auth_config)
        client._session = mock_session
        
        result = client.login("testuser", "password123", auth_endpoint="/auth/login")
        
        assert result["access_token"] == "test-jwt-token"
        assert result["refresh_token"] == "test-refresh-token"
        assert result["expires_in"] == 3600
    
    def test_login_success_snake_case(self, auth_config, mock_session):
        """Test login with snake_case response."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "test-jwt-token",
            "refresh_token": "test-refresh-token",
            "expires_in": 3600
        }
        mock_session.post.return_value = mock_response
        
        client = MubanAuthClient(auth_config)
        client._session = mock_session
        
        result = client.login("testuser", "password123", auth_endpoint="/oauth/token")
        
        assert result["access_token"] == "test-jwt-token"
    
    def test_login_success_nested_data(self, auth_config, mock_session):
        """Test login with nested data response."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {
                "accessToken": "nested-token",
                "refreshToken": "nested-refresh"
            }
        }
        mock_session.post.return_value = mock_response
        
        client = MubanAuthClient(auth_config)
        client._session = mock_session
        
        result = client.login("user", "pass", auth_endpoint="/auth/login")
        
        assert result["access_token"] == "nested-token"
    
    def test_login_invalid_credentials(self, auth_config, mock_session):
        """Test login with invalid credentials."""
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.json.return_value = {
            "message": "Invalid username or password"
        }
        mock_session.post.return_value = mock_response
        
        client = MubanAuthClient(auth_config)
        client._session = mock_session
        
        with pytest.raises(AuthenticationError) as exc_info:
            client.login("baduser", "badpass", auth_endpoint="/auth/login")
        
        assert "Invalid username or password" in str(exc_info.value)
    
    def test_login_bad_request(self, auth_config, mock_session):
        """Test login with bad request."""
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.json.return_value = {
            "error": "Missing required field"
        }
        mock_session.post.return_value = mock_response
        
        client = MubanAuthClient(auth_config)
        client._session = mock_session
        
        with pytest.raises(AuthenticationError) as exc_info:
            client.login("user", "pass", auth_endpoint="/auth/login")
        
        assert "Missing required field" in str(exc_info.value)
    
    def test_login_no_token_in_response(self, auth_config, mock_session):
        """Test login when response has no token."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "ok"  # No token field
        }
        mock_session.post.return_value = mock_response
        
        client = MubanAuthClient(auth_config)
        client._session = mock_session
        
        with pytest.raises(AuthenticationError) as exc_info:
            client.login("user", "pass", auth_endpoint="/auth/login")
        
        assert "no token" in str(exc_info.value).lower()


class TestHandleAuthResponse:
    """Test _handle_auth_response method."""
    
    def test_handle_success_response(self, auth_client):
        """Test handling successful response."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "my-token",
            "refresh_token": "my-refresh",
            "expires_in": 7200,
            "token_type": "Bearer"
        }
        
        result = auth_client._handle_auth_response(mock_response)
        
        assert result["access_token"] == "my-token"
        assert result["refresh_token"] == "my-refresh"
        assert result["expires_in"] == 7200
        assert result["token_type"] == "Bearer"
    
    def test_handle_401_with_json_error(self, auth_client):
        """Test handling 401 with JSON error message."""
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.json.return_value = {
            "error_description": "The user credentials were incorrect."
        }
        
        with pytest.raises(AuthenticationError) as exc_info:
            auth_client._handle_auth_response(mock_response)
        
        assert "incorrect" in str(exc_info.value).lower()
    
    def test_handle_401_no_json(self, auth_client):
        """Test handling 401 without JSON body."""
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.json.side_effect = ValueError("No JSON")
        
        with pytest.raises(AuthenticationError) as exc_info:
            auth_client._handle_auth_response(mock_response)
        
        assert "Invalid credentials" in str(exc_info.value)
    
    def test_handle_unexpected_status(self, auth_client):
        """Test handling unexpected status code."""
        mock_response = Mock()
        mock_response.status_code = 500
        
        with pytest.raises(APIError) as exc_info:
            auth_client._handle_auth_response(mock_response)
        
        assert exc_info.value.status_code == 500


class TestClientCredentials:
    """Test client credentials authentication."""
    
    def test_client_credentials_login(self, auth_config, mock_session):
        """Test login with client credentials."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "client-cred-token",
            "token_type": "Bearer",
            "expires_in": 3600
        }
        mock_session.post.return_value = mock_response
        
        client = MubanAuthClient(auth_config)
        client._session = mock_session
        
        result = client.client_credentials_login(
            client_id="my-client-id",
            client_secret="my-client-secret",
            auth_endpoint="/oauth/token"
        )
        
        assert result["access_token"] == "client-cred-token"


class TestTokenRefresh:
    """Test token refresh functionality."""
    
    def test_refresh_token_success(self, auth_config, mock_session):
        """Test successful token refresh."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "new-access-token",
            "refresh_token": "new-refresh-token",
            "expires_in": 3600
        }
        mock_session.post.return_value = mock_response
        
        client = MubanAuthClient(auth_config)
        client._session = mock_session
        
        result = client.refresh_token(
            "old-refresh-token",
            auth_endpoint="/auth/refresh"
        )
        
        assert result["access_token"] == "new-access-token"
    
    def test_refresh_token_expired(self, auth_config, mock_session):
        """Test refresh with expired token."""
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.json.return_value = {
            "error": "Refresh token expired"
        }
        mock_session.post.return_value = mock_response
        
        client = MubanAuthClient(auth_config)
        client._session = mock_session
        
        with pytest.raises(AuthenticationError):
            client.refresh_token(
                "expired-refresh-token",
                auth_endpoint="/auth/refresh"
            )
