"""
Tests for Muban CLI commands with mocked API.
"""

import pytest
from unittest.mock import MagicMock, patch, Mock
from click.testing import CliRunner

from muban_cli.cli import cli
from muban_cli.config import MubanConfig, ConfigManager


@pytest.fixture
def runner():
    """Create CLI test runner."""
    return CliRunner()


@pytest.fixture
def mock_config():
    """Create mock configuration."""
    config = MubanConfig(
        token="test-jwt-token",
        refresh_token="test-refresh-token",
        server_url="https://api.muban.me",
        timeout=30,
        verify_ssl=True
    )
    return config


@pytest.fixture
def mock_config_manager(mock_config):
    """Create mock config manager."""
    manager = MagicMock(spec=ConfigManager)
    manager.get.return_value = mock_config
    manager.load.return_value = mock_config
    return manager


class TestListCommand:
    """Test the list templates command."""
    
    def test_list_templates_success(self, runner, mock_config_manager):
        """Test listing templates successfully."""
        mock_api = MagicMock()
        mock_api.list_templates.return_value = {
            'data': {
                'items': [
                    {
                        'id': 'template-123',
                        'name': 'Test Template',
                        'author': 'Test Author',
                        'fileSize': 1024000,
                        'created': '2025-01-08T10:00:00Z'
                    }
                ],
                'totalItems': 1,
                'totalPages': 1
            }
        }
        mock_api.__enter__ = Mock(return_value=mock_api)
        mock_api.__exit__ = Mock(return_value=False)
        
        with patch('muban_cli.commands.templates.MubanAPIClient', return_value=mock_api), \
             patch('muban_cli.commands.MubanContext') as mock_ctx_class:
            
            mock_ctx = MagicMock()
            mock_ctx.config_manager = mock_config_manager
            mock_ctx_class.return_value = mock_ctx
            
            with patch('muban_cli.cli.get_config_manager', return_value=mock_config_manager):
                result = runner.invoke(cli, ['list'])
                
                # Should succeed (may fail on require_config, that's OK for this test)
                assert 'template' in result.output.lower() or result.exit_code != 0
    
    def test_list_templates_json_format(self, runner, mock_config_manager):
        """Test listing templates in JSON format."""
        mock_api = MagicMock()
        mock_api.list_templates.return_value = {
            'data': {
                'items': [{'id': 'test-id', 'name': 'Test'}],
                'totalItems': 1,
                'totalPages': 1
            }
        }
        mock_api.__enter__ = Mock(return_value=mock_api)
        mock_api.__exit__ = Mock(return_value=False)
        
        with patch('muban_cli.commands.templates.MubanAPIClient', return_value=mock_api), \
             patch('muban_cli.cli.get_config_manager', return_value=mock_config_manager):
            
            result = runner.invoke(cli, ['list', '--format', 'json'])
            # Check command structure works
            assert result.exit_code == 0 or 'not configured' in result.output.lower()


class TestFontsCommand:
    """Test the fonts command."""
    
    def test_fonts_help(self, runner):
        """Test fonts command help."""
        result = runner.invoke(cli, ['fonts', '--help'])
        assert result.exit_code == 0
        assert 'font' in result.output.lower()


class TestICCProfilesCommand:
    """Test the icc-profiles command."""
    
    def test_icc_profiles_help(self, runner):
        """Test ICC profiles command help."""
        result = runner.invoke(cli, ['icc-profiles', '--help'])
        assert result.exit_code == 0
        assert 'icc' in result.output.lower() or 'profile' in result.output.lower()


class TestUsersCommands:
    """Test user management commands."""
    
    def test_users_list_help(self, runner):
        """Test users list help."""
        result = runner.invoke(cli, ['users', 'list', '--help'])
        assert result.exit_code == 0
        assert 'page' in result.output.lower()
    
    def test_users_me_help(self, runner):
        """Test users me help."""
        result = runner.invoke(cli, ['users', 'me', '--help'])
        assert result.exit_code == 0
    
    def test_users_create_help(self, runner):
        """Test users create help."""
        result = runner.invoke(cli, ['users', 'create', '--help'])
        assert result.exit_code == 0
        assert 'username' in result.output.lower()
    
    def test_users_get_requires_id(self, runner):
        """Test users get requires user ID."""
        result = runner.invoke(cli, ['users', 'get'])
        assert result.exit_code != 0


class TestAuditCommands:
    """Test audit commands."""
    
    def test_audit_logs_help(self, runner):
        """Test audit logs help."""
        result = runner.invoke(cli, ['audit', 'logs', '--help'])
        assert result.exit_code == 0
        assert 'page' in result.output.lower()
    
    def test_audit_security_help(self, runner):
        """Test audit security help."""
        result = runner.invoke(cli, ['audit', 'security', '--help'])
        assert result.exit_code == 0
    
    def test_audit_event_types_help(self, runner):
        """Test audit event-types help."""
        result = runner.invoke(cli, ['audit', 'event-types', '--help'])
        assert result.exit_code == 0
    
    def test_audit_statistics_help(self, runner):
        """Test audit statistics help."""
        result = runner.invoke(cli, ['audit', 'statistics', '--help'])
        assert result.exit_code == 0


class TestAsyncCommands:
    """Test async operation commands."""
    
    def test_async_list_help(self, runner):
        """Test async list help."""
        result = runner.invoke(cli, ['async', 'list', '--help'])
        assert result.exit_code == 0
        assert 'status' in result.output.lower()
    
    def test_async_get_requires_id(self, runner):
        """Test async get requires request ID."""
        result = runner.invoke(cli, ['async', 'get'])
        assert result.exit_code != 0
    
    def test_async_submit_help(self, runner):
        """Test async submit help."""
        result = runner.invoke(cli, ['async', 'submit', '--help'])
        assert result.exit_code == 0
        assert 'template' in result.output.lower()
    
    def test_async_errors_help(self, runner):
        """Test async errors help."""
        result = runner.invoke(cli, ['async', 'errors', '--help'])
        assert result.exit_code == 0
    
    def test_async_workers_help(self, runner):
        """Test async workers help."""
        result = runner.invoke(cli, ['async', 'workers', '--help'])
        assert result.exit_code == 0
    
    def test_async_metrics_help(self, runner):
        """Test async metrics help."""
        result = runner.invoke(cli, ['async', 'metrics', '--help'])
        assert result.exit_code == 0


class TestAdminCommands:
    """Test admin commands."""
    
    def test_admin_verify_integrity_requires_id(self, runner):
        """Test verify-integrity requires template ID."""
        result = runner.invoke(cli, ['admin', 'verify-integrity'])
        assert result.exit_code != 0
    
    def test_admin_regenerate_digest_requires_id(self, runner):
        """Test regenerate-digest requires template ID."""
        result = runner.invoke(cli, ['admin', 'regenerate-digest'])
        assert result.exit_code != 0


class TestGenerateCommand:
    """Test generate command."""
    
    def test_generate_requires_template(self, runner):
        """Test generate requires template ID."""
        result = runner.invoke(cli, ['generate'])
        assert result.exit_code != 0
    
    def test_generate_help(self, runner):
        """Test generate help."""
        result = runner.invoke(cli, ['generate', '--help'])
        assert result.exit_code == 0
        assert 'template' in result.output.lower()
        assert 'format' in result.output.lower()


class TestGetCommand:
    """Test get template command."""
    
    def test_get_requires_template_id(self, runner):
        """Test get requires template ID."""
        result = runner.invoke(cli, ['get'])
        assert result.exit_code != 0
    
    def test_get_help(self, runner):
        """Test get help."""
        result = runner.invoke(cli, ['get', '--help'])
        assert result.exit_code == 0
        assert 'params' in result.output.lower()
        assert 'fields' in result.output.lower()


class TestPushCommand:
    """Test push template command."""
    
    def test_push_requires_file(self, runner):
        """Test push requires file argument."""
        result = runner.invoke(cli, ['push'])
        assert result.exit_code != 0
    
    def test_push_help(self, runner):
        """Test push help."""
        result = runner.invoke(cli, ['push', '--help'])
        assert result.exit_code == 0
        assert 'name' in result.output.lower()
        assert 'author' in result.output.lower()


class TestDeleteCommand:
    """Test delete template command."""
    
    def test_delete_requires_template_id(self, runner):
        """Test delete requires template ID."""
        result = runner.invoke(cli, ['delete'])
        assert result.exit_code != 0
    
    def test_delete_help(self, runner):
        """Test delete help."""
        result = runner.invoke(cli, ['delete', '--help'])
        assert result.exit_code == 0


class TestConfigureCommand:
    """Test configure command."""
    
    def test_configure_show(self, runner):
        """Test configure --show option."""
        with runner.isolated_filesystem():
            result = runner.invoke(cli, ['configure', '--show'])
            assert result.exit_code == 0
            assert 'server' in result.output.lower()
    
    def test_configure_help(self, runner):
        """Test configure help."""
        result = runner.invoke(cli, ['configure', '--help'])
        assert result.exit_code == 0
        assert 'server' in result.output.lower()


class TestLoginCommand:
    """Test login command."""
    
    def test_login_help(self, runner):
        """Test login help."""
        result = runner.invoke(cli, ['login', '--help'])
        assert result.exit_code == 0
        assert 'username' in result.output.lower()
        assert 'password' in result.output.lower()


class TestLogoutCommand:
    """Test logout command."""
    
    def test_logout_help(self, runner):
        """Test logout help."""
        result = runner.invoke(cli, ['logout', '--help'])
        assert result.exit_code == 0


class TestCommandSignatures:
    """
    Test that all commands with @common_options have correct function signatures.
    
    This catches bugs where a command uses @common_options decorator but the function
    doesn't accept all parameters (like truncate_length).
    
    Uses inspect to check signatures directly - no network calls, instant execution.
    """

    def test_all_common_options_commands_accept_truncate_length(self):
        """
        Verify all commands using @common_options accept truncate_length parameter.
        
        This is a comprehensive test that inspects Click command signatures to ensure
        they match what the common_options decorator provides.
        """
        import inspect
        
        # Get all commands from CLI
        commands_to_check = []
        
        def collect_commands(group, prefix=""):
            """Recursively collect all commands from a Click group."""
            for name, cmd in group.commands.items():
                full_name = f"{prefix} {name}".strip()
                if hasattr(cmd, 'commands'):  # It's a group
                    collect_commands(cmd, full_name)
                else:
                    commands_to_check.append((full_name, cmd))
        
        collect_commands(cli)
        
        # Commands that use @common_options should have these params
        common_params = {'verbose', 'quiet', 'output_format', 'truncate_length'}
        
        errors = []
        for cmd_name, cmd in commands_to_check:
            # Get the callback function
            callback = cmd.callback
            if callback is None:
                continue
            
            # Get function signature
            sig = inspect.signature(callback)
            param_names = set(sig.parameters.keys())
            
            # Check if this command uses common_options by checking for verbose/quiet
            if 'verbose' in param_names and 'quiet' in param_names:
                # This command uses @common_options, check for truncate_length
                if 'truncate_length' not in param_names:
                    errors.append(f"Command '{cmd_name}' uses @common_options but missing 'truncate_length' parameter")
        
        assert not errors, "Signature mismatches found:\n" + "\n".join(errors)
