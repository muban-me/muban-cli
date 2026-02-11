"""
Generate Tab - Generate documents from templates.
"""

import json
import logging
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
    QSizePolicy,
)

from muban_cli.api import MubanAPIClient
from muban_cli.config import get_config_manager

logger = logging.getLogger(__name__)


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
        data: Optional[Dict[str, Any]] = None,
        pdf_export_options: Optional[Dict[str, Any]] = None,
        html_export_options: Optional[Dict[str, Any]] = None,
    ):
        super().__init__()
        self.client = client
        self.template_id = template_id
        self.output_path = Path(output_path)
        self.output_format = output_format
        self.parameters = parameters
        self.data = data
        self.pdf_export_options = pdf_export_options
        self.html_export_options = html_export_options

    def run(self):
        try:
            # Convert dict params to list format expected by API
            params_list = [{"name": k, "value": v} for k, v in self.parameters.items()]
            self.client.generate_document(
                template_id=self.template_id,
                output_format=self.output_format,
                parameters=params_list,
                output_path=self.output_path,
                data=self.data,
                pdf_export_options=self.pdf_export_options,
                html_export_options=self.html_export_options,
            )
            self.finished.emit(str(self.output_path))
        except Exception as e:
            logger.exception("Document generation failed")
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
            # Handle different response structures
            # New format: {'meta': ..., 'data': [...], 'errors': []}
            # Old format: {'content': [...]}
            if isinstance(result, dict):
                if "data" in result and isinstance(result["data"], list):
                    params = result["data"]
                elif "content" in result:
                    params = result["content"]
                else:
                    params = result
            else:
                params = result
            self.finished.emit(params if isinstance(params, list) else [])
        except Exception as e:
            logger.exception("Failed to load template parameters")
            self.error.emit(str(e))


class FieldsWorker(QThread):
    """Worker thread for loading template fields."""

    finished = pyqtSignal(list)
    error = pyqtSignal(str)

    def __init__(self, client: MubanAPIClient, template_id: str):
        super().__init__()
        self.client = client
        self.template_id = template_id

    def run(self):
        try:
            result = self.client.get_template_fields(self.template_id)
            if isinstance(result, dict):
                if "data" in result and isinstance(result["data"], list):
                    fields = result["data"]
                elif "content" in result:
                    fields = result["content"]
                else:
                    fields = result
            else:
                fields = result
            self.finished.emit(fields if isinstance(fields, list) else [])
        except Exception as e:
            logger.exception("Failed to load template fields")
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


class GenerateTab(QWidget):
    """Tab for generating documents."""

    def __init__(self):
        super().__init__()
        self._parameters: List[Dict[str, Any]] = []
        self._fields: List[Dict[str, Any]] = []
        self._fields_data: Optional[Dict[str, Any]] = None
        self._icc_loaded = False
        self._icc_profiles: List[str] = []
        self._pdf_options: Dict[str, Any] = {}
        self._html_options: Dict[str, Any] = {}
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

        self.params_table = QTableWidget(0, 4)
        self.params_table.setHorizontalHeaderLabels(["Name", "Type", "Default (expression)", "Value"])
        header = self.params_table.horizontalHeader()
        if header:
            header.setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
            header.setSectionResizeMode(2, QHeaderView.ResizeMode.Interactive)
            header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.params_table.setColumnWidth(0, 200)
        self.params_table.setColumnWidth(1, 80)
        self.params_table.setColumnWidth(2, 200)
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
        self.load_request_btn = QPushButton("Load Request...")
        self.load_request_btn.setToolTip(
            'Load full request JSON (muban-cli compatible):\n'
            '{\n'
            '  "parameters": [{"name": "param", "value": "val"}, ...],\n'
            '  "data": {"field_name": [{...}, ...]}  // optional\n'
            '}\n\n'
            'Simple parameter formats also supported:\n'
            '{"param_name": "value", ...}'
        )
        self.load_request_btn.clicked.connect(self._load_request_from_file)
        file_layout.addWidget(self.load_request_btn)
        file_layout.addStretch()
        params_layout.addLayout(file_layout)

        top_layout.addWidget(params_group)

        # Fields (informational) and Data - hidden by default, shown only when template has fields
        self.fields_group = QGroupBox("Fields (data collections)")
        fields_layout = QVBoxLayout(self.fields_group)
        self.fields_group.setVisible(False)  # Hidden until fields are loaded

        # Fields table (shows template field definitions)
        fields_label = QLabel("Template field definitions:")
        fields_layout.addWidget(fields_label)
        
        self.fields_table = QTableWidget(0, 3)
        self.fields_table.setHorizontalHeaderLabels(["Name", "Type", "Description"])
        fields_header = self.fields_table.horizontalHeader()
        if fields_header:
            fields_header.setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
            fields_header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.fields_table.setColumnWidth(0, 200)
        self.fields_table.setColumnWidth(1, 80)
        self.fields_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        # Fixed height for fields table (shows ~3-4 rows of field definitions)
        self.fields_table.setFixedHeight(120)
        fields_layout.addWidget(self.fields_table)

        # Data editor (for field data) - hidden by default, shown when data is loaded
        self.data_label = QLabel("Data (JSON for collections - loaded from request):")
        self.data_label.setVisible(False)
        fields_layout.addWidget(self.data_label)
        
        self.data_editor = QTextEdit()
        self.data_editor.setPlaceholderText(
            'Data loaded from request JSON will appear here.\n'
            'Format: {"field_name": [{"col1": "val1", ...}, ...]}'
        )
        self.data_editor.setAcceptRichText(False)
        self.data_editor.setVisible(False)
        self.data_editor.setMinimumHeight(100)
        fields_layout.addWidget(self.data_editor)
        
        # Set size policy so the group shrinks when data editor is hidden
        self.fields_group.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)

        top_layout.addWidget(self.fields_group)

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

        # Export options button
        export_layout = QHBoxLayout()
        self.export_options_btn = QPushButton("⚙️ Export Options...")
        self.export_options_btn.setToolTip("Configure PDF/HTML export options")
        self.export_options_btn.clicked.connect(self._open_export_options_dialog)
        export_layout.addWidget(self.export_options_btn)
        self.export_summary_label = QLabel("Default settings")
        self.export_summary_label.setStyleSheet("color: gray; font-style: italic;")
        export_layout.addWidget(self.export_summary_label)
        export_layout.addStretch()
        top_layout.addLayout(export_layout)

        # Update export options visibility based on format
        self._update_export_options_visibility()

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

    def showEvent(self, event):
        """Called when the tab is shown."""
        super().showEvent(event)
        # Load ICC profiles on first show
        if not self._icc_loaded:
            self._load_icc_profiles()

    def set_template(self, template_id: str):
        """Set the template ID (called from templates tab)."""
        self.template_id_input.setText(template_id)
        self._load_parameters()

    def _load_icc_profiles(self):
        """Load available ICC profiles from server."""
        client = self._get_client()
        if not client:
            return

        self.icc_worker = ICCProfilesWorker(client)
        self.icc_worker.finished.connect(self._on_icc_loaded)
        self.icc_worker.error.connect(self._on_icc_error)
        self.icc_worker.start()

    def _on_icc_loaded(self, profiles: list):
        """Handle ICC profiles loaded."""
        self._icc_loaded = True
        # Store profiles for use in dialog
        self._icc_profiles = []
        for profile in profiles:
            if isinstance(profile, str):
                self._icc_profiles.append(profile)
            elif isinstance(profile, dict) and "name" in profile:
                self._icc_profiles.append(profile["name"])

    def _on_icc_error(self, error: str):
        """Handle ICC profiles loading error."""
        self._log(f"⚠️ Could not load ICC profiles: {error}")

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
        """Load parameters and fields for the template."""
        template_id = self.template_id_input.text().strip()
        if not template_id:
            QMessageBox.warning(self, "Error", "Please enter a template ID.")
            return

        client = self._get_client()
        if not client:
            return

        # Clear previous data
        self._fields_data = None
        self.data_editor.clear()
        self.data_editor.setVisible(False)
        self.data_label.setVisible(False)
        self.fields_group.updateGeometry()

        self._set_ui_enabled(False)
        self.progress.setVisible(True)
        self.progress.setRange(0, 0)
        self._log(f"Loading parameters and fields for {template_id}...")

        # Load parameters
        self.params_worker = ParametersWorker(client, template_id)
        self.params_worker.finished.connect(self._on_parameters_loaded)
        self.params_worker.error.connect(self._on_parameters_error)
        self.params_worker.start()

        # Load fields
        client2 = self._get_client()  # Need separate client for parallel request
        if client2:
            self.fields_worker = FieldsWorker(client2, template_id)
            self.fields_worker.finished.connect(self._on_fields_loaded)
            self.fields_worker.error.connect(self._on_fields_error)
            self.fields_worker.start()

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

            # Default column (read-only) - shows expression/default from template
            default_item = QTableWidgetItem(str(default) if default else "")
            default_item.setFlags(default_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.params_table.setItem(i, 2, default_item)

            # Value column (editable) - user enters values to send to API
            self.params_table.setItem(i, 3, QTableWidgetItem(""))

        self._log(f"✓ Loaded {len(parameters)} parameters")

    def _on_parameters_error(self, error: str):
        """Handle parameter load error."""
        self._set_ui_enabled(True)
        self.progress.setVisible(False)
        self._log(f"⚠️ Error loading parameters: {error}")

    def _on_fields_loaded(self, fields: list):
        """Handle loaded fields."""
        self._fields = fields
        self.fields_table.setRowCount(len(fields))

        for i, f in enumerate(fields):
            name = f.get("name", "")
            ftype = f.get("type", "String")
            desc = f.get("description", "")

            name_item = QTableWidgetItem(name)
            name_item.setFlags(name_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.fields_table.setItem(i, 0, name_item)

            type_item = QTableWidgetItem(ftype)
            type_item.setFlags(type_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.fields_table.setItem(i, 1, type_item)

            desc_item = QTableWidgetItem(desc)
            desc_item.setFlags(desc_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.fields_table.setItem(i, 2, desc_item)

        # Show fields section only if there are fields defined
        self.fields_group.setVisible(len(fields) > 0)
        
        if fields:
            self._log(f"✓ Loaded {len(fields)} fields")

    def _on_fields_error(self, error: str):
        """Handle fields load error."""
        self._log(f"⚠️ Fields: {error}")

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
        self.params_table.setItem(row, 2, QTableWidgetItem(""))  # Default (empty for manual)
        self.params_table.setItem(row, 3, QTableWidgetItem(value))  # Value

        self.param_name_input.clear()
        self.param_value_input.clear()

    def _load_request_from_file(self):
        """Load request (parameters and data) from JSON file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Load Request",
            "",
            "JSON Files (*.json);;All Files (*)",
        )
        if not file_path:
            return

        try:
            with open(file_path) as f:
                request = json.load(f)

            params = {}
            data = None

            if isinstance(request, dict):
                # Check for full request format with "parameters" key
                if "parameters" in request:
                    # Full request format: {"parameters": [...], "data": {...}}
                    params_list = request.get("parameters", [])
                    if isinstance(params_list, list):
                        params = {p.get("name"): p.get("value") for p in params_list if "name" in p}
                    data = request.get("data")
                else:
                    # Simple dict format: {"param_name": "value", ...}
                    # Exclude known request keys that aren't parameters
                    exclude_keys = {"data", "filename", "documentLocale", "pdfExportOptions", 
                                   "htmlExportOptions", "ignorePagination"}
                    params = {k: v for k, v in request.items() if k not in exclude_keys}
                    data = request.get("data")
            elif isinstance(request, list):
                # List format: [{"name": "param", "value": "val"}, ...]
                params = {p.get("name"): p.get("value") for p in request if "name" in p}
            else:
                raise ValueError("Invalid JSON format")

            # Apply parameters to table
            for row in range(self.params_table.rowCount()):
                name_item = self.params_table.item(row, 0)
                if name_item and name_item.text() in params:
                    self.params_table.setItem(row, 3, QTableWidgetItem(str(params[name_item.text()])))

            # Store and display data
            self._fields_data = data
            if data:
                self.data_editor.setPlainText(json.dumps(data, indent=2))
                self.data_editor.setVisible(True)
                self.data_label.setVisible(True)
                self.fields_group.updateGeometry()
                self._log(f"✓ Loaded request with parameters and data from {Path(file_path).name}")
            else:
                self.data_editor.clear()
                self.data_editor.setVisible(False)
                self.data_label.setVisible(False)
                self.fields_group.updateGeometry()
                self._log(f"✓ Loaded parameters from {Path(file_path).name}")
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to load request: {e}")

    def _on_format_changed(self, format: str):
        """Update output path extension and export options visibility when format changes."""
        current = self.output_input.text()
        if current:
            path = Path(current)
            self.output_input.setText(str(path.with_suffix(f".{format}")))
        self._update_export_options_visibility()

    def _update_export_options_visibility(self):
        """Show/hide export options based on selected format."""
        format = self.format_combo.currentText()
        # Only show export options button for formats that have options
        show = format in ("pdf", "html")
        self.export_options_btn.setVisible(show)
        self.export_summary_label.setVisible(show)
        self._update_export_summary()

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
            value_item = self.params_table.item(row, 3)
            if name_item and value_item:
                name = name_item.text()
                value = value_item.text()
                if value:  # Only include non-empty values
                    params[name] = value
        return params

    def _get_data(self) -> Optional[Dict[str, Any]]:
        """Get data from editor (user may have edited it)."""
        data_text = self.data_editor.toPlainText().strip()
        if not data_text:
            return self._fields_data  # Return stored data if editor is empty
        try:
            return json.loads(data_text)
        except json.JSONDecodeError:
            return self._fields_data  # Fall back to stored data if JSON is invalid

    def _get_pdf_options(self) -> Optional[Dict[str, Any]]:
        """Get PDF export options."""
        return self._pdf_options if self._pdf_options else None

    def _get_html_options(self) -> Optional[Dict[str, Any]]:
        """Get HTML export options."""
        return self._html_options if self._html_options else None

    def _open_export_options_dialog(self):
        """Open the export options dialog."""
        from muban_cli.gui.dialogs.export_options_dialog import ExportOptionsDialog

        format = self.format_combo.currentText()
        dialog = ExportOptionsDialog(
            parent=self,
            pdf_options=self._pdf_options,
            html_options=self._html_options,
            icc_profiles=self._icc_profiles,
        )
        # Switch to the appropriate tab
        if format == "html":
            dialog.tabs.setCurrentIndex(1)

        if dialog.exec():
            self._pdf_options = dialog.get_pdf_options() or {}
            self._html_options = dialog.get_html_options() or {}
            self._update_export_summary()

    def _update_export_summary(self):
        """Update the export options summary label."""
        format = self.format_combo.currentText()
        if format == "pdf":
            if self._pdf_options:
                parts = []
                if self._pdf_options.get("pdfaConformance"):
                    parts.append(self._pdf_options["pdfaConformance"])
                if self._pdf_options.get("iccProfile"):
                    parts.append(f"ICC: {self._pdf_options['iccProfile']}")
                if self._pdf_options.get("userPassword") or self._pdf_options.get("ownerPassword"):
                    parts.append("Encrypted")
                if parts:
                    self.export_summary_label.setText(", ".join(parts))
                else:
                    self.export_summary_label.setText("Custom settings")
            else:
                self.export_summary_label.setText("Default settings")
        elif format == "html":
            if self._html_options:
                parts = []
                if not self._html_options.get("embedFonts", True):
                    parts.append("No fonts")
                if not self._html_options.get("embedImages", True):
                    parts.append("No images")
                if self._html_options.get("useWebSafeFonts"):
                    parts.append("Web-safe")
                if self._html_options.get("removeEmptySpace"):
                    parts.append("Compact")
                if parts:
                    self.export_summary_label.setText(", ".join(parts))
                else:
                    self.export_summary_label.setText("Custom settings")
            else:
                self.export_summary_label.setText("Default settings")
        else:
            self.export_summary_label.setText("Default settings")

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

        # Validate data JSON if present
        data = self._get_data()
        data_text = self.data_editor.toPlainText().strip()
        if data_text and data is None:
            try:
                json.loads(data_text)
            except json.JSONDecodeError as e:
                QMessageBox.warning(self, "Error", f"Invalid data JSON: {e}")
                return

        client = self._get_client()
        if not client:
            return

        self._set_ui_enabled(False)
        self.progress.setVisible(True)
        self.progress.setRange(0, 0)
        self._log(f"Generating {self.format_combo.currentText().upper()}...")

        # Get export options based on format
        format = self.format_combo.currentText()
        pdf_options = self._get_pdf_options() if format == "pdf" else None
        html_options = self._get_html_options() if format == "html" else None

        self.generate_worker = GenerateWorker(
            client,
            template_id,
            output_path,
            format,
            self._get_parameters(),
            data,
            pdf_options,
            html_options,
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
        self.fields_table.setEnabled(enabled)
        self.data_editor.setEnabled(enabled)
        self.param_name_input.setEnabled(enabled)
        self.param_value_input.setEnabled(enabled)
        self.add_param_btn.setEnabled(enabled)
        self.load_request_btn.setEnabled(enabled)
        self.format_combo.setEnabled(enabled)
        self.output_input.setEnabled(enabled)
        self.output_browse_btn.setEnabled(enabled)
        self.export_options_btn.setEnabled(enabled)
        self.generate_btn.setEnabled(enabled)

    def _log(self, message: str):
        """Add message to status output."""
        self.status_output.append(message)
