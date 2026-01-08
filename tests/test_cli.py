"""
Tests for CLI commands.
"""

from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from muban_cli.cli import cli


@pytest.fixture
def runner():
    """Create CLI test runner."""
    return CliRunner()


@pytest.fixture
def mock_config():
    """Create mock configuration."""
    with patch('muban_cli.cli.get_config_manager') as mock:
        config_manager = MagicMock()
        config_manager.get.return_value = MagicMock(
            token="test-token",
            server_url="https://test.muban.me",
            timeout=30,
            verify_ssl=True,
            is_configured=MagicMock(return_value=True)
        )
        mock.return_value = config_manager
        yield config_manager


class TestCLI:
    """Tests for main CLI."""
    
    def test_version(self, runner):
        """Test version option."""
        result = runner.invoke(cli, ['--version'])
        assert result.exit_code == 0
        assert 'muban' in result.output.lower()
    
    def test_help(self, runner):
        """Test help output."""
        result = runner.invoke(cli, ['--help'])
        assert result.exit_code == 0
        assert 'Muban CLI' in result.output


class TestConfigureCommand:
    """Tests for configure command."""
    
    def test_configure_show(self, runner, mock_config):
        """Test showing current configuration."""
        result = runner.invoke(cli, ['configure', '--show'])
        assert result.exit_code == 0
        assert 'Configuration' in result.output
    
    def test_configure_with_server_option(self, runner, mock_config):
        """Test configuration with server option."""
        result = runner.invoke(cli, [
            'configure',
            '--server', 'https://new.server.com'
        ])
        assert result.exit_code == 0
        mock_config.update.assert_called()


class TestListCommand:
    """Tests for list command."""
    
    def test_list_not_configured(self, runner):
        """Test list when not configured."""
        with patch('muban_cli.cli.get_config_manager') as mock:
            config_manager = MagicMock()
            config_manager.get.return_value = MagicMock(
                token="",
                server_url="",
                is_configured=MagicMock(return_value=False)
            )
            mock.return_value = config_manager
            
            result = runner.invoke(cli, ['list'])
            assert result.exit_code == 1
            assert 'not configured' in result.output.lower()
    
    def test_list_templates(self, runner, mock_config):
        """Test listing templates."""
        mock_response = {
            'data': {
                'items': [
                    {
                        'id': 'test-id-1',
                        'name': 'Test Template',
                        'author': 'Test Author',
                        'fileSize': 1024,
                        'created': '2025-01-01T00:00:00Z'
                    }
                ],
                'totalItems': 1,
                'totalPages': 1
            }
        }
        
        with patch('muban_cli.cli.MubanAPIClient') as mock_client:
            mock_instance = MagicMock()
            mock_instance.__enter__ = MagicMock(return_value=mock_instance)
            mock_instance.__exit__ = MagicMock(return_value=False)
            mock_instance.list_templates.return_value = mock_response
            mock_client.return_value = mock_instance
            
            result = runner.invoke(cli, ['list'])
            
            assert result.exit_code == 0
            assert 'Test Template' in result.output


class TestGenerateCommand:
    """Tests for generate command."""
    
    def test_generate_basic(self, runner, mock_config, tmp_path):
        """Test basic document generation."""
        output_file = tmp_path / "output.pdf"
        
        with patch('muban_cli.cli.MubanAPIClient') as mock_client:
            mock_instance = MagicMock()
            mock_instance.__enter__ = MagicMock(return_value=mock_instance)
            mock_instance.__exit__ = MagicMock(return_value=False)
            mock_instance.generate_document.return_value = output_file
            mock_client.return_value = mock_instance
            
            result = runner.invoke(cli, [
                'generate', 'test-template-id',
                '-p', 'title=Test Report'
            ])
            
            assert result.exit_code == 0
            mock_instance.generate_document.assert_called_once()
    
    def test_generate_with_params_file(self, runner, mock_config, tmp_path):
        """Test generation with parameters file."""
        params_file = tmp_path / "params.json"
        params_file.write_text('{"title": "Test", "year": 2025}')
        output_file = tmp_path / "output.pdf"
        
        with patch('muban_cli.cli.MubanAPIClient') as mock_client:
            mock_instance = MagicMock()
            mock_instance.__enter__ = MagicMock(return_value=mock_instance)
            mock_instance.__exit__ = MagicMock(return_value=False)
            mock_instance.generate_document.return_value = output_file
            mock_client.return_value = mock_instance
            
            result = runner.invoke(cli, [
                'generate', 'test-template-id',
                '--params-file', str(params_file)
            ])
            
            assert result.exit_code == 0


class TestPushCommand:
    """Tests for push command."""
    
    def test_push_non_zip_file(self, runner, mock_config, tmp_path):
        """Test push with non-ZIP file."""
        txt_file = tmp_path / "test.txt"
        txt_file.write_text("test content")
        
        result = runner.invoke(cli, [
            'push', str(txt_file),
            '--name', 'Test',
            '--author', 'Author'
        ])
        
        assert result.exit_code == 1
        assert 'ZIP' in result.output


class TestDeleteCommand:
    """Tests for delete command."""
    
    def test_delete_with_confirmation(self, runner, mock_config):
        """Test delete with confirmation."""
        with patch('muban_cli.cli.MubanAPIClient') as mock_client:
            mock_instance = MagicMock()
            mock_instance.__enter__ = MagicMock(return_value=mock_instance)
            mock_instance.__exit__ = MagicMock(return_value=False)
            mock_client.return_value = mock_instance
            
            # Answer 'y' to confirmation
            result = runner.invoke(cli, ['delete', 'test-id'], input='y\n')
            
            assert result.exit_code == 0
            mock_instance.delete_template.assert_called_once()
    
    def test_delete_cancelled(self, runner, mock_config):
        """Test delete cancellation."""
        result = runner.invoke(cli, ['delete', 'test-id'], input='n\n')
        
        assert result.exit_code == 0
        assert 'Cancelled' in result.output


class TestAuditCommands:
    """Tests for audit commands."""
    
    def test_audit_health(self, runner, mock_config):
        """Test audit health command."""
        with patch('muban_cli.cli.MubanAPIClient') as mock_client:
            mock_instance = MagicMock()
            mock_instance.__enter__ = MagicMock(return_value=mock_instance)
            mock_instance.__exit__ = MagicMock(return_value=False)
            mock_instance.get_audit_health.return_value = {'data': 'OK'}
            mock_client.return_value = mock_instance
            
            result = runner.invoke(cli, ['audit', 'health'])
            
            assert result.exit_code == 0
