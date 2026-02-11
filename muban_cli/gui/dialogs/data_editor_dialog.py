"""
Data Editor Dialog - Edit JSON data in a larger, more capable editor.
"""

import json
from typing import Optional

from PyQt6.QtCore import Qt, QRect, QSize
from PyQt6.QtGui import QFont, QTextCursor, QPainter, QColor
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QPlainTextEdit,
    QPushButton,
    QDialogButtonBox,
    QLabel,
    QMessageBox,
    QWidget,
)


class LineNumberArea(QWidget):
    """Widget that displays line numbers for a CodeEditor."""

    def __init__(self, editor):
        super().__init__(editor)
        self.editor = editor

    def sizeHint(self) -> QSize:
        return QSize(self.editor.line_number_area_width(), 0)

    def paintEvent(self, event):
        self.editor.line_number_area_paint_event(event)


class CodeEditor(QPlainTextEdit):
    """PlainTextEdit with line numbers."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.line_number_area = LineNumberArea(self)

        self.blockCountChanged.connect(self._update_line_number_area_width)
        self.updateRequest.connect(self._update_line_number_area)

        self._update_line_number_area_width(0)

    def line_number_area_width(self) -> int:
        digits = 1
        max_num = max(1, self.blockCount())
        while max_num >= 10:
            max_num //= 10
            digits += 1
        space = 10 + self.fontMetrics().horizontalAdvance('9') * digits
        return space

    def _update_line_number_area_width(self, _):
        self.setViewportMargins(self.line_number_area_width(), 0, 0, 0)

    def _update_line_number_area(self, rect, dy):
        if dy:
            self.line_number_area.scroll(0, dy)
        else:
            self.line_number_area.update(0, rect.y(), self.line_number_area.width(), rect.height())

        viewport = self.viewport()
        if viewport and rect.contains(viewport.rect()):
            self._update_line_number_area_width(0)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        cr = self.contentsRect()
        self.line_number_area.setGeometry(QRect(cr.left(), cr.top(), self.line_number_area_width(), cr.height()))

    def line_number_area_paint_event(self, event):
        painter = QPainter(self.line_number_area)
        painter.fillRect(event.rect(), QColor(240, 240, 240))

        block = self.firstVisibleBlock()
        block_number = block.blockNumber()
        top = round(self.blockBoundingGeometry(block).translated(self.contentOffset()).top())
        bottom = top + round(self.blockBoundingRect(block).height())

        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                number = str(block_number + 1)
                painter.setPen(QColor(120, 120, 120))
                painter.drawText(0, top, self.line_number_area.width() - 5,
                                 self.fontMetrics().height(),
                                 Qt.AlignmentFlag.AlignRight, number)

            block = block.next()
            top = bottom
            bottom = top + round(self.blockBoundingRect(block).height())
            block_number += 1


class DataEditorDialog(QDialog):
    """Dialog for editing JSON data with formatting and validation capabilities."""

    def __init__(self, parent=None, data: str = "", title: str = "Edit Data"):
        super().__init__(parent)
        self._data = data
        self.setWindowTitle(title)
        self.setMinimumSize(800, 600)
        self.resize(900, 700)
        self._setup_ui()
        self._load_data()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        # Toolbar with actions
        toolbar = QHBoxLayout()

        self.format_btn = QPushButton("Format JSON")
        self.format_btn.setToolTip("Format and indent JSON (Ctrl+Shift+F)")
        self.format_btn.clicked.connect(self._format_json)
        toolbar.addWidget(self.format_btn)

        self.validate_btn = QPushButton("Validate JSON")
        self.validate_btn.setToolTip("Check if JSON is valid")
        self.validate_btn.clicked.connect(self._validate_json)
        toolbar.addWidget(self.validate_btn)

        self.minify_btn = QPushButton("Minify")
        self.minify_btn.setToolTip("Remove whitespace from JSON")
        self.minify_btn.clicked.connect(self._minify_json)
        toolbar.addWidget(self.minify_btn)

        toolbar.addStretch()

        # Status label
        self.status_label = QLabel("")
        toolbar.addWidget(self.status_label)

        layout.addLayout(toolbar)

        # Editor with line numbers
        self.editor = CodeEditor()
        self.editor.setPlaceholderText(
            'Enter JSON data for template fields.\n\n'
            'Format for collections:\n'
            '{\n'
            '  "field_name": [\n'
            '    {"column1": "value1", "column2": "value2"},\n'
            '    {"column1": "value3", "column2": "value4"}\n'
            '  ]\n'
            '}'
        )
        # Use monospace font for better JSON editing
        font = QFont("Consolas", 10)
        font.setStyleHint(QFont.StyleHint.Monospace)
        self.editor.setFont(font)
        self.editor.setTabStopDistance(20)  # 2 spaces worth
        self.editor.setLineWrapMode(CodeEditor.LineWrapMode.NoWrap)
        self.editor.textChanged.connect(self._update_status)
        layout.addWidget(self.editor)

        # Info bar
        info_layout = QHBoxLayout()
        self.line_count_label = QLabel("Lines: 0")
        self.char_count_label = QLabel("Characters: 0")
        info_layout.addWidget(self.line_count_label)
        info_layout.addWidget(self.char_count_label)
        info_layout.addStretch()
        layout.addLayout(info_layout)

        # Dialog buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self._on_accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def _load_data(self):
        """Load initial data into the editor."""
        self.editor.setPlainText(self._data)
        self._update_status()

    def _update_status(self):
        """Update line and character count."""
        text = self.editor.toPlainText()
        lines = text.count('\n') + (1 if text else 0)
        chars = len(text)
        self.line_count_label.setText(f"Lines: {lines}")
        self.char_count_label.setText(f"Characters: {chars}")

    def _format_json(self):
        """Format JSON with proper indentation."""
        text = self.editor.toPlainText().strip()
        if not text:
            return

        try:
            data = json.loads(text)
            formatted = json.dumps(data, indent=2, ensure_ascii=False)
            self.editor.setPlainText(formatted)
            self.status_label.setText("✓ Formatted")
            self.status_label.setStyleSheet("color: green;")
        except json.JSONDecodeError as e:
            self.status_label.setText(f"✗ Invalid JSON: {e.msg}")
            self.status_label.setStyleSheet("color: red;")
            # Try to position cursor at error location
            self._highlight_error(e.lineno, e.colno)

    def _validate_json(self):
        """Validate JSON syntax."""
        text = self.editor.toPlainText().strip()
        if not text:
            self.status_label.setText("Empty")
            self.status_label.setStyleSheet("color: gray;")
            return

        try:
            json.loads(text)
            self.status_label.setText("✓ Valid JSON")
            self.status_label.setStyleSheet("color: green;")
        except json.JSONDecodeError as e:
            self.status_label.setText(f"✗ Line {e.lineno}: {e.msg}")
            self.status_label.setStyleSheet("color: red;")
            self._highlight_error(e.lineno, e.colno)

    def _minify_json(self):
        """Remove whitespace from JSON."""
        text = self.editor.toPlainText().strip()
        if not text:
            return

        try:
            data = json.loads(text)
            minified = json.dumps(data, separators=(',', ':'), ensure_ascii=False)
            self.editor.setPlainText(minified)
            self.status_label.setText("✓ Minified")
            self.status_label.setStyleSheet("color: green;")
        except json.JSONDecodeError as e:
            self.status_label.setText(f"✗ Invalid JSON: {e.msg}")
            self.status_label.setStyleSheet("color: red;")

    def _highlight_error(self, line: int, col: int):
        """Move cursor to error location."""
        cursor = self.editor.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.Start)
        for _ in range(line - 1):
            cursor.movePosition(QTextCursor.MoveOperation.NextBlock)
        cursor.movePosition(QTextCursor.MoveOperation.Right, QTextCursor.MoveMode.MoveAnchor, col - 1)
        self.editor.setTextCursor(cursor)
        self.editor.setFocus()

    def _on_accept(self):
        """Validate JSON before accepting."""
        text = self.editor.toPlainText().strip()
        if text:
            try:
                json.loads(text)
            except json.JSONDecodeError as e:
                result = QMessageBox.warning(
                    self,
                    "Invalid JSON",
                    f"The JSON data is invalid:\n{e.msg} at line {e.lineno}\n\n"
                    "Do you want to save anyway?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No
                )
                if result == QMessageBox.StandardButton.No:
                    self._highlight_error(e.lineno, e.colno)
                    return
        self.accept()

    def get_data(self) -> str:
        """Get the edited data."""
        return self.editor.toPlainText()
