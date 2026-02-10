"""
Templates Tab - List and manage templates on the server.
"""

from pathlib import Path
from typing import Optional, Dict, Any, List

from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QShowEvent
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGroupBox,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QMessageBox,
    QProgressBar,
    QFileDialog,
    QAbstractItemView,
)

from muban_cli.api import MubanAPIClient
from muban_cli.config import get_config_manager


class TemplateWorker(QThread):
    """Worker thread for template operations."""

    finished = pyqtSignal(dict)  # Emits {'templates': [...], 'page': int, 'total_pages': int, 'total_items': int}
    error = pyqtSignal(str)

    def __init__(self, client: MubanAPIClient, search: Optional[str] = None, page: int = 1):
        super().__init__()
        self.client = client
        self.search = search
        self.page = page

    def run(self):
        try:
            result = self.client.list_templates(search=self.search, page=self.page)
            
            # Handle different response structures
            # New format: {'meta': ..., 'data': {'items': [...], 'totalPages': ..., 'totalItems': ...}, 'errors': []}
            templates = []
            total_pages = 1
            total_items = 0
            current_page = self.page
            
            if isinstance(result, dict):
                if "data" in result and isinstance(result["data"], dict):
                    data = result["data"]
                    templates = data.get("items", [])
                    total_pages = data.get("totalPages", 1)
                    total_items = data.get("totalItems", len(templates))
                    current_page = data.get("currentPage", self.page)
                elif "content" in result:
                    templates = result["content"]
                    total_pages = result.get("totalPages", 1)
                    total_items = result.get("totalElements", len(templates))
                else:
                    templates = result if isinstance(result, list) else []
            else:
                templates = result if isinstance(result, list) else []
                
            self.finished.emit({
                'templates': templates,
                'page': current_page,
                'total_pages': total_pages,
                'total_items': total_items
            })
        except Exception as e:
            self.error.emit(str(e))


class UploadWorker(QThread):
    """Worker thread for template upload."""

    finished = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, client: MubanAPIClient, file_path: str, name: str, author: str):
        super().__init__()
        self.client = client
        self.file_path = Path(file_path)
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
            self.error.emit(str(e))


class TemplatesTab(QWidget):
    """Tab for managing templates."""

    def __init__(self):
        super().__init__()
        self._templates: List[Dict[str, Any]] = []
        self._initial_load_done = False
        self.worker: Optional[TemplateWorker] = None
        self._current_page = 1
        self._total_pages = 1
        self._total_items = 0
        self._setup_ui()

    def showEvent(self, event: QShowEvent):
        """Auto-load templates on first display."""
        super().showEvent(event)
        if not self._initial_load_done:
            self._initial_load_done = True
            self._load_templates()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        # Connection status
        status_layout = QHBoxLayout()
        self.status_label = QLabel("Not connected")
        status_layout.addWidget(self.status_label)
        status_layout.addStretch()
        self.refresh_btn = QPushButton("🔄 Refresh")
        self.refresh_btn.clicked.connect(self._load_templates)
        status_layout.addWidget(self.refresh_btn)
        layout.addLayout(status_layout)

        # Search
        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search templates...")
        self.search_input.returnPressed.connect(self._search_templates)
        search_layout.addWidget(self.search_input)
        self.search_btn = QPushButton("Search")
        self.search_btn.clicked.connect(self._search_templates)
        search_layout.addWidget(self.search_btn)
        layout.addLayout(search_layout)

        # Templates table
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["ID", "Name", "Author", "Created"])
        header = self.table.horizontalHeader()
        if header:
            header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
            header.setStretchLastSection(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setColumnWidth(0, 280)
        self.table.setColumnWidth(1, 200)
        self.table.setColumnWidth(2, 250)
        layout.addWidget(self.table)

        # Progress
        self.progress = QProgressBar()
        self.progress.setVisible(False)
        layout.addWidget(self.progress)

        # Pagination
        pagination_layout = QHBoxLayout()
        self.prev_btn = QPushButton("◀ Previous")
        self.prev_btn.clicked.connect(self._prev_page)
        self.prev_btn.setEnabled(False)
        pagination_layout.addWidget(self.prev_btn)
        
        pagination_layout.addStretch()
        self.page_label = QLabel("Page 1 of 1")
        pagination_layout.addWidget(self.page_label)
        pagination_layout.addStretch()
        
        self.next_btn = QPushButton("Next ▶")
        self.next_btn.clicked.connect(self._next_page)
        self.next_btn.setEnabled(False)
        pagination_layout.addWidget(self.next_btn)
        layout.addLayout(pagination_layout)

        # Actions
        actions_group = QGroupBox("Actions")
        actions_layout = QHBoxLayout(actions_group)

        self.upload_btn = QPushButton("📤 Upload Template...")
        self.upload_btn.clicked.connect(self._upload_template)
        actions_layout.addWidget(self.upload_btn)

        self.download_btn = QPushButton("📥 Download")
        self.download_btn.clicked.connect(self._download_template)
        actions_layout.addWidget(self.download_btn)

        self.delete_btn = QPushButton("🗑️ Delete")
        self.delete_btn.clicked.connect(self._delete_template)
        actions_layout.addWidget(self.delete_btn)

        actions_layout.addStretch()

        self.generate_btn = QPushButton("⚙️ Generate Document...")
        self.generate_btn.clicked.connect(self._generate_from_template)
        actions_layout.addWidget(self.generate_btn)

        layout.addWidget(actions_group)

    def _get_client(self) -> Optional[MubanAPIClient]:
        """Get configured API client."""
        try:
            config = get_config_manager().load()
            if not config.server_url:
                self.status_label.setText("⚠️ Server not configured - go to Settings tab")
                return None

            client = MubanAPIClient(config)
            self.status_label.setText(f"✓ Connected to {config.server_url}")
            return client
        except Exception as e:
            self.status_label.setText(f"⚠️ Error: {e}")
            return None

    def _search_templates(self):
        """Search templates (resets to page 1)."""
        self._load_templates(reset_page=True)

    def _load_templates(self, reset_page: bool = False):
        """Load templates from server."""
        try:
            client = self._get_client()
            if not client:
                return

            if reset_page:
                self._current_page = 1

            self._set_ui_enabled(False)
            self.progress.setVisible(True)
            self.progress.setRange(0, 0)

            search = self.search_input.text().strip() or None
            self.worker = TemplateWorker(client, search, self._current_page)
            self.worker.finished.connect(self._on_templates_loaded)
            self.worker.error.connect(self._on_load_error)
            self.worker.start()
        except Exception as e:
            self._set_ui_enabled(True)
            self.progress.setVisible(False)
            QMessageBox.critical(self, "Error", f"Failed to load templates: {e}")

    def _on_templates_loaded(self, result: dict):
        """Handle loaded templates."""
        self._set_ui_enabled(True)
        self.progress.setVisible(False)

        templates = result.get('templates', [])
        self._current_page = result.get('page', 1)
        self._total_pages = result.get('total_pages', 1)
        self._total_items = result.get('total_items', len(templates))

        self._templates = templates
        self.table.setRowCount(len(templates))

        for i, t in enumerate(templates):
            self.table.setItem(i, 0, QTableWidgetItem(t.get("id", "")))
            self.table.setItem(i, 1, QTableWidgetItem(t.get("name", "")))
            self.table.setItem(i, 2, QTableWidgetItem(t.get("author", "")))
            # Format date: "2025-12-18T23:01:39.952558" -> "2025-12-18 23:01:39"
            created = t.get("created", "")
            if created:
                created = created.replace("T", " ")[:19]
            self.table.setItem(i, 3, QTableWidgetItem(created))

        # Update pagination controls
        self._update_pagination_ui()
        self.status_label.setText(f"✓ Loaded {len(templates)} of {self._total_items} templates")

    def _update_pagination_ui(self):
        """Update pagination buttons and label."""
        self.page_label.setText(f"Page {self._current_page} of {self._total_pages} ({self._total_items} total)")
        self.prev_btn.setEnabled(self._current_page > 1)
        self.next_btn.setEnabled(self._current_page < self._total_pages)

    def _prev_page(self):
        """Go to previous page."""
        if self._current_page > 1:
            self._current_page -= 1
            self._load_templates()

    def _next_page(self):
        """Go to next page."""
        if self._current_page < self._total_pages:
            self._current_page += 1
            self._load_templates()

    def _on_load_error(self, error: str):
        """Handle load error."""
        self._set_ui_enabled(True)
        self.progress.setVisible(False)
        self.status_label.setText(f"⚠️ Error: {error}")
        QMessageBox.warning(self, "Error", f"Failed to load templates:\n{error}")

    def _get_selected_template(self) -> Optional[Dict[str, Any]]:
        """Get currently selected template."""
        row = self.table.currentRow()
        if row < 0 or row >= len(self._templates):
            return None
        return self._templates[row]

    def _upload_template(self):
        """Upload a template package."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Template Package",
            "",
            "ZIP Files (*.zip);;All Files (*)",
        )
        if not file_path:
            return

        # Ask for metadata
        from muban_cli.gui.dialogs.upload_dialog import UploadDialog

        dialog = UploadDialog(file_path, self)
        if not dialog.exec():
            return

        client = self._get_client()
        if not client:
            return

        self._set_ui_enabled(False)
        self.progress.setVisible(True)
        self.progress.setRange(0, 0)

        self.upload_worker = UploadWorker(
            client,
            file_path,
            dialog.get_name(),
            dialog.get_author(),
        )
        self.upload_worker.finished.connect(self._on_upload_finished)
        self.upload_worker.error.connect(self._on_upload_error)
        self.upload_worker.start()

    def _on_upload_finished(self, result: dict):
        """Handle successful upload."""
        self._set_ui_enabled(True)
        self.progress.setVisible(False)
        QMessageBox.information(
            self,
            "Upload Complete",
            f"Template uploaded successfully!\nID: {result.get('id', 'N/A')}",
        )
        self._load_templates()

    def _on_upload_error(self, error: str):
        """Handle upload error."""
        self._set_ui_enabled(True)
        self.progress.setVisible(False)
        QMessageBox.critical(self, "Upload Error", error)

    def _download_template(self):
        """Download selected template."""
        template = self._get_selected_template()
        if not template:
            QMessageBox.warning(self, "No Selection", "Please select a template to download.")
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Template As",
            f"{template.get('name', 'template')}.zip",
            "ZIP Files (*.zip);;All Files (*)",
        )
        if not file_path:
            return

        client = self._get_client()
        if not client:
            return

        try:
            client.download_template(template["id"], Path(file_path))
            QMessageBox.information(self, "Download Complete", f"Template saved to:\n{file_path}")
        except Exception as e:
            QMessageBox.critical(self, "Download Error", str(e))

    def _delete_template(self):
        """Delete selected template."""
        template = self._get_selected_template()
        if not template:
            QMessageBox.warning(self, "No Selection", "Please select a template to delete.")
            return

        reply = QMessageBox.question(
            self,
            "Confirm Delete",
            f"Are you sure you want to delete template:\n{template.get('name', template['id'])}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        client = self._get_client()
        if not client:
            return

        try:
            client.delete_template(template["id"])
            QMessageBox.information(self, "Deleted", "Template deleted successfully.")
            self._load_templates()
        except Exception as e:
            QMessageBox.critical(self, "Delete Error", str(e))

    def _generate_from_template(self):
        """Switch to generate tab with selected template."""
        template = self._get_selected_template()
        if not template:
            QMessageBox.warning(self, "No Selection", "Please select a template first.")
            return

        # Find main window and switch to generate tab
        main_window = self.window()
        if hasattr(main_window, "tabs") and hasattr(main_window, "generate_tab"):
            generate_tab = getattr(main_window, "generate_tab")
            tabs = getattr(main_window, "tabs")
            generate_tab.set_template(template["id"])
            tabs.setCurrentWidget(generate_tab)

    def _set_ui_enabled(self, enabled: bool):
        """Enable/disable UI elements."""
        self.refresh_btn.setEnabled(enabled)
        self.search_input.setEnabled(enabled)
        self.search_btn.setEnabled(enabled)
        self.table.setEnabled(enabled)
        self.upload_btn.setEnabled(enabled)
        self.download_btn.setEnabled(enabled)
        self.delete_btn.setEnabled(enabled)
        self.generate_btn.setEnabled(enabled)
        if enabled:
            self._update_pagination_ui()
        else:
            self.prev_btn.setEnabled(False)
            self.next_btn.setEnabled(False)
