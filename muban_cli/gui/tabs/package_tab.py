"""
Package Tab - Template packaging (JRXML/DOCX) with dependencies.
"""

import logging
from pathlib import Path
from typing import List, Optional

from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
    QGroupBox,
    QLineEdit,
    QPushButton,
    QFileDialog,
    QTextEdit,
    QCheckBox,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QMessageBox,
    QProgressBar,
    QSplitter,
    QLabel,
    QStyle,
)

from muban_cli.packager import JRXMLPackager, PackageResult, FontSpec
from muban_cli.config import get_config_manager
from muban_cli.api import MubanAPIClient

logger = logging.getLogger(__name__)


class PackageWorker(QThread):
    """Worker thread for packaging operations."""

    finished = pyqtSignal(object)  # PackageResult
    error = pyqtSignal(str)
    log = pyqtSignal(str)

    def __init__(
        self,
        template_path: Path,
        output_path: Optional[Path],
        fonts: List[FontSpec],
        reports_dir_param: str,
        dry_run: bool = False,
        fonts_xml_path: Optional[Path] = None,
    ):
        super().__init__()
        self.template_path = template_path
        self.output_path = output_path
        self.fonts = fonts
        self.reports_dir_param = reports_dir_param
        self.dry_run = dry_run
        self.fonts_xml_path = fonts_xml_path

    def run(self):
        try:
            packager = JRXMLPackager(reports_dir_param=self.reports_dir_param)
            result = packager.package(
                self.template_path,
                self.output_path,
                dry_run=self.dry_run,
                fonts=self.fonts,
                fonts_xml_path=self.fonts_xml_path,
            )
            self.finished.emit(result)
        except Exception as e:
            logger.exception("Packaging failed")
            self.error.emit(str(e))


class UploadWorker(QThread):
    """Worker thread for auto-upload after packaging."""

    finished = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, client: MubanAPIClient, file_path: Path, name: str, author: str):
        super().__init__()
        self.client = client
        self.file_path = file_path
        self.name = name
        self.author = author

    def run(self):
        try:
            result = self.client.upload_template(
                self.file_path,
                name=self.name,
                author=self.author,
            )
            self.finished.emit(result)
        except Exception as e:
            logger.exception("Failed to upload template")
            self.error.emit(str(e))


class PackageTab(QWidget):
    """Tab for packaging JRXML/DOCX templates."""

    def __init__(self):
        super().__init__()
        self._fonts: List[FontSpec] = []
        self._last_package_result: Optional[PackageResult] = None
        self._upload_worker: Optional[UploadWorker] = None
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        # Main splitter
        splitter = QSplitter(Qt.Orientation.Vertical)

        # Top section - inputs
        top_widget = QWidget()
        top_layout = QVBoxLayout(top_widget)
        top_layout.setContentsMargins(0, 0, 0, 0)

        # File selection group
        file_group = QGroupBox("Template File")
        file_layout = QFormLayout(file_group)

        # Template file (JRXML or DOCX)
        template_layout = QHBoxLayout()
        self.template_input = QLineEdit()
        self.template_input.setPlaceholderText("Select a template file (.jrxml or .docx)...")
        self.template_browse_btn = QPushButton("Browse...")
        self.template_browse_btn.clicked.connect(self._browse_template)
        template_layout.addWidget(self.template_input)
        template_layout.addWidget(self.template_browse_btn)
        file_layout.addRow("Template File:", template_layout)

        # Output file
        output_layout = QHBoxLayout()
        self.output_input = QLineEdit()
        self.output_input.setPlaceholderText("Output ZIP file (optional, auto-generated)")
        self.output_browse_btn = QPushButton("Browse...")
        self.output_browse_btn.clicked.connect(self._browse_output)
        output_layout.addWidget(self.output_input)
        output_layout.addWidget(self.output_browse_btn)
        file_layout.addRow("Output:", output_layout)

        # Reports dir param
        self.reports_dir_input = QLineEdit("REPORTS_DIR")
        self.reports_dir_input.setToolTip("Path parameter name used in JRXML templates (ignored for DOCX)")
        file_layout.addRow("Reports Dir Param:", self.reports_dir_input)

        top_layout.addWidget(file_group)

        # Fonts group
        fonts_group = QGroupBox("Custom Fonts (Optional)")
        fonts_layout = QVBoxLayout(fonts_group)

        # Existing fonts.xml option
        fonts_xml_layout = QHBoxLayout()
        fonts_xml_layout.addWidget(QLabel("Existing fonts.xml:"))
        self.fonts_xml_input = QLineEdit()
        self.fonts_xml_input.setPlaceholderText("Or use an existing fonts.xml file...")
        fonts_xml_layout.addWidget(self.fonts_xml_input)
        self.fonts_xml_browse_btn = QPushButton("Browse...")
        self.fonts_xml_browse_btn.clicked.connect(self._browse_fonts_xml)
        fonts_xml_layout.addWidget(self.fonts_xml_browse_btn)
        self.fonts_xml_clear_btn = QPushButton("Clear")
        self.fonts_xml_clear_btn.clicked.connect(self._clear_fonts_xml)
        fonts_xml_layout.addWidget(self.fonts_xml_clear_btn)
        self.fonts_xml_input.textChanged.connect(self._on_fonts_xml_changed)
        fonts_layout.addLayout(fonts_xml_layout)

        # Separator label
        or_label = QLabel("— OR add individual font files below —")
        or_label.setStyleSheet("color: gray; font-style: italic;")
        or_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        fonts_layout.addWidget(or_label)

        # Font table
        self.fonts_table = QTableWidget(0, 4)
        self.fonts_table.setHorizontalHeaderLabels(["File", "Name", "Face", "Embedded"])
        header = self.fonts_table.horizontalHeader()
        if header:
            header.setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
            header.setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive)
            header.setSectionResizeMode(2, QHeaderView.ResizeMode.Interactive)
            header.setSectionResizeMode(3, QHeaderView.ResizeMode.Interactive)
        self.fonts_table.setColumnWidth(0, 200)
        self.fonts_table.setColumnWidth(1, 150)
        self.fonts_table.setColumnWidth(2, 100)
        self.fonts_table.setColumnWidth(3, 80)
        self.fonts_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        fonts_layout.addWidget(self.fonts_table)

        # Font buttons
        font_btn_layout = QHBoxLayout()
        self.add_font_btn = QPushButton("Add Font...")
        self.add_font_btn.clicked.connect(self._add_font)
        self.remove_font_btn = QPushButton("Remove")
        self.remove_font_btn.clicked.connect(self._remove_font)
        font_btn_layout.addWidget(self.add_font_btn)
        font_btn_layout.addWidget(self.remove_font_btn)
        font_btn_layout.addStretch()
        fonts_layout.addLayout(font_btn_layout)

        top_layout.addWidget(fonts_group)

        # Action buttons
        action_layout = QHBoxLayout()
        self.dry_run_cb = QCheckBox("Dry run (analyze only)")
        action_layout.addWidget(self.dry_run_cb)
        action_layout.addStretch()

        self.package_btn = QPushButton("Package Template")
        self.package_btn.setMinimumWidth(150)
        self.package_btn.clicked.connect(self._run_package)
        style = self.style()
        if style:
            self.package_btn.setIcon(style.standardIcon(QStyle.StandardPixmap.SP_FileDialogNewFolder))
        action_layout.addWidget(self.package_btn)

        top_layout.addLayout(action_layout)

        # Progress bar
        self.progress = QProgressBar()
        self.progress.setVisible(False)
        top_layout.addWidget(self.progress)

        splitter.addWidget(top_widget)

        # Bottom section - output log
        log_group = QGroupBox("Output")
        log_layout = QVBoxLayout(log_group)
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setMinimumHeight(150)
        log_layout.addWidget(self.log_output)
        splitter.addWidget(log_group)

        # Set splitter sizes
        splitter.setSizes([400, 200])

        layout.addWidget(splitter)

    def _browse_template(self):
        """Browse for template file (JRXML or DOCX)."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Template File",
            "",
            "Template Files (*.jrxml *.docx);;JRXML Files (*.jrxml);;DOCX Files (*.docx);;All Files (*)",
        )
        if file_path:
            self.template_input.setText(file_path)
            # Auto-set output path
            if not self.output_input.text():
                output = Path(file_path).with_suffix(".zip")
                self.output_input.setText(str(output))

    def _browse_output(self):
        """Browse for output ZIP file."""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Package As",
            self.output_input.text() or "",
            "ZIP Files (*.zip);;All Files (*)",
        )
        if file_path:
            self.output_input.setText(file_path)

    def _add_font(self):
        """Add a font to the list."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Font File",
            "",
            "Font Files (*.ttf *.otf *.TTF *.OTF);;All Files (*)",
        )
        if not file_path:
            return

        # Show font dialog (supports multi-face selection)
        from muban_cli.gui.dialogs.font_dialog import FontDialog

        dialog = FontDialog(file_path, self)
        if dialog.exec():
            font_specs = dialog.get_font_specs()
            # Deduplicate: skip (name, face) pairs already in the list
            existing = {(f.name, f.face) for f in self._fonts}
            new_specs = [s for s in font_specs if (s.name, s.face) not in existing]
            skipped = len(font_specs) - len(new_specs)
            if skipped:
                faces = ", ".join(
                    s.face for s in font_specs if (s.name, s.face) in existing
                )
                QMessageBox.information(
                    self,
                    "Duplicates Skipped",
                    f"Skipped {skipped} already registered face(s): {faces}",
                )
            if new_specs:
                self._fonts.extend(new_specs)
                self._refresh_fonts_table()

    def _browse_fonts_xml(self):
        """Browse for existing fonts.xml file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select fonts.xml File",
            "",
            "XML Files (*.xml);;All Files (*)",
        )
        if file_path:
            self.fonts_xml_input.setText(file_path)

    def _clear_fonts_xml(self):
        """Clear the fonts.xml path."""
        self.fonts_xml_input.clear()

    def _on_fonts_xml_changed(self, text: str):
        """Enable/disable manual font controls based on fonts.xml input."""
        has_fonts_xml = bool(text.strip())
        self.fonts_table.setEnabled(not has_fonts_xml)
        self.add_font_btn.setEnabled(not has_fonts_xml)
        self.remove_font_btn.setEnabled(not has_fonts_xml)

    def _remove_font(self):
        """Remove selected font."""
        rows = set(item.row() for item in self.fonts_table.selectedItems())
        if not rows:
            return
        # Remove in reverse order to preserve indices
        for row in sorted(rows, reverse=True):
            del self._fonts[row]
        self._refresh_fonts_table()

    def _refresh_fonts_table(self):
        """Refresh the fonts table."""
        from PyQt6.QtCore import Qt
        self.fonts_table.setRowCount(len(self._fonts))
        for i, font in enumerate(self._fonts):
            items = [
                QTableWidgetItem(font.file_path.name),
                QTableWidgetItem(font.name),
                QTableWidgetItem(font.face),
                QTableWidgetItem("Yes" if font.embedded else "No"),
            ]
            for col, item in enumerate(items):
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.fonts_table.setItem(i, col, item)

    def _run_package(self):
        """Run the packaging operation."""
        template_path = self.template_input.text().strip()
        if not template_path:
            QMessageBox.warning(self, "Error", "Please select a template file (.jrxml or .docx).")
            return

        template_path = Path(template_path)
        if not template_path.exists():
            QMessageBox.warning(self, "Error", f"File not found: {template_path}")
            return

        output_path = self.output_input.text().strip()
        output_path = Path(output_path) if output_path else None

        dry_run = self.dry_run_cb.isChecked()
        
        # Get fonts.xml path if specified
        fonts_xml_text = self.fonts_xml_input.text().strip()
        fonts_xml_path = Path(fonts_xml_text) if fonts_xml_text else None
        if fonts_xml_path and not fonts_xml_path.exists():
            QMessageBox.warning(self, "Error", f"fonts.xml not found: {fonts_xml_path}")
            return

        # Disable UI during operation
        self._set_ui_enabled(False)
        self.progress.setVisible(True)
        self.progress.setRange(0, 0)  # Indeterminate
        self.log_output.clear()
        self._log("Starting packaging...")

        # Run in worker thread
        self.worker = PackageWorker(
            template_path,
            output_path,
            self._fonts.copy(),
            self.reports_dir_input.text(),
            dry_run,
            fonts_xml_path,
        )
        self.worker.finished.connect(self._on_package_finished)
        self.worker.error.connect(self._on_package_error)
        self.worker.start()

    def _on_package_finished(self, result: PackageResult):
        """Handle successful packaging."""
        try:
            self._last_package_result = result
            
            if result.success:
                is_dry_run = self.dry_run_cb.isChecked()
                if is_dry_run:
                    self._log(f"\n✓ Dry run complete. Would create: {result.output_path}")
                else:
                    self._log(f"\n✓ Package created: {result.output_path}")
                self._log(f"  Main template: {result.main_template} ({result.template_type})")
                self._log(f"  Assets: {len(result.assets_included)} included, {len(result.assets_missing)} missing")
                if result.fonts_included:
                    unique_font_files = len({f.file_path for f in result.fonts_included})
                    self._log(f"  Fonts: {unique_font_files} file(s)")
                elif result.fonts_xml_files:
                    self._log(f"  Fonts: {len(result.fonts_xml_files)} file(s) from fonts.xml")
                if not is_dry_run and result.output_path and result.output_path.exists():
                    size_kb = result.output_path.stat().st_size / 1024
                    self._log(f"  Size: {size_kb:.1f} KB")

                if len(result.assets_missing) > 0:
                    self._log("\n⚠ Missing assets:")
                    for asset in result.assets_missing:
                        self._log(f"  - {asset}")
                
                # Auto-upload if enabled and not dry run
                if not is_dry_run and result.output_path:
                    self._try_auto_upload(result.output_path)
                else:
                    self._set_ui_enabled(True)
                    self.progress.setVisible(False)
            else:
                self._set_ui_enabled(True)
                self.progress.setVisible(False)
                self._log(f"\n✗ Packaging failed")
                for error in result.errors:
                    self._log(f"  Error: {error}")
        except Exception as e:
            self._set_ui_enabled(True)
            self.progress.setVisible(False)
            logger.exception("Error displaying packaging results")
            self._log(f"\n✗ Error displaying results: {e}")

    def _on_package_error(self, error: str):
        """Handle packaging error."""
        self._set_ui_enabled(True)
        self.progress.setVisible(False)
        self._log(f"\n✗ Error: {error}")
        QMessageBox.critical(self, "Packaging Error", error)

    def _try_auto_upload(self, output_path: Path):
        """Attempt auto-upload if enabled in config."""
        try:
            config = get_config_manager().load()
            
            if not config.auto_upload_on_package:
                self._set_ui_enabled(True)
                self.progress.setVisible(False)
                return
            
            if not config.is_authenticated():
                self._log("\n⚠ Auto-upload skipped: Not authenticated")
                self._set_ui_enabled(True)
                self.progress.setVisible(False)
                return
            
            if not config.default_author:
                self._log("\n⚠ Auto-upload skipped: Default author not set in settings")
                self._set_ui_enabled(True)
                self.progress.setVisible(False)
                return
            
            # Use filename stem as template name
            template_name = output_path.stem
            
            self._log(f"\n📤 Auto-uploading to server...")
            self._log(f"  Name: {template_name}")
            self._log(f"  Author: {config.default_author}")
            
            client = MubanAPIClient(config)
            self._upload_worker = UploadWorker(
                client,
                output_path,
                template_name,
                config.default_author,
            )
            self._upload_worker.finished.connect(self._on_upload_finished)
            self._upload_worker.error.connect(self._on_upload_error)
            self._upload_worker.start()
            
        except Exception as e:
            logger.exception("Error during auto-upload setup")
            self._log(f"\n✗ Auto-upload error: {e}")
            self._set_ui_enabled(True)
            self.progress.setVisible(False)

    def _on_upload_finished(self, result: dict):
        """Handle successful upload."""
        self._set_ui_enabled(True)
        self.progress.setVisible(False)
        
        template = result.get('data', {})
        self._log(f"\n✓ Template uploaded successfully!")
        self._log(f"  ID: {template.get('id')}")
        self._log(f"  Name: {template.get('name')}")

    def _on_upload_error(self, error: str):
        """Handle upload error."""
        self._set_ui_enabled(True)
        self.progress.setVisible(False)
        self._log(f"\n✗ Auto-upload failed: {error}")

    def _set_ui_enabled(self, enabled: bool):
        """Enable/disable UI elements."""
        self.template_input.setEnabled(enabled)
        self.template_browse_btn.setEnabled(enabled)
        self.output_input.setEnabled(enabled)
        self.output_browse_btn.setEnabled(enabled)
        self.reports_dir_input.setEnabled(enabled)
        self.fonts_xml_input.setEnabled(enabled)
        self.fonts_xml_browse_btn.setEnabled(enabled)
        self.fonts_xml_clear_btn.setEnabled(enabled)
        # Font controls respect fonts.xml state when re-enabling
        has_fonts_xml = bool(self.fonts_xml_input.text().strip())
        self.fonts_table.setEnabled(enabled and not has_fonts_xml)
        self.add_font_btn.setEnabled(enabled and not has_fonts_xml)
        self.remove_font_btn.setEnabled(enabled and not has_fonts_xml)
        self.dry_run_cb.setEnabled(enabled)
        self.package_btn.setEnabled(enabled)

    def _log(self, message: str):
        """Add message to log output."""
        self.log_output.append(message)
