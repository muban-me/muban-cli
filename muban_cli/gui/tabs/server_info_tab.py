"""
Server Info Tab - Display server resources (fonts, ICC profiles).
"""

import logging
from typing import Optional, List, Dict, Any

from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGroupBox,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QProgressBar,
    QMessageBox,
    QSplitter,
    QListWidget,
    QListWidgetItem,
    QStyle,
)

from muban_cli.api import MubanAPIClient
from muban_cli.config import get_config_manager

logger = logging.getLogger(__name__)


class FontsWorker(QThread):
    """Worker thread for loading fonts."""

    finished = pyqtSignal(list)
    error = pyqtSignal(str)

    def __init__(self, client: MubanAPIClient):
        super().__init__()
        self.client = client

    def run(self):
        try:
            result = self.client.get_fonts()
            # Extract fonts from API response
            if isinstance(result, dict):
                if "data" in result:
                    fonts = result["data"]
                elif "content" in result:
                    fonts = result["content"]
                else:
                    fonts = result
            else:
                fonts = result
            self.finished.emit(fonts if isinstance(fonts, list) else [])
        except Exception as e:
            logger.exception("Failed to load fonts")
            self.error.emit(str(e))


class ICCProfilesWorker(QThread):
    """Worker thread for loading ICC profiles."""

    finished = pyqtSignal(list)
    error = pyqtSignal(str)

    def __init__(self, client: MubanAPIClient):
        super().__init__()
        self.client = client

    def run(self):
        try:
            result = self.client.get_icc_profiles()
            # Extract profiles from API response
            if isinstance(result, dict):
                if "data" in result:
                    profiles = result["data"]
                elif "content" in result:
                    profiles = result["content"]
                else:
                    profiles = result
            else:
                profiles = result
            self.finished.emit(profiles if isinstance(profiles, list) else [])
        except Exception as e:
            logger.exception("Failed to load ICC profiles")
            self.error.emit(str(e))


class ServerInfoTab(QWidget):
    """Tab for displaying server information (fonts, ICC profiles)."""

    def __init__(self):
        super().__init__()
        self._fonts: List[Dict[str, Any]] = []
        self._icc_profiles: List[str] = []
        self._loaded = False
        self._fonts_loading = False
        self._icc_loading = False
        self._fonts_worker: Optional[FontsWorker] = None
        self._icc_worker: Optional[ICCProfilesWorker] = None
        
        # Timeout timer to prevent indefinite hangs
        self._timeout_timer = QTimer(self)
        self._timeout_timer.setSingleShot(True)
        self._timeout_timer.timeout.connect(self._on_loading_timeout)
        
        self._setup_ui()

    def showEvent(self, event):
        """Load data when tab is first shown."""
        super().showEvent(event)
        if not self._loaded:
            self._loaded = True
            self._load_all()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        # Refresh button at top
        refresh_layout = QHBoxLayout()
        self.refresh_btn = QPushButton("Refresh Server Info")
        self.refresh_btn.clicked.connect(self._load_all)
        style = self.style()
        if style:
            self.refresh_btn.setIcon(style.standardIcon(QStyle.StandardPixmap.SP_BrowserReload))
        refresh_layout.addWidget(self.refresh_btn)
        refresh_layout.addStretch()
        layout.addLayout(refresh_layout)

        # Progress bar
        self.progress = QProgressBar()
        self.progress.setVisible(False)
        layout.addWidget(self.progress)

        # Splitter for fonts and ICC profiles
        splitter = QSplitter(Qt.Orientation.Vertical)

        # Fonts section
        fonts_group = QGroupBox("Available Fonts")
        fonts_layout = QVBoxLayout(fonts_group)

        fonts_info = QLabel(
            "Fonts available on the server for use in JRXML templates (fontName attribute)."
        )
        fonts_info.setWordWrap(True)
        fonts_layout.addWidget(fonts_info)

        self.fonts_table = QTableWidget(0, 4)
        self.fonts_table.setHorizontalHeaderLabels(["Font Name", "Faces", "PDF Embedded", "Source"])
        fonts_header = self.fonts_table.horizontalHeader()
        if fonts_header:
            fonts_header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.fonts_table.setColumnWidth(0, 250)
        self.fonts_table.setColumnWidth(1, 200)
        self.fonts_table.setColumnWidth(2, 100)
        self.fonts_table.setColumnWidth(3, 80)
        self.fonts_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.fonts_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.fonts_table.setAlternatingRowColors(True)
        fonts_layout.addWidget(self.fonts_table)

        self.fonts_count_label = QLabel("No fonts loaded")
        fonts_layout.addWidget(self.fonts_count_label)

        splitter.addWidget(fonts_group)

        # ICC Profiles section
        icc_group = QGroupBox("Available ICC Profiles")
        icc_layout = QVBoxLayout(icc_group)

        icc_info = QLabel(
            "ICC color profiles available for PDF export (pdfExportOptions.iccProfile). "
            "Used for CMYK color management in professional printing."
        )
        icc_info.setWordWrap(True)
        icc_layout.addWidget(icc_info)

        self.icc_list = QListWidget()
        self.icc_list.setAlternatingRowColors(True)
        icc_layout.addWidget(self.icc_list)

        self.icc_count_label = QLabel("No ICC profiles loaded")
        icc_layout.addWidget(self.icc_count_label)

        splitter.addWidget(icc_group)

        # Set initial splitter sizes (fonts get more space)
        splitter.setSizes([400, 200])

        layout.addWidget(splitter)

    def _get_client(self) -> Optional[MubanAPIClient]:
        """Get API client with current config."""
        try:
            config = get_config_manager().load()
            return MubanAPIClient(config)
        except Exception as e:
            QMessageBox.warning(
                self,
                "Configuration Error",
                f"Failed to load configuration: {e}\n\nPlease configure settings first.",
            )
            return None

    def _load_all(self):
        """Load both fonts and ICC profiles."""
        client = self._get_client()
        if not client:
            return

        # Stop any existing workers
        self._cleanup_workers()

        self._set_ui_enabled(False)
        self.progress.setVisible(True)
        self.progress.setRange(0, 0)

        # Reset loading flags
        self._fonts_loading = True
        self._icc_loading = True

        # Start timeout timer using configured timeout (in seconds, convert to ms)
        config = get_config_manager().load()
        timeout_ms = config.timeout * 1000
        self._timeout_timer.start(timeout_ms)

        # Load fonts
        self._fonts_worker = FontsWorker(client)
        self._fonts_worker.finished.connect(self._on_fonts_loaded)
        self._fonts_worker.error.connect(self._on_fonts_error)
        self._fonts_worker.start()

        # Load ICC profiles (use separate client)
        client2 = self._get_client()
        if client2:
            self._icc_worker = ICCProfilesWorker(client2)
            self._icc_worker.finished.connect(self._on_icc_loaded)
            self._icc_worker.error.connect(self._on_icc_error)
            self._icc_worker.start()
        else:
            # Mark ICC loading as done if client creation failed
            self._icc_loading = False
            self.icc_count_label.setText("Error: Could not create API client")
            self._check_loading_complete()

    def _cleanup_workers(self):
        """Stop and clean up any running workers."""
        self._timeout_timer.stop()
        
        if self._fonts_worker is not None:
            if self._fonts_worker.isRunning():
                self._fonts_worker.quit()
                self._fonts_worker.wait(1000)  # Wait up to 1 second
            self._fonts_worker = None
        
        if self._icc_worker is not None:
            if self._icc_worker.isRunning():
                self._icc_worker.quit()
                self._icc_worker.wait(1000)
            self._icc_worker = None
        
        self._fonts_loading = False
        self._icc_loading = False

    def _on_fonts_loaded(self, fonts: list):
        """Handle loaded fonts."""
        self._fonts_loading = False
        self._fonts = fonts
        self.fonts_table.setRowCount(len(fonts))

        for i, font in enumerate(fonts):
            # Font name
            name = font.get("name", "Unknown")
            name_item = QTableWidgetItem(name)
            name_item.setToolTip(f"Use in JRXML: fontName=\"{name}\"")
            self.fonts_table.setItem(i, 0, name_item)

            # Faces (normal, bold, italic, boldItalic)
            faces = font.get("faces", [])
            faces_str = ", ".join(faces) if faces else "normal"
            faces_item = QTableWidgetItem(faces_str)
            self.fonts_table.setItem(i, 1, faces_item)

            # PDF Embedded
            pdf_embedded = font.get("pdfEmbedded", False)
            embedded_item = QTableWidgetItem("Yes" if pdf_embedded else "No")
            embedded_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.fonts_table.setItem(i, 2, embedded_item)

            # Source
            source = font.get("source", "SERVER")
            source_item = QTableWidgetItem(source)
            source_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.fonts_table.setItem(i, 3, source_item)

        self.fonts_count_label.setText(f"{len(fonts)} font(s) available")
        self._check_loading_complete()

    def _on_fonts_error(self, error: str):
        """Handle fonts loading error."""
        self._fonts_loading = False
        self.fonts_count_label.setText(f"Error: {error}")
        self._check_loading_complete()

    def _on_icc_loaded(self, profiles: list):
        """Handle loaded ICC profiles."""
        self._icc_loading = False
        self._icc_profiles = profiles
        self.icc_list.clear()

        for profile in profiles:
            item = QListWidgetItem(profile)
            item.setToolTip(f'Use in request: "iccProfile": "{profile}"')
            self.icc_list.addItem(item)

        self.icc_count_label.setText(f"{len(profiles)} ICC profile(s) available")
        self._check_loading_complete()

    def _on_icc_error(self, error: str):
        """Handle ICC profiles loading error."""
        self._icc_loading = False
        self.icc_count_label.setText(f"Error: {error}")
        self._check_loading_complete()

    def _on_loading_timeout(self):
        """Handle loading timeout - force completion."""
        logger.warning("Server info loading timed out")
        
        if self._fonts_loading:
            self._fonts_loading = False
            self.fonts_count_label.setText("Error: Request timed out")
        
        if self._icc_loading:
            self._icc_loading = False
            self.icc_count_label.setText("Error: Request timed out")
        
        self._cleanup_workers()
        self._set_ui_enabled(True)
        self.progress.setVisible(False)
        
        QMessageBox.warning(
            self,
            "Timeout",
            "Server requests timed out. Please check your connection and try again."
        )

    def _check_loading_complete(self):
        """Check if all loading is complete."""
        if not self._fonts_loading and not self._icc_loading:
            self._timeout_timer.stop()
            self._set_ui_enabled(True)
            self.progress.setVisible(False)

    def _set_ui_enabled(self, enabled: bool):
        """Enable/disable UI elements."""
        self.refresh_btn.setEnabled(enabled)
        self.fonts_table.setEnabled(enabled)
        self.icc_list.setEnabled(enabled)
