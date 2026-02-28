"""
Upload Dialog - Enter template metadata for upload.
"""

from pathlib import Path

from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
    QLineEdit,
    QTextEdit,
    QDialogButtonBox,
    QLabel,
)


class UploadDialog(QDialog):
    """Dialog for entering template upload metadata."""
    
    MAX_DESCRIPTION_LENGTH = 1000

    def __init__(self, file_path: str, default_author: str = "", parent=None):
        super().__init__(parent)
        self.file_path = Path(file_path)
        self.default_author = default_author
        self.setWindowTitle("Upload Template")
        self.setMinimumWidth(450)
        self.setMinimumHeight(300)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        # File info
        file_label = QLabel(f"<b>File:</b> {self.file_path.name}")
        layout.addWidget(file_label)

        # Form
        form = QFormLayout()

        # Template name
        self.name_input = QLineEdit()
        self.name_input.setText(self.file_path.stem)
        self.name_input.setPlaceholderText("Template display name")
        form.addRow("Name:", self.name_input)

        # Author
        self.author_input = QLineEdit()
        self.author_input.setText(self.default_author)
        self.author_input.setPlaceholderText("Author name (optional)")
        form.addRow("Author:", self.author_input)

        layout.addLayout(form)

        # Description (multi-line text area with counter)
        desc_label = QLabel("Description:")
        layout.addWidget(desc_label)
        
        self.description_input = QTextEdit()
        self.description_input.setPlaceholderText("Human-readable description (optional)")
        self.description_input.setMinimumHeight(80)
        self.description_input.setMaximumHeight(150)
        self.description_input.textChanged.connect(self._on_description_changed)
        layout.addWidget(self.description_input)
        
        # Character counter
        counter_layout = QHBoxLayout()
        counter_layout.addStretch()
        self.char_counter = QLabel(f"0 / {self.MAX_DESCRIPTION_LENGTH}")
        self.char_counter.setStyleSheet("color: gray; font-size: 11px;")
        counter_layout.addWidget(self.char_counter)
        layout.addLayout(counter_layout)

        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
    
    def _on_description_changed(self):
        """Handle description text change - enforce limit and update counter."""
        text = self.description_input.toPlainText()
        length = len(text)
        
        # Enforce max length
        if length > self.MAX_DESCRIPTION_LENGTH:
            # Block signals to avoid recursion
            self.description_input.blockSignals(True)
            cursor = self.description_input.textCursor()
            pos = cursor.position()
            self.description_input.setPlainText(text[:self.MAX_DESCRIPTION_LENGTH])
            # Restore cursor position
            cursor.setPosition(min(pos, self.MAX_DESCRIPTION_LENGTH))
            self.description_input.setTextCursor(cursor)
            self.description_input.blockSignals(False)
            length = self.MAX_DESCRIPTION_LENGTH
        
        # Update counter with color feedback
        self.char_counter.setText(f"{length} / {self.MAX_DESCRIPTION_LENGTH}")
        if length >= self.MAX_DESCRIPTION_LENGTH:
            self.char_counter.setStyleSheet("color: #cc0000; font-size: 11px;")
        elif length > self.MAX_DESCRIPTION_LENGTH * 0.9:
            self.char_counter.setStyleSheet("color: #cc7700; font-size: 11px;")
        else:
            self.char_counter.setStyleSheet("color: gray; font-size: 11px;")

    def get_name(self) -> str:
        """Get the template name."""
        return self.name_input.text().strip()

    def get_author(self) -> str:
        """Get the author name."""
        return self.author_input.text().strip()

    def get_description(self) -> str:
        """Get the template description."""
        return self.description_input.toPlainText().strip()
