"""
Package Tab - JRXML template packaging with dependencies.
"""

from pathlib import Path
from typing import List, Optional

from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
    QGroupBox,
    QLabel,
    QLineEdit,
    QPushButton,
    QFileDialog,
    QTextEdit,
    QCheckBox,
    QComboBox,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QMessageBox,
    QProgressBar,
    QSplitter,
)

from muban_cli.packager import JRXMLPackager, PackageResult, FontSpec


class PackageWorker(QThread):
    """Worker thread for packaging operations."""

    finished = pyqtSignal(object)  # PackageResult
    error = pyqtSignal(str)
    log = pyqtSignal(str)

    def __init__(
        self,
        jrxml_path: Path,
        output_path: Optional[Path],
        fonts: List[FontSpec],
        reports_dir_param: str,
        dry_run: bool = False,
    ):
        super().__init__()
        self.jrxml_path = jrxml_path
        self.output_path = output_path
        self.fonts = fonts
        self.reports_dir_param = reports_dir_param
        self.dry_run = dry_run

    def run(self):
        try:
            packager = JRXMLPackager(reports_dir_param=self.reports_dir_param)
            result = packager.package(
                self.jrxml_path,
                self.output_path,
                dry_run=self.dry_run,
                fonts=self.fonts,
            )
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))


class PackageTab(QWidget):
    """Tab for packaging JRXML templates."""

    def __init__(self):
        super().__init__()
        self._fonts: List[FontSpec] = []
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

        # JRXML file
        jrxml_layout = QHBoxLayout()
        self.jrxml_input = QLineEdit()
        self.jrxml_input.setPlaceholderText("Select a JRXML template file...")
        self.jrxml_browse_btn = QPushButton("Browse...")
        self.jrxml_browse_btn.clicked.connect(self._browse_jrxml)
        jrxml_layout.addWidget(self.jrxml_input)
        jrxml_layout.addWidget(self.jrxml_browse_btn)
        file_layout.addRow("JRXML File:", jrxml_layout)

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
        file_layout.addRow("Reports Dir Param:", self.reports_dir_input)

        top_layout.addWidget(file_group)

        # Fonts group
        fonts_group = QGroupBox("Custom Fonts (Optional)")
        fonts_layout = QVBoxLayout(fonts_group)

        # Font table
        self.fonts_table = QTableWidget(0, 4)
        self.fonts_table.setHorizontalHeaderLabels(["File", "Name", "Face", "Embedded"])
        header = self.fonts_table.horizontalHeader()
        if header:
            header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
            header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
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

        self.package_btn = QPushButton("📦 Package Template")
        self.package_btn.setMinimumWidth(150)
        self.package_btn.clicked.connect(self._run_package)
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

    def _browse_jrxml(self):
        """Browse for JRXML file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select JRXML Template",
            "",
            "JRXML Files (*.jrxml);;All Files (*)",
        )
        if file_path:
            self.jrxml_input.setText(file_path)
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

        # Show font dialog
        from muban_cli.gui.dialogs.font_dialog import FontDialog

        dialog = FontDialog(file_path, self)
        if dialog.exec():
            font_spec = dialog.get_font_spec()
            self._fonts.append(font_spec)
            self._refresh_fonts_table()

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
        self.fonts_table.setRowCount(len(self._fonts))
        for i, font in enumerate(self._fonts):
            self.fonts_table.setItem(i, 0, QTableWidgetItem(font.file_path.name))
            self.fonts_table.setItem(i, 1, QTableWidgetItem(font.name))
            self.fonts_table.setItem(i, 2, QTableWidgetItem(font.face))
            self.fonts_table.setItem(i, 3, QTableWidgetItem("Yes" if font.embedded else "No"))

    def _run_package(self):
        """Run the packaging operation."""
        jrxml_path = self.jrxml_input.text().strip()
        if not jrxml_path:
            QMessageBox.warning(self, "Error", "Please select a JRXML file.")
            return

        jrxml_path = Path(jrxml_path)
        if not jrxml_path.exists():
            QMessageBox.warning(self, "Error", f"File not found: {jrxml_path}")
            return

        output_path = self.output_input.text().strip()
        output_path = Path(output_path) if output_path else None

        dry_run = self.dry_run_cb.isChecked()

        # Disable UI during operation
        self._set_ui_enabled(False)
        self.progress.setVisible(True)
        self.progress.setRange(0, 0)  # Indeterminate
        self.log_output.clear()
        self._log("Starting packaging...")

        # Run in worker thread
        self.worker = PackageWorker(
            jrxml_path,
            output_path,
            self._fonts.copy(),
            self.reports_dir_input.text(),
            dry_run,
        )
        self.worker.finished.connect(self._on_package_finished)
        self.worker.error.connect(self._on_package_error)
        self.worker.start()

    def _on_package_finished(self, result: PackageResult):
        """Handle successful packaging."""
        self._set_ui_enabled(True)
        self.progress.setVisible(False)

        if result.success:
            self._log(f"\n✓ Package created: {result.output_path}")
            self._log(f"  Main template: {result.main_jrxml}")
            self._log(f"  Assets: {len(result.assets_included)} included, {len(result.assets_missing)} missing")
            if result.fonts_included:
                self._log(f"  Fonts: {len(result.fonts_included)} file(s)")
            if result.output_path:
                size_kb = result.output_path.stat().st_size / 1024
                self._log(f"  Size: {size_kb:.1f} KB")

            if len(result.assets_missing) > 0:
                self._log("\n⚠ Missing assets:")
                for asset in result.assets_missing:
                    self._log(f"  - {asset}")
        else:
            self._log(f"\n✗ Packaging failed")
            for error in result.errors:
                self._log(f"  Error: {error}")

    def _on_package_error(self, error: str):
        """Handle packaging error."""
        self._set_ui_enabled(True)
        self.progress.setVisible(False)
        self._log(f"\n✗ Error: {error}")
        QMessageBox.critical(self, "Packaging Error", error)

    def _set_ui_enabled(self, enabled: bool):
        """Enable/disable UI elements."""
        self.jrxml_input.setEnabled(enabled)
        self.jrxml_browse_btn.setEnabled(enabled)
        self.output_input.setEnabled(enabled)
        self.output_browse_btn.setEnabled(enabled)
        self.reports_dir_input.setEnabled(enabled)
        self.fonts_table.setEnabled(enabled)
        self.add_font_btn.setEnabled(enabled)
        self.remove_font_btn.setEnabled(enabled)
        self.dry_run_cb.setEnabled(enabled)
        self.package_btn.setEnabled(enabled)

    def _log(self, message: str):
        """Add message to log output."""
        self.log_output.append(message)
