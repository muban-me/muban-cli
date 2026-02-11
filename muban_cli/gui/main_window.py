"""
Muban GUI - Main Window.
"""

from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import (
    QMainWindow,
    QTabWidget,
    QStatusBar,
    QMessageBox,
)

from muban_cli import __version__, __prog_name__
from muban_cli.gui.tabs.package_tab import PackageTab
from muban_cli.gui.tabs.templates_tab import TemplatesTab
from muban_cli.gui.tabs.generate_tab import GenerateTab
from muban_cli.gui.tabs.settings_tab import SettingsTab
from muban_cli.gui.tabs.server_info_tab import ServerInfoTab


class MubanMainWindow(QMainWindow):
    """Main application window with tabbed interface."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{__prog_name__} - Document Generation Tool")
        self.setMinimumSize(1000, 750)
        self.resize(1100, 800)

        self._setup_menu()
        self._setup_tabs()
        self._setup_statusbar()

    def _setup_menu(self):
        """Setup the menu bar."""
        menubar = self.menuBar()
        if not menubar:
            return

        # File menu
        file_menu = menubar.addMenu("&File")
        if file_menu:
            exit_action = QAction("E&xit", self)
            exit_action.setShortcut("Ctrl+Q")
            exit_action.triggered.connect(self.close)
            file_menu.addAction(exit_action)

        # Help menu
        help_menu = menubar.addMenu("&Help")
        if help_menu:
            about_action = QAction("&About", self)
            about_action.triggered.connect(self._show_about)
            help_menu.addAction(about_action)

    def _setup_tabs(self):
        """Setup the main tab widget."""
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)

        # Create tabs
        self.package_tab = PackageTab()
        self.templates_tab = TemplatesTab()
        self.generate_tab = GenerateTab()
        self.server_info_tab = ServerInfoTab()
        self.settings_tab = SettingsTab()

        # Add tabs
        self.tabs.addTab(self.package_tab, "📦 Package")
        self.tabs.addTab(self.templates_tab, "📄 Templates")
        self.tabs.addTab(self.generate_tab, "⚙️ Generate")
        self.tabs.addTab(self.server_info_tab, "🖥️ Server Info")
        self.tabs.addTab(self.settings_tab, "⚙️ Settings")

        self.setCentralWidget(self.tabs)

    def _setup_statusbar(self):
        """Setup the status bar."""
        self.statusbar = QStatusBar()
        self.setStatusBar(self.statusbar)
        self.statusbar.showMessage("Ready")

    def _show_about(self):
        """Show about dialog."""
        QMessageBox.about(
            self,
            f"About {__prog_name__}",
            f"<h3>{__prog_name__} v{__version__}</h3>"
            "<p>A graphical interface for the Muban Document Generation Service.</p>"
            "<p>Features:</p>"
            "<ul>"
            "<li>Package JRXML templates with dependencies</li>"
            "<li>Manage templates on the server</li>"
            "<li>Generate PDF, XLSX, DOCX documents</li>"
            "<li>Configure server and authentication</li>"
            "</ul>"
            "<p><a href='https://muban.me'>https://muban.me</a></p>"
        )

    def show_status(self, message: str, timeout: int = 5000):
        """Show a message in the status bar."""
        self.statusbar.showMessage(message, timeout)
