"""
Tags Management Dialog - View and edit template tags.
"""

import re
from typing import List, Dict, Optional

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QPushButton,
    QDialogButtonBox,
    QMessageBox,
    QLabel,
    QAbstractItemView,
)


# Validation patterns from API spec
KEY_PATTERN = re.compile(r'^[a-zA-Z0-9_-]+$')
VALUE_PATTERN = re.compile(r'^[a-zA-Z0-9_.\-]+$')
MAX_KEY_LENGTH = 64
MAX_VALUE_LENGTH = 255
MAX_TAGS = 20


class TagsDialog(QDialog):
    """Dialog for managing template tags."""

    def __init__(self, parent=None, template_name: str = "", tags: Optional[List[Dict[str, str]]] = None):
        super().__init__(parent)
        self._tags = tags or []
        self.setWindowTitle(f"Tags — {template_name}" if template_name else "Manage Tags")
        self.setMinimumWidth(500)
        self.setMinimumHeight(350)
        self._setup_ui()
        self._load_tags()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        # Info label
        info = QLabel(f"Max {MAX_TAGS} tags. Keys: alphanumeric, _, -. Values: alphanumeric, _, ., -")
        info.setWordWrap(True)
        layout.addWidget(info)

        # Tags table
        self.table = QTableWidget(0, 2)
        self.table.setHorizontalHeaderLabels(["Key", "Value"])
        header = self.table.horizontalHeader()
        if header:
            header.setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
            header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.setColumnWidth(0, 180)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        layout.addWidget(self.table)

        # Add / Remove buttons
        btn_layout = QHBoxLayout()
        self.add_btn = QPushButton("Add Tag")
        self.add_btn.clicked.connect(self._add_row)
        btn_layout.addWidget(self.add_btn)

        self.remove_btn = QPushButton("Remove Selected")
        self.remove_btn.clicked.connect(self._remove_selected)
        btn_layout.addWidget(self.remove_btn)

        btn_layout.addStretch()

        self.count_label = QLabel(f"0 / {MAX_TAGS}")
        btn_layout.addWidget(self.count_label)
        layout.addLayout(btn_layout)

        # OK / Cancel
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._validate_and_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _load_tags(self):
        for tag in self._tags:
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(tag.get("key", "")))
            self.table.setItem(row, 1, QTableWidgetItem(tag.get("value", "")))
        self._update_count()

    def _add_row(self):
        if self.table.rowCount() >= MAX_TAGS:
            QMessageBox.warning(self, "Limit Reached", f"Maximum {MAX_TAGS} tags allowed.")
            return
        row = self.table.rowCount()
        self.table.insertRow(row)
        self.table.setItem(row, 0, QTableWidgetItem(""))
        self.table.setItem(row, 1, QTableWidgetItem(""))
        self.table.setCurrentCell(row, 0)
        self.table.editItem(self.table.item(row, 0))
        self._update_count()

    def _remove_selected(self):
        row = self.table.currentRow()
        if row >= 0:
            self.table.removeRow(row)
            self._update_count()

    def _update_count(self):
        self.count_label.setText(f"{self.table.rowCount()} / {MAX_TAGS}")

    def _validate_and_accept(self):
        """Validate all tags before accepting."""
        errors = []
        seen_keys = set()
        for row in range(self.table.rowCount()):
            key_item = self.table.item(row, 0)
            value_item = self.table.item(row, 1)
            key = key_item.text().strip() if key_item else ""
            value = value_item.text().strip() if value_item else ""

            if not key and not value:
                continue  # skip empty rows

            if not key:
                errors.append(f"Row {row + 1}: Key is required")
                continue

            if len(key) > MAX_KEY_LENGTH:
                errors.append(f"Row {row + 1}: Key exceeds {MAX_KEY_LENGTH} chars")
            elif not KEY_PATTERN.match(key):
                errors.append(f"Row {row + 1}: Key '{key}' has invalid characters")

            if not value:
                errors.append(f"Row {row + 1}: Value is required")
            elif len(value) > MAX_VALUE_LENGTH:
                errors.append(f"Row {row + 1}: Value exceeds {MAX_VALUE_LENGTH} chars")
            elif not VALUE_PATTERN.match(value):
                errors.append(f"Row {row + 1}: Value '{value}' has invalid characters")

            if key in seen_keys:
                errors.append(f"Row {row + 1}: Duplicate key '{key}'")
            seen_keys.add(key)

        if errors:
            QMessageBox.warning(self, "Validation Errors", "\n".join(errors))
            return

        self.accept()

    def get_tags(self) -> List[Dict[str, str]]:
        """Return the list of tags from the table."""
        tags = []
        for row in range(self.table.rowCount()):
            key_item = self.table.item(row, 0)
            value_item = self.table.item(row, 1)
            key = key_item.text().strip() if key_item else ""
            value = value_item.text().strip() if value_item else ""
            if key and value:
                tags.append({"key": key, "value": value})
        return tags
