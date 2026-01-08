"""
Simple CLI tests that don't require complex mocking.

These tests verify CLI structure and basic behavior without hitting APIs.
"""

import pytest
from click.testing import CliRunner

from muban_cli.cli import cli


@pytest.fixture
def runner():
    """Create CLI test runner."""
    return CliRunner()


class TestCLIStructure:
    """Test CLI structure and help output."""
    
    def test_version(self, runner):
        """Test version option."""
        result = runner.invoke(cli, ['--version'])
        assert result.exit_code == 0
        assert 'muban' in result.output.lower()
    
    def test_help(self, runner):
        """Test main help."""
        result = runner.invoke(cli, ['--help'])
        assert result.exit_code == 0
        assert 'Muban CLI' in result.output
    
    def test_login_help(self, runner):
        """Test login help."""
        result = runner.invoke(cli, ['login', '--help'])
        assert result.exit_code == 0
        assert 'username' in result.output.lower()
    
    def test_list_help(self, runner):
        """Test list help."""
        result = runner.invoke(cli, ['list', '--help'])
        assert result.exit_code == 0
        assert 'template' in result.output.lower()
    
    def test_generate_help(self, runner):
        """Test generate help."""
        result = runner.invoke(cli, ['generate', '--help'])
        assert result.exit_code == 0
        assert 'template' in result.output.lower()
    
    def test_configure_help(self, runner):
        """Test configure help."""
        result = runner.invoke(cli, ['configure', '--help'])
        assert result.exit_code == 0
        assert 'server' in result.output.lower()
    
    def test_users_help(self, runner):
        """Test users group help."""
        result = runner.invoke(cli, ['users', '--help'])
        assert result.exit_code == 0
        assert 'list' in result.output
        assert 'create' in result.output
    
    def test_audit_help(self, runner):
        """Test audit group help."""
        result = runner.invoke(cli, ['audit', '--help'])
        assert result.exit_code == 0
        assert 'logs' in result.output
    
    def test_admin_help(self, runner):
        """Test admin group help."""
        result = runner.invoke(cli, ['admin', '--help'])
        assert result.exit_code == 0
    
    def test_unknown_command(self, runner):
        """Test unknown command error."""
        result = runner.invoke(cli, ['unknown-cmd'])
        assert result.exit_code != 0


class TestCLIBasicValidation:
    """Test CLI argument validation without API calls."""
    
    def test_generate_missing_template_id(self, runner):
        """Test generate requires template ID."""
        result = runner.invoke(cli, ['generate'])
        assert result.exit_code != 0
        # Should show missing argument error
    
    def test_push_missing_file(self, runner):
        """Test push requires file argument."""
        result = runner.invoke(cli, ['push'])
        assert result.exit_code != 0
    
    def test_get_missing_template_id(self, runner):
        """Test get requires template ID."""
        result = runner.invoke(cli, ['get'])
        assert result.exit_code != 0
    
    def test_delete_missing_template_id(self, runner):
        """Test delete requires template ID."""
        result = runner.invoke(cli, ['delete'])
        assert result.exit_code != 0
