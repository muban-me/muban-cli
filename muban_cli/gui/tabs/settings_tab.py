"""
Settings Tab - Server configuration and authentication.
"""

import logging
from datetime import datetime
from typing import Optional

from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
    QGroupBox,
    QLabel,
    QLineEdit,
    QPushButton,
    QCheckBox,
    QSpinBox,
    QMessageBox,
    QProgressBar,
    QStyle,
)

from muban_cli.config import get_config_manager, MubanConfig
from muban_cli.auth import MubanAuthClient
from muban_cli.gui.icons import create_logout_icon, create_login_icon
from muban_cli.gui.error_dialog import show_error_dialog

logger = logging.getLogger(__name__)


class LoginWorker(QThread):
    """Worker thread for login operations."""

    finished = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, auth_client: MubanAuthClient, username: str, password: str):
        super().__init__()
        self.auth_client = auth_client
        self.username = username
        self.password = password

    def run(self):
        try:
            result = self.auth_client.login(self.username, self.password)
            self.finished.emit(result)
        except Exception as e:
            logger.exception("Login failed")
            self.error.emit(str(e))


class ClientCredentialsWorker(QThread):
    """Worker thread for client credentials login."""

    finished = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, auth_client: MubanAuthClient, client_id: str, client_secret: str):
        super().__init__()
        self.auth_client = auth_client
        self.client_id = client_id
        self.client_secret = client_secret

    def run(self):
        try:
            result = self.auth_client.client_credentials_login(self.client_id, self.client_secret)
            self.finished.emit(result)
        except Exception as e:
            logger.exception("Client credentials login failed")
            self.error.emit(str(e))


class SettingsTab(QWidget):
    """Tab for server and authentication settings."""

    def __init__(self):
        super().__init__()
        self._setup_ui()
        self._load_config()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        # Server configuration
        server_group = QGroupBox("Server Configuration")
        server_layout = QFormLayout(server_group)

        self.server_url_input = QLineEdit()
        self.server_url_input.setPlaceholderText("https://api.muban.me")
        server_layout.addRow("Server URL:", self.server_url_input)

        self.auth_server_input = QLineEdit()
        self.auth_server_input.setPlaceholderText("Optional: OAuth2/IdP URL if different")
        server_layout.addRow("Auth Server URL:", self.auth_server_input)

        self.verify_ssl_cb = QCheckBox("Verify SSL certificates")
        self.verify_ssl_cb.setChecked(True)
        server_layout.addRow("", self.verify_ssl_cb)

        self.timeout_spin = QSpinBox()
        self.timeout_spin.setRange(5, 300)
        self.timeout_spin.setValue(30)
        self.timeout_spin.setSuffix(" seconds")
        server_layout.addRow("Timeout:", self.timeout_spin)

        self.max_retries_spin = QSpinBox()
        self.max_retries_spin.setRange(0, 10)
        self.max_retries_spin.setValue(3)
        self.max_retries_spin.setToolTip("Max retries for transient errors (502, 503, 504, 429). Set to 0 to disable retries.")
        server_layout.addRow("Max Retries:", self.max_retries_spin)

        self.author_input = QLineEdit()
        self.author_input.setPlaceholderText("Default author for template uploads")
        server_layout.addRow("Default Author:", self.author_input)

        self.auto_upload_cb = QCheckBox("Auto-upload after packaging")
        self.auto_upload_cb.setToolTip("Automatically upload templates after successful packaging")
        server_layout.addRow("", self.auto_upload_cb)

        layout.addWidget(server_group)

        # Authentication - User credentials
        auth_group = QGroupBox("User Authentication")
        auth_layout = QFormLayout(auth_group)

        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("username@example.com")
        auth_layout.addRow("Username:", self.username_input)

        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setPlaceholderText("Password")
        auth_layout.addRow("Password:", self.password_input)

        login_btn_layout = QHBoxLayout()
        self.login_btn = QPushButton("Login")
        self.login_btn.setIcon(create_login_icon())
        self.login_btn.clicked.connect(self._login)
        login_btn_layout.addWidget(self.login_btn)
        login_btn_layout.addStretch()
        auth_layout.addRow("", login_btn_layout)

        layout.addWidget(auth_group)

        # Client credentials (OAuth2)
        oauth_group = QGroupBox("Client Credentials (Service Account)")
        oauth_layout = QFormLayout(oauth_group)

        self.client_id_input = QLineEdit()
        self.client_id_input.setPlaceholderText("Client ID")
        oauth_layout.addRow("Client ID:", self.client_id_input)

        self.client_secret_input = QLineEdit()
        self.client_secret_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.client_secret_input.setPlaceholderText("Client Secret")
        oauth_layout.addRow("Client Secret:", self.client_secret_input)

        client_btn_layout = QHBoxLayout()
        self.client_login_btn = QPushButton("Login with Client Credentials")
        self.client_login_btn.setIcon(create_login_icon())
        self.client_login_btn.clicked.connect(self._login_client_credentials)
        client_btn_layout.addWidget(self.client_login_btn)
        client_btn_layout.addStretch()
        oauth_layout.addRow("", client_btn_layout)

        layout.addWidget(oauth_group)

        # Status
        status_group = QGroupBox("Authentication Status")
        status_layout = QVBoxLayout(status_group)

        self.status_label = QLabel("Not authenticated")
        status_layout.addWidget(self.status_label)

        self.token_info_label = QLabel("")
        self.token_info_label.setStyleSheet("color: gray; font-size: 11px;")
        status_layout.addWidget(self.token_info_label)

        status_btn_layout = QHBoxLayout()
        self.refresh_btn = QPushButton("Refresh Token")
        self.refresh_btn.clicked.connect(self._refresh_token)
        self.refresh_btn.setEnabled(False)
        status_btn_layout.addWidget(self.refresh_btn)

        self.logout_btn = QPushButton("Logout")
        self.logout_btn.clicked.connect(self._logout)
        self.logout_btn.setEnabled(False)
        status_btn_layout.addWidget(self.logout_btn)
        
        # Apply icons
        style = self.style()
        if style:
            self.refresh_btn.setIcon(style.standardIcon(QStyle.StandardPixmap.SP_BrowserReload))
        self.logout_btn.setIcon(create_logout_icon())

        status_btn_layout.addStretch()
        status_layout.addLayout(status_btn_layout)

        layout.addWidget(status_group)

        # Progress
        self.progress = QProgressBar()
        self.progress.setVisible(False)
        layout.addWidget(self.progress)

        # Action buttons
        action_layout = QHBoxLayout()
        
        self.clear_btn = QPushButton("Clear Configuration")
        self.clear_btn.clicked.connect(self._clear_config)
        action_layout.addWidget(self.clear_btn)
        
        action_layout.addStretch()
        
        self.save_btn = QPushButton("Save Configuration")
        self.save_btn.clicked.connect(self._save_config)
        action_layout.addWidget(self.save_btn)
        
        # Apply icons to action buttons
        style = self.style()
        if style:
            self.clear_btn.setIcon(style.standardIcon(QStyle.StandardPixmap.SP_TrashIcon))
            self.save_btn.setIcon(style.standardIcon(QStyle.StandardPixmap.SP_DialogSaveButton))
        
        layout.addLayout(action_layout)

        layout.addStretch()

    def _load_config(self):
        """Load current configuration."""
        try:
            config = get_config_manager().load()
            self.server_url_input.setText(config.server_url or "")
            self.auth_server_input.setText(config.auth_server_url or "")
            self.verify_ssl_cb.setChecked(config.verify_ssl)
            self.timeout_spin.setValue(config.timeout)
            self.max_retries_spin.setValue(config.max_retries)
            self.author_input.setText(config.default_author or "")
            self.auto_upload_cb.setChecked(config.auto_upload_on_package)
            self.client_id_input.setText(config.client_id or "")
            self.client_secret_input.setText(config.client_secret or "")

            self._update_auth_status(config)
        except Exception as e:
            self.status_label.setText(f"⚠️ Error loading config: {e}")

    def _update_auth_status(self, config: Optional[MubanConfig] = None):
        """Update authentication status display."""
        if config is None:
            config = get_config_manager().load()

        if config.is_authenticated():
            self.status_label.setText("✓ Authenticated")
            self.status_label.setStyleSheet("color: green;")

            if config.token_expires_at:
                expires = datetime.fromtimestamp(config.token_expires_at)
                if config.is_token_expired():
                    self.token_info_label.setText(f"Token expired at {expires}")
                    self.token_info_label.setStyleSheet("color: red; font-size: 11px;")
                else:
                    self.token_info_label.setText(f"Token expires: {expires}")
                    self.token_info_label.setStyleSheet("color: gray; font-size: 11px;")
            else:
                self.token_info_label.setText("Token expiration unknown")

            self.refresh_btn.setEnabled(config.has_refresh_token())
            self.logout_btn.setEnabled(True)
        else:
            self.status_label.setText("Not authenticated")
            self.status_label.setStyleSheet("")
            self.token_info_label.setText("")
            self.refresh_btn.setEnabled(False)
            self.logout_btn.setEnabled(False)

    def _save_config(self):
        """Save configuration."""
        try:
            config = get_config_manager().load()
            config.server_url = self.server_url_input.text().strip()
            config.auth_server_url = self.auth_server_input.text().strip()
            config.verify_ssl = self.verify_ssl_cb.isChecked()
            config.timeout = self.timeout_spin.value()
            config.max_retries = self.max_retries_spin.value()
            config.default_author = self.author_input.text().strip()
            config.auto_upload_on_package = self.auto_upload_cb.isChecked()
            config.client_id = self.client_id_input.text().strip()
            config.client_secret = self.client_secret_input.text().strip()

            get_config_manager().save(config)
            QMessageBox.information(self, "Saved", "Configuration saved successfully.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save configuration: {e}")

    def _clear_config(self):
        """Clear all configuration."""
        reply = QMessageBox.question(
            self,
            "Clear Configuration",
            "Are you sure you want to clear all configuration?\n\n"
            "This will remove server URL, authentication tokens, and all settings.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
            
        try:
            get_config_manager().clear()
            
            # Clear all input fields
            self.server_url_input.clear()
            self.auth_server_input.clear()
            self.verify_ssl_cb.setChecked(True)
            self.timeout_spin.setValue(30)
            self.max_retries_spin.setValue(3)
            self.author_input.clear()
            self.auto_upload_cb.setChecked(False)
            self.username_input.clear()
            self.password_input.clear()
            self.client_id_input.clear()
            self.client_secret_input.clear()
            
            # Update auth status
            self._update_auth_status(MubanConfig())
            
            QMessageBox.information(self, "Cleared", "Configuration cleared successfully.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to clear configuration: {e}")

    def _get_auth_client(self) -> MubanAuthClient:
        """Get auth client with current config."""
        config = get_config_manager().load()
        config.server_url = self.server_url_input.text().strip()
        config.auth_server_url = self.auth_server_input.text().strip()
        config.verify_ssl = self.verify_ssl_cb.isChecked()
        config.client_id = self.client_id_input.text().strip()
        config.client_secret = self.client_secret_input.text().strip()
        return MubanAuthClient(config)

    def _login(self):
        """Login with username/password."""
        username = self.username_input.text().strip()
        password = self.password_input.text()

        if not username or not password:
            QMessageBox.warning(self, "Error", "Please enter username and password.")
            return

        self._set_ui_enabled(False)
        self.progress.setVisible(True)
        self.progress.setRange(0, 0)

        auth_client = self._get_auth_client()
        self.login_worker = LoginWorker(auth_client, username, password)
        self.login_worker.finished.connect(self._on_login_finished)
        self.login_worker.error.connect(self._on_login_error)
        self.login_worker.start()

    def _on_login_finished(self, result: dict):
        """Handle successful login."""
        self._set_ui_enabled(True)
        self.progress.setVisible(False)
        self.password_input.clear()

        # Save the tokens from the login result
        self._save_token_result(result)
        
        # Also save form settings
        self._save_config()
        self._update_auth_status()

        QMessageBox.information(self, "Login Successful", "You are now logged in.")

    def _save_token_result(self, result: dict):
        """Save token result to config."""
        config = get_config_manager().load()
        
        if "access_token" in result:
            config.token = result["access_token"]
        if "refresh_token" in result:
            config.refresh_token = result["refresh_token"]
        if "expires_in" in result:
            import time
            config.token_expires_at = int(time.time()) + result["expires_in"]
        elif "expires_at" in result:
            config.token_expires_at = result["expires_at"]
            
        get_config_manager().save(config)

    def _on_login_error(self, error: str):
        """Handle login error."""
        self._set_ui_enabled(True)
        self.progress.setVisible(False)
        show_error_dialog(self, "Login Failed", error)

    def _login_client_credentials(self):
        """Login with client credentials."""
        client_id = self.client_id_input.text().strip()
        client_secret = self.client_secret_input.text().strip()

        if not client_id or not client_secret:
            QMessageBox.warning(self, "Error", "Please enter client ID and secret.")
            return

        self._set_ui_enabled(False)
        self.progress.setVisible(True)
        self.progress.setRange(0, 0)

        auth_client = self._get_auth_client()
        self.client_worker = ClientCredentialsWorker(auth_client, client_id, client_secret)
        self.client_worker.finished.connect(self._on_login_finished)
        self.client_worker.error.connect(self._on_login_error)
        self.client_worker.start()

    def _refresh_token(self):
        """Refresh the access token."""
        try:
            config = get_config_manager().load()
            if not config.refresh_token:
                QMessageBox.warning(self, "Error", "No refresh token available.")
                return
            auth_client = self._get_auth_client()
            auth_client.refresh_token(config.refresh_token)
            self._update_auth_status()
            QMessageBox.information(self, "Token Refreshed", "Access token has been refreshed.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to refresh token: {e}")

    def _logout(self):
        """Logout and clear credentials."""
        reply = QMessageBox.question(
            self,
            "Confirm Logout",
            "Are you sure you want to logout?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        try:
            config = get_config_manager().load()
            config.token = ""
            config.refresh_token = ""
            config.token_expires_at = 0
            get_config_manager().save(config)
            self._update_auth_status()
            QMessageBox.information(self, "Logged Out", "You have been logged out.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to logout: {e}")

    def _set_ui_enabled(self, enabled: bool):
        """Enable/disable UI elements."""
        self.server_url_input.setEnabled(enabled)
        self.auth_server_input.setEnabled(enabled)
        self.verify_ssl_cb.setEnabled(enabled)
        self.timeout_spin.setEnabled(enabled)
        self.max_retries_spin.setEnabled(enabled)
        self.username_input.setEnabled(enabled)
        self.password_input.setEnabled(enabled)
        self.login_btn.setEnabled(enabled)
        self.client_id_input.setEnabled(enabled)
        self.client_secret_input.setEnabled(enabled)
        self.client_login_btn.setEnabled(enabled)
        self.save_btn.setEnabled(enabled)
