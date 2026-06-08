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
    QTabWidget,
    QStyle,
    QApplication,
)

from muban_cli.api import MubanAPIClient
from muban_cli.config import get_config_manager
from muban_cli.utils import parse_typed_value, format_typed_value
from muban_cli.gui.icons import create_play_icon
from muban_cli.gui.error_dialog import show_error_dialog

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
        txt_export_options: Optional[Dict[str, Any]] = None,
        document_locale: Optional[str] = None,
        ignore_pagination: bool = False,
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
        self.txt_export_options = txt_export_options
        self.document_locale = document_locale
        self.ignore_pagination = ignore_pagination

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
                txt_export_options=self.txt_export_options,
                document_locale=self.document_locale,
                ignore_pagination=self.ignore_pagination,
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
        self._txt_options: Dict[str, Any] = {}
        self._document_locale: Optional[str] = None
        self._ignore_pagination: bool = False
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

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

        layout.addWidget(template_group)

        # Tabbed section for Parameters / Fields
        self.data_tabs = QTabWidget()

        # --- Parameters tab ---
        params_widget = QWidget()
        params_layout = QVBoxLayout(params_widget)
        params_layout.setContentsMargins(4, 4, 4, 4)

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
        self.params_table.setMinimumHeight(60)
        params_layout.addWidget(self.params_table, 1)

        # Manual parameter entry
        manual_layout = QHBoxLayout()
        self.param_name_input = QLineEdit()
        self.param_name_input.setPlaceholderText("Parameter name")
        self.param_value_input = QLineEdit()
        self.param_value_input.setPlaceholderText('Value ("text" for string, 123 for number)')
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

        self.copy_request_btn = QPushButton("Copy Request JSON")
        self.copy_request_btn.setToolTip("Copy the full assembled request body JSON to clipboard")
        self.copy_request_btn.clicked.connect(self._copy_request_json)
        file_layout.addWidget(self.copy_request_btn)

        self.edit_data_btn = QPushButton("Edit Request...")
        self.edit_data_btn.setToolTip("Open the JSON editor to view and edit the full request body")
        self.edit_data_btn.clicked.connect(self._open_data_editor)
        file_layout.addWidget(self.edit_data_btn)

        file_layout.addStretch()
        params_layout.addLayout(file_layout)

        # Data section (shown below Load Request when data is present)
        self.data_row_widget = QWidget()
        data_row = QHBoxLayout(self.data_row_widget)
        data_row.setContentsMargins(0, 4, 0, 0)
        data_row.setSpacing(8)

        self.data_label = QLabel("Data JSON:")
        data_row.addWidget(self.data_label)

        self.data_preview = QLabel("")
        data_row.addWidget(self.data_preview, 1)

        self.data_row_widget.setVisible(False)
        params_layout.addWidget(self.data_row_widget)

        self.data_tabs.addTab(params_widget, "Parameters")

        # --- Fields tab (added dynamically when fields are loaded) ---
        self.fields_widget = QWidget()
        fields_layout = QVBoxLayout(self.fields_widget)
        fields_layout.setContentsMargins(4, 4, 4, 4)

        self.fields_table = QTableWidget(0, 3)
        self.fields_table.setHorizontalHeaderLabels(["Name", "Type", "Description"])
        fields_header = self.fields_table.horizontalHeader()
        if fields_header:
            fields_header.setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
            fields_header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.fields_table.setColumnWidth(0, 200)
        self.fields_table.setColumnWidth(1, 80)
        self.fields_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.fields_table.setMinimumHeight(80)
        fields_layout.addWidget(self.fields_table)

        self._data_json = ""
        self._fields_tab_index = -1  # Not added yet

        layout.addWidget(self.data_tabs, 1)

        # Output options
        output_group = QGroupBox("Output Options")
        output_layout = QFormLayout(output_group)

        # Format (display uppercase, store lowercase as item data for API calls)
        self.format_combo = QComboBox()
        for fmt in ["pdf", "xlsx", "docx", "rtf", "html", "txt"]:
            self.format_combo.addItem(fmt.upper(), fmt)
        self.format_combo.currentIndexChanged.connect(self._on_format_changed)
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

        layout.addWidget(output_group)

        # Export options button
        export_layout = QHBoxLayout()
        self.export_options_btn = QPushButton("Export Options...")
        self.export_options_btn.setToolTip("Configure PDF/HTML/TXT export options")
        self.export_options_btn.clicked.connect(self._open_export_options_dialog)
        export_layout.addWidget(self.export_options_btn)
        self.export_summary_label = QLabel("Default settings")
        self.export_summary_label.setStyleSheet("color: gray; font-style: italic;")
        export_layout.addWidget(self.export_summary_label)
        export_layout.addStretch()
        layout.addLayout(export_layout)

        # Update export options visibility based on format
        self._update_export_options_visibility()

        # Generate button
        action_layout = QHBoxLayout()
        action_layout.addStretch()
        self.generate_btn = QPushButton("Generate Document")
        self.generate_btn.setMinimumWidth(150)
        self.generate_btn.clicked.connect(self._generate)
        action_layout.addWidget(self.generate_btn)
        layout.addLayout(action_layout)
        
        # Apply icons
        style = self.style()
        if style:
            self.export_options_btn.setIcon(style.standardIcon(QStyle.StandardPixmap.SP_FileDialogDetailedView))
        self.generate_btn.setIcon(create_play_icon())

        # Progress
        self.progress = QProgressBar()
        self.progress.setVisible(False)
        layout.addWidget(self.progress)

        # Status/log area (fixed at bottom)
        log_group = QGroupBox("Status")
        log_layout = QVBoxLayout(log_group)
        self.status_output = QTextEdit()
        self.status_output.setReadOnly(True)
        self.status_output.setMaximumHeight(100)
        log_layout.addWidget(self.status_output)
        layout.addWidget(log_group)

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
        self._data_json = ""
        self._update_data_preview()
        self._set_data_row_visible(False)
        self.fields_widget.updateGeometry()

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

        # Show Fields tab only if there are fields defined
        if len(fields) > 0 and self._fields_tab_index == -1:
            self._fields_tab_index = self.data_tabs.addTab(self.fields_widget, "Fields")
        elif len(fields) == 0 and self._fields_tab_index != -1:
            self.data_tabs.removeTab(self._fields_tab_index)
            self._fields_tab_index = -1
        
        if fields:
            self._log(f"✓ Loaded {len(fields)} fields")

    def _on_fields_error(self, error: str):
        """Handle fields load error."""
        self._log(f"⚠️ Fields: {error}")

    def _add_manual_param(self):
        """Add a manual parameter."""
        name = self.param_name_input.text().strip()
        value_text = self.param_value_input.text()
        if not name:
            return

        # Parse and format the value to show type
        typed_value = parse_typed_value(value_text)
        display_value = format_typed_value(typed_value)
        
        # Determine type name for display
        if typed_value is None:
            type_name = "null"
        elif isinstance(typed_value, bool):
            type_name = "Boolean"
        elif isinstance(typed_value, int):
            type_name = "Integer"
        elif isinstance(typed_value, float):
            type_name = "Number"
        else:
            type_name = "String"

        row = self.params_table.rowCount()
        self.params_table.insertRow(row)

        name_item = QTableWidgetItem(name)
        self.params_table.setItem(row, 0, name_item)
        self.params_table.setItem(row, 1, QTableWidgetItem(type_name))
        self.params_table.setItem(row, 2, QTableWidgetItem(""))  # Default (empty for manual)
        self.params_table.setItem(row, 3, QTableWidgetItem(display_value))  # Value with type indicator

        self.param_name_input.clear()
        self.param_value_input.clear()

    def _build_request_body(
        self,
        params: Dict[str, Any],
        data: Optional[Any] = None,
        pdf_options: Optional[Dict[str, Any]] = None,
        html_options: Optional[Dict[str, Any]] = None,
        txt_options: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Assemble the full request body dict from current UI state."""
        params_list = [{"name": k, "value": v} for k, v in params.items()]
        body: Dict[str, Any] = {"parameters": params_list}
        if data:
            body["data"] = data
        if self._document_locale:
            body["documentLocale"] = self._document_locale
        if self._ignore_pagination:
            body["ignorePagination"] = self._ignore_pagination
        if pdf_options:
            body["pdfExportOptions"] = pdf_options
        if html_options:
            body["htmlExportOptions"] = html_options
        if txt_options:
            body["txtExportOptions"] = txt_options
        return body

    def _copy_request_json(self):
        """Copy the full assembled request body JSON to the clipboard."""
        fmt = self._get_format()
        pdf_options = self._get_pdf_options() if fmt == "pdf" else None
        html_options = self._get_html_options() if fmt == "html" else None
        txt_options = self._get_txt_options() if fmt == "txt" else None
        params = self._get_parameters()
        data = self._get_data()
        body = self._build_request_body(params, data, pdf_options, html_options, txt_options)
        text = json.dumps(body, indent=2, ensure_ascii=False)
        app = QApplication.instance()
        if isinstance(app, QApplication):
            clipboard = app.clipboard()
            if clipboard:
                clipboard.setText(text)
        self._log("✓ Request JSON copied to clipboard")

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
            loaded_options = []

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
                                   "htmlExportOptions", "txtExportOptions", "ignorePagination"}
                    params = {k: v for k, v in request.items() if k not in exclude_keys}
                    data = request.get("data")
                
                # Extract export options from the request
                if "documentLocale" in request:
                    self._document_locale = request["documentLocale"]
                    loaded_options.append(f"locale={self._document_locale}")
                if "ignorePagination" in request:
                    self._ignore_pagination = bool(request["ignorePagination"])
                    loaded_options.append("ignorePagination")
                if "pdfExportOptions" in request and isinstance(request["pdfExportOptions"], dict):
                    self._pdf_options = request["pdfExportOptions"]
                    loaded_options.append("pdfExportOptions")
                if "htmlExportOptions" in request and isinstance(request["htmlExportOptions"], dict):
                    self._html_options = request["htmlExportOptions"]
                    loaded_options.append("htmlExportOptions")
                if "txtExportOptions" in request and isinstance(request["txtExportOptions"], dict):
                    self._txt_options = request["txtExportOptions"]
                    loaded_options.append("txtExportOptions")
                    
            elif isinstance(request, list):
                # List format: [{"name": "param", "value": "val"}, ...]
                params = {p.get("name"): p.get("value") for p in request if "name" in p}
            else:
                raise ValueError("Invalid JSON format")

            # Apply parameters to table (preserving types from JSON)
            for row in range(self.params_table.rowCount()):
                name_item = self.params_table.item(row, 0)
                if name_item and name_item.text() in params:
                    param_value = params[name_item.text()]
                    display_value = format_typed_value(param_value)
                    self.params_table.setItem(row, 3, QTableWidgetItem(display_value))

            # Store and display data
            self._fields_data = data
            options_info = f" (export options: {', '.join(loaded_options)})" if loaded_options else ""
            
            if data:
                self._data_json = json.dumps(data, indent=2, ensure_ascii=False)
                self._update_data_preview()
                self._set_data_row_visible(True)
                self.fields_widget.updateGeometry()
                self._log(f"✓ Loaded request with parameters and data from {Path(file_path).name}{options_info}")
            else:
                self._data_json = ""
                self._update_data_preview()
                self._set_data_row_visible(False)
                self.fields_widget.updateGeometry()
                self._log(f"✓ Loaded parameters from {Path(file_path).name}{options_info}")
            
            # Update export summary to reflect loaded options
            self._update_export_summary()
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to load request: {e}")

    def _get_format(self) -> str:
        """Get the current format as lowercase string for API calls."""
        return self.format_combo.currentData() or self.format_combo.currentText().lower()
    
    def _on_format_changed(self, index: int):
        """Update output path extension and export options visibility when format changes."""
        fmt = self._get_format()
        # HTML format returns a ZIP archive, not a raw .html file
        _EXT_MAP = {"html": "zip"}
        ext = _EXT_MAP.get(fmt, fmt)
        current = self.output_input.text()
        if current:
            path = Path(current)
            self.output_input.setText(str(path.with_suffix(f".{ext}")))
        self._update_export_options_visibility()

    def _update_export_options_visibility(self):
        """Show/hide export options based on selected format."""
        format = self._get_format()
        # Only show export options button for formats that have options
        show = format in ("pdf", "html", "txt")
        self.export_options_btn.setVisible(show)
        self.export_summary_label.setVisible(show)
        self._update_export_summary()

    def _browse_output(self):
        """Browse for output file."""
        fmt = self._get_format()
        # HTML format returns a ZIP archive, not a raw .html file
        _EXT_MAP = {"html": "zip"}
        filter_map = {
            "pdf": "PDF Files (*.pdf)",
            "xlsx": "Excel Files (*.xlsx)",
            "docx": "Word Files (*.docx)",
            "rtf": "RTF Files (*.rtf)",
            "html": "ZIP Archive (*.zip)",
            "txt": "Text Files (*.txt)",
        }
        ext = _EXT_MAP.get(fmt, fmt)

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Document As",
            self.output_input.text() or f"document.{ext}",
            f"{filter_map.get(fmt, 'All Files (*)')};;All Files (*)",
        )
        if file_path:
            self.output_input.setText(file_path)

    def _get_parameters(self) -> Dict[str, Any]:
        """Get parameters from table with proper typing."""
        params = {}
        for row in range(self.params_table.rowCount()):
            name_item = self.params_table.item(row, 0)
            value_item = self.params_table.item(row, 3)
            if name_item and value_item:
                name = name_item.text()
                value_text = value_item.text()
                if value_text:  # Only include non-empty values
                    # Parse the displayed value back to typed value
                    params[name] = parse_typed_value(value_text)
        return params

    def _get_data(self) -> Optional[Dict[str, Any]]:
        """Get data from internal storage."""
        if not self._data_json:
            return self._fields_data
        try:
            return json.loads(self._data_json)
        except json.JSONDecodeError:
            return self._fields_data  # Fall back to stored data if JSON is invalid

    def _get_pdf_options(self) -> Optional[Dict[str, Any]]:
        """Get PDF export options."""
        return self._pdf_options if self._pdf_options else None

    def _get_html_options(self) -> Optional[Dict[str, Any]]:
        """Get HTML export options."""
        return self._html_options if self._html_options else None

    def _get_txt_options(self) -> Optional[Dict[str, Any]]:
        """Get TXT export options."""
        return self._txt_options if self._txt_options else None

    def _update_data_preview(self):
        """Update the data preview label with a summary."""
        if not self._data_json:
            self.data_preview.setText("")
            return

        try:
            data = json.loads(self._data_json)
            # Count collections and records
            collections = len(data) if isinstance(data, dict) else 0
            total_records = 0
            if isinstance(data, dict):
                for key, value in data.items():
                    if isinstance(value, list):
                        total_records += len(value)

            lines = self._data_json.count('\n') + 1
            chars = len(self._data_json)

            preview = f"{collections} collection(s), {total_records} record(s) | {lines} lines, {chars} chars"
            self.data_preview.setText(preview)
        except json.JSONDecodeError:
            self.data_preview.setText("Invalid JSON")

    def _set_data_row_visible(self, visible: bool):
        """Show or hide the data row widget."""
        self.data_row_widget.setVisible(visible)

    def _open_data_editor(self):
        """Open the full request JSON in the editor dialog."""
        from muban_cli.gui.dialogs.data_editor_dialog import DataEditorDialog

        fmt = self._get_format()
        pdf_options = self._get_pdf_options() if fmt == "pdf" else None
        html_options = self._get_html_options() if fmt == "html" else None
        txt_options = self._get_txt_options() if fmt == "txt" else None
        params = self._get_parameters()
        data = self._get_data()
        body = self._build_request_body(params, data, pdf_options, html_options, txt_options)
        body_json = json.dumps(body, indent=2, ensure_ascii=False)

        dialog = DataEditorDialog(
            parent=self,
            data=body_json,
            title="Edit Request JSON"
        )

        if dialog.exec():
            try:
                edited = json.loads(dialog.get_data())
            except json.JSONDecodeError as e:
                QMessageBox.warning(self, "Invalid JSON", f"Could not parse edited request: {e}")
                return

            # Apply parameters
            params_list = edited.get("parameters", [])
            if isinstance(params_list, list):
                new_params = {p.get("name"): p.get("value") for p in params_list if "name" in p}
                for row in range(self.params_table.rowCount()):
                    name_item = self.params_table.item(row, 0)
                    if name_item and name_item.text() in new_params:
                        self.params_table.setItem(row, 3, QTableWidgetItem(
                            format_typed_value(new_params[name_item.text()])
                        ))

            # Apply data
            new_data = edited.get("data")
            if new_data is not None:
                self._data_json = json.dumps(new_data, indent=2, ensure_ascii=False)
            else:
                self._data_json = ""
            self._update_data_preview()
            self._set_data_row_visible(bool(self._data_json))

            # Apply options
            if "documentLocale" in edited:
                self._document_locale = edited["documentLocale"] or None
            if "ignorePagination" in edited:
                self._ignore_pagination = bool(edited["ignorePagination"])
            if "pdfExportOptions" in edited and isinstance(edited["pdfExportOptions"], dict):
                self._pdf_options = edited["pdfExportOptions"]
            if "htmlExportOptions" in edited and isinstance(edited["htmlExportOptions"], dict):
                self._html_options = edited["htmlExportOptions"]
            if "txtExportOptions" in edited and isinstance(edited["txtExportOptions"], dict):
                self._txt_options = edited["txtExportOptions"]

            self._update_export_summary()
            self._log("✓ Request updated from editor")

    def _open_export_options_dialog(self):
        """Open the export options dialog."""
        from muban_cli.gui.dialogs.export_options_dialog import ExportOptionsDialog

        fmt = self._get_format()
        dialog = ExportOptionsDialog(
            parent=self,
            pdf_options=self._pdf_options,
            html_options=self._html_options,
            txt_options=self._txt_options,
            icc_profiles=self._icc_profiles,
            document_locale=self._document_locale,
            ignore_pagination=self._ignore_pagination,
        )
        # Switch to the appropriate tab (General is tab 0, PDF is 1, HTML is 2, TXT is 3)
        if fmt == "pdf":
            dialog.tabs.setCurrentIndex(1)
        elif fmt == "html":
            dialog.tabs.setCurrentIndex(2)
        elif fmt == "txt":
            dialog.tabs.setCurrentIndex(3)

        if dialog.exec():
            self._pdf_options = dialog.get_pdf_options() or {}
            self._html_options = dialog.get_html_options() or {}
            self._txt_options = dialog.get_txt_options() or {}
            self._document_locale = dialog.get_document_locale()
            self._ignore_pagination = dialog.get_ignore_pagination()
            self._update_export_summary()

    def _update_export_summary(self):
        """Update the export options summary label."""
        format = self._get_format()
        
        # Build general options parts (apply to all formats)
        general_parts = []
        if self._document_locale:
            general_parts.append(f"Locale: {self._document_locale}")
        if self._ignore_pagination:
            general_parts.append("No pagination")
        
        format_parts = []
        
        if format == "pdf":
            if self._pdf_options:
                if self._pdf_options.get("pdfaConformance"):
                    format_parts.append(self._pdf_options["pdfaConformance"])
                if self._pdf_options.get("iccProfile"):
                    format_parts.append(f"ICC: {self._pdf_options['iccProfile']}")
                if self._pdf_options.get("userPassword") or self._pdf_options.get("ownerPassword"):
                    format_parts.append("Encrypted")
        elif format == "html":
            if self._html_options:
                if not self._html_options.get("embedFonts", True):
                    format_parts.append("No fonts")
                if not self._html_options.get("embedImages", True):
                    format_parts.append("No images")
                if self._html_options.get("useWebSafeFonts"):
                    format_parts.append("Web-safe")
                if self._html_options.get("removeEmptySpace"):
                    format_parts.append("Compact")
        elif format == "txt":
            if self._txt_options:
                if self._txt_options.get("characterWidth"):
                    format_parts.append(f"W:{self._txt_options['characterWidth']}")
                if self._txt_options.get("characterHeight"):
                    format_parts.append(f"H:{self._txt_options['characterHeight']}")
                if self._txt_options.get("pageWidthInChars"):
                    format_parts.append(f"{self._txt_options['pageWidthInChars']} cols")
                if self._txt_options.get("pageHeightInChars"):
                    format_parts.append(f"{self._txt_options['pageHeightInChars']} rows")
                if self._txt_options.get("trimLineRight"):
                    format_parts.append("Trim")
        
        # Combine general and format-specific parts
        all_parts = general_parts + format_parts
        if all_parts:
            self.export_summary_label.setText(", ".join(all_parts))
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
        if self._data_json and data is None:
            try:
                json.loads(self._data_json)
            except json.JSONDecodeError as e:
                QMessageBox.warning(self, "Error", f"Invalid data JSON: {e}")
                return

        client = self._get_client()
        if not client:
            return

        self._set_ui_enabled(False)
        self.progress.setVisible(True)
        self.progress.setRange(0, 0)
        self._log(f"Generating {self.format_combo.currentText()}...")

        # Get export options based on format
        format = self._get_format()
        pdf_options = self._get_pdf_options() if format == "pdf" else None
        html_options = self._get_html_options() if format == "html" else None
        txt_options = self._get_txt_options() if format == "txt" else None
        
        # Build request body for debug logging (mirrors what API client does)
        params = self._get_parameters()
        request_body = self._build_request_body(params, data, pdf_options, html_options, txt_options)

        # Log request body in debug mode
        logger.debug("Generate document request body:\n%s", json.dumps(request_body, indent=2, ensure_ascii=False))

        self.generate_worker = GenerateWorker(
            client,
            template_id,
            output_path,
            format,
            params,
            data,
            pdf_options,
            html_options,
            txt_options,
            self._document_locale,
            self._ignore_pagination,
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
        show_error_dialog(self, "Generation Error", error)

    def _set_ui_enabled(self, enabled: bool):
        """Enable/disable UI elements."""
        self.template_id_input.setEnabled(enabled)
        self.load_params_btn.setEnabled(enabled)
        self.params_table.setEnabled(enabled)
        self.fields_table.setEnabled(enabled)
        self.edit_data_btn.setEnabled(enabled)
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
