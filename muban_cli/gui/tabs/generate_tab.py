"""
Generate Tab - Generate documents from templates.
"""

import json
from pathlib import Path
from typing import Optional, Dict, Any, List

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
    QComboBox,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QMessageBox,
    QProgressBar,
    QFileDialog,
    QTextEdit,
    QSplitter,
)

from muban_cli.api import MubanAPIClient
from muban_cli.config import get_config_manager


class GenerateWorker(QThread):
    """Worker thread for document generation."""

    finished = pyqtSignal(str)  # output path
    error = pyqtSignal(str)

    def __init__(
        self,
        client: MubanAPIClient,
        template_id: str,
        output_path: str,
        output_format: str,
        parameters: Dict[str, Any],
    ):
        super().__init__()
        self.client = client
        self.template_id = template_id
        self.output_path = Path(output_path)
        self.output_format = output_format
        self.parameters = parameters

    def run(self):
        try:
            # Convert dict params to list format expected by API
            params_list = [{"name": k, "value": v} for k, v in self.parameters.items()]
            self.client.generate_document(
                template_id=self.template_id,
                output_format=self.output_format,
                parameters=params_list,
                output_path=self.output_path,
            )
            self.finished.emit(str(self.output_path))
        except Exception as e:
            self.error.emit(str(e))


class ParametersWorker(QThread):
    """Worker thread for loading template parameters."""

    finished = pyqtSignal(list)
    error = pyqtSignal(str)

    def __init__(self, client: MubanAPIClient, template_id: str):
        super().__init__()
        self.client = client
        self.template_id = template_id

    def run(self):
        try:
            result = self.client.get_template_parameters(self.template_id)
            params = result.get("content", result) if isinstance(result, dict) else result
            self.finished.emit(params if isinstance(params, list) else [])
        except Exception as e:
            self.error.emit(str(e))


class GenerateTab(QWidget):
    """Tab for generating documents."""

    def __init__(self):
        super().__init__()
        self._parameters: List[Dict[str, Any]] = []
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        # Main splitter
        splitter = QSplitter(Qt.Orientation.Vertical)

        # Top section - inputs
        top_widget = QWidget()
        top_layout = QVBoxLayout(top_widget)
        top_layout.setContentsMargins(0, 0, 0, 0)

        # Template selection
        template_group = QGroupBox("Template")
        template_layout = QFormLayout(template_group)

        template_id_layout = QHBoxLayout()
        self.template_id_input = QLineEdit()
        self.template_id_input.setPlaceholderText("Enter template ID or select from Templates tab")
        self.load_params_btn = QPushButton("Load Parameters")
        self.load_params_btn.clicked.connect(self._load_parameters)
        template_id_layout.addWidget(self.template_id_input)
        template_id_layout.addWidget(self.load_params_btn)
        template_layout.addRow("Template ID:", template_id_layout)

        top_layout.addWidget(template_group)

        # Parameters
        params_group = QGroupBox("Parameters")
        params_layout = QVBoxLayout(params_group)

        self.params_table = QTableWidget(0, 3)
        self.params_table.setHorizontalHeaderLabels(["Name", "Type", "Value"])
        header = self.params_table.horizontalHeader()
        if header:
            header.setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
            header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.params_table.setColumnWidth(0, 200)
        self.params_table.setColumnWidth(1, 100)
        params_layout.addWidget(self.params_table)

        # Manual parameter entry
        manual_layout = QHBoxLayout()
        self.param_name_input = QLineEdit()
        self.param_name_input.setPlaceholderText("Parameter name")
        self.param_value_input = QLineEdit()
        self.param_value_input.setPlaceholderText("Value")
        self.add_param_btn = QPushButton("Add")
        self.add_param_btn.clicked.connect(self._add_manual_param)
        manual_layout.addWidget(self.param_name_input)
        manual_layout.addWidget(self.param_value_input)
        manual_layout.addWidget(self.add_param_btn)
        params_layout.addLayout(manual_layout)

        # Load from file
        file_layout = QHBoxLayout()
        self.load_params_file_btn = QPushButton("Load from JSON...")
        self.load_params_file_btn.clicked.connect(self._load_params_from_file)
        file_layout.addWidget(self.load_params_file_btn)
        file_layout.addStretch()
        params_layout.addLayout(file_layout)

        top_layout.addWidget(params_group)

        # Output options
        output_group = QGroupBox("Output Options")
        output_layout = QFormLayout(output_group)

        # Format
        self.format_combo = QComboBox()
        self.format_combo.addItems(["pdf", "xlsx", "docx", "rtf", "html"])
        self.format_combo.currentTextChanged.connect(self._on_format_changed)
        output_layout.addRow("Format:", self.format_combo)

        # Output file
        output_file_layout = QHBoxLayout()
        self.output_input = QLineEdit()
        self.output_input.setPlaceholderText("Output file path")
        self.output_browse_btn = QPushButton("Browse...")
        self.output_browse_btn.clicked.connect(self._browse_output)
        output_file_layout.addWidget(self.output_input)
        output_file_layout.addWidget(self.output_browse_btn)
        output_layout.addRow("Output:", output_file_layout)

        top_layout.addWidget(output_group)

        # Generate button
        action_layout = QHBoxLayout()
        action_layout.addStretch()
        self.generate_btn = QPushButton("⚙️ Generate Document")
        self.generate_btn.setMinimumWidth(150)
        self.generate_btn.clicked.connect(self._generate)
        action_layout.addWidget(self.generate_btn)
        top_layout.addLayout(action_layout)

        # Progress
        self.progress = QProgressBar()
        self.progress.setVisible(False)
        top_layout.addWidget(self.progress)

        splitter.addWidget(top_widget)

        # Status/log area
        log_group = QGroupBox("Status")
        log_layout = QVBoxLayout(log_group)
        self.status_output = QTextEdit()
        self.status_output.setReadOnly(True)
        self.status_output.setMaximumHeight(100)
        log_layout.addWidget(self.status_output)
        splitter.addWidget(log_group)

        splitter.setSizes([500, 100])
        layout.addWidget(splitter)

    def set_template(self, template_id: str):
        """Set the template ID (called from templates tab)."""
        self.template_id_input.setText(template_id)
        self._load_parameters()

    def _get_client(self) -> Optional[MubanAPIClient]:
        """Get configured API client."""
        try:
            config = get_config_manager().load()
            if not config.server_url:
                self._log("⚠️ Server not configured - go to Settings tab")
                return None
            return MubanAPIClient(config)
        except Exception as e:
            self._log(f"⚠️ Error: {e}")
            return None

    def _load_parameters(self):
        """Load parameters for the template."""
        template_id = self.template_id_input.text().strip()
        if not template_id:
            QMessageBox.warning(self, "Error", "Please enter a template ID.")
            return

        client = self._get_client()
        if not client:
            return

        self._set_ui_enabled(False)
        self.progress.setVisible(True)
        self.progress.setRange(0, 0)
        self._log(f"Loading parameters for {template_id}...")

        self.params_worker = ParametersWorker(client, template_id)
        self.params_worker.finished.connect(self._on_parameters_loaded)
        self.params_worker.error.connect(self._on_parameters_error)
        self.params_worker.start()

    def _on_parameters_loaded(self, parameters: list):
        """Handle loaded parameters."""
        self._set_ui_enabled(True)
        self.progress.setVisible(False)

        self._parameters = parameters
        self.params_table.setRowCount(len(parameters))

        for i, p in enumerate(parameters):
            name = p.get("name", "")
            ptype = p.get("type", p.get("valueClassName", "String"))
            default = p.get("defaultValue", "")

            name_item = QTableWidgetItem(name)
            name_item.setFlags(name_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.params_table.setItem(i, 0, name_item)

            type_item = QTableWidgetItem(str(ptype).split(".")[-1])
            type_item.setFlags(type_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.params_table.setItem(i, 1, type_item)

            self.params_table.setItem(i, 2, QTableWidgetItem(str(default) if default else ""))

        self._log(f"✓ Loaded {len(parameters)} parameters")

    def _on_parameters_error(self, error: str):
        """Handle parameter load error."""
        self._set_ui_enabled(True)
        self.progress.setVisible(False)
        self._log(f"⚠️ Error loading parameters: {error}")

    def _add_manual_param(self):
        """Add a manual parameter."""
        name = self.param_name_input.text().strip()
        value = self.param_value_input.text()
        if not name:
            return

        row = self.params_table.rowCount()
        self.params_table.insertRow(row)

        name_item = QTableWidgetItem(name)
        self.params_table.setItem(row, 0, name_item)
        self.params_table.setItem(row, 1, QTableWidgetItem("String"))
        self.params_table.setItem(row, 2, QTableWidgetItem(value))

        self.param_name_input.clear()
        self.param_value_input.clear()

    def _load_params_from_file(self):
        """Load parameters from JSON file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Load Parameters",
            "",
            "JSON Files (*.json);;All Files (*)",
        )
        if not file_path:
            return

        try:
            with open(file_path) as f:
                data = json.load(f)

            # Handle both dict and list formats
            if isinstance(data, dict):
                params = data
            elif isinstance(data, list):
                params = {p.get("name"): p.get("value") for p in data if "name" in p}
            else:
                raise ValueError("Invalid JSON format")

            # Apply to table
            for row in range(self.params_table.rowCount()):
                name_item = self.params_table.item(row, 0)
                if name_item and name_item.text() in params:
                    self.params_table.setItem(row, 2, QTableWidgetItem(str(params[name_item.text()])))

            self._log(f"✓ Loaded parameters from {Path(file_path).name}")
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to load parameters: {e}")

    def _on_format_changed(self, format: str):
        """Update output path extension when format changes."""
        current = self.output_input.text()
        if current:
            path = Path(current)
            self.output_input.setText(str(path.with_suffix(f".{format}")))

    def _browse_output(self):
        """Browse for output file."""
        format = self.format_combo.currentText()
        filter_map = {
            "pdf": "PDF Files (*.pdf)",
            "xlsx": "Excel Files (*.xlsx)",
            "docx": "Word Files (*.docx)",
            "rtf": "RTF Files (*.rtf)",
            "html": "HTML Files (*.html)",
        }

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Document As",
            self.output_input.text() or f"document.{format}",
            f"{filter_map.get(format, 'All Files (*)')};;All Files (*)",
        )
        if file_path:
            self.output_input.setText(file_path)

    def _get_parameters(self) -> Dict[str, Any]:
        """Get parameters from table."""
        params = {}
        for row in range(self.params_table.rowCount()):
            name_item = self.params_table.item(row, 0)
            value_item = self.params_table.item(row, 2)
            if name_item and value_item:
                name = name_item.text()
                value = value_item.text()
                if value:  # Only include non-empty values
                    params[name] = value
        return params

    def _generate(self):
        """Generate the document."""
        template_id = self.template_id_input.text().strip()
        if not template_id:
            QMessageBox.warning(self, "Error", "Please enter a template ID.")
            return

        output_path = self.output_input.text().strip()
        if not output_path:
            QMessageBox.warning(self, "Error", "Please specify an output file.")
            return

        client = self._get_client()
        if not client:
            return

        self._set_ui_enabled(False)
        self.progress.setVisible(True)
        self.progress.setRange(0, 0)
        self._log(f"Generating {self.format_combo.currentText().upper()}...")

        self.generate_worker = GenerateWorker(
            client,
            template_id,
            output_path,
            self.format_combo.currentText(),
            self._get_parameters(),
        )
        self.generate_worker.finished.connect(self._on_generate_finished)
        self.generate_worker.error.connect(self._on_generate_error)
        self.generate_worker.start()

    def _on_generate_finished(self, output_path: str):
        """Handle successful generation."""
        self._set_ui_enabled(True)
        self.progress.setVisible(False)
        self._log(f"✓ Document saved to: {output_path}")
        QMessageBox.information(
            self,
            "Generation Complete",
            f"Document generated successfully!\n\n{output_path}",
        )

    def _on_generate_error(self, error: str):
        """Handle generation error."""
        self._set_ui_enabled(True)
        self.progress.setVisible(False)
        self._log(f"✗ Error: {error}")
        QMessageBox.critical(self, "Generation Error", error)

    def _set_ui_enabled(self, enabled: bool):
        """Enable/disable UI elements."""
        self.template_id_input.setEnabled(enabled)
        self.load_params_btn.setEnabled(enabled)
        self.params_table.setEnabled(enabled)
        self.param_name_input.setEnabled(enabled)
        self.param_value_input.setEnabled(enabled)
        self.add_param_btn.setEnabled(enabled)
        self.load_params_file_btn.setEnabled(enabled)
        self.format_combo.setEnabled(enabled)
        self.output_input.setEnabled(enabled)
        self.output_browse_btn.setEnabled(enabled)
        self.generate_btn.setEnabled(enabled)

    def _log(self, message: str):
        """Add message to status output."""
        self.status_output.append(message)
