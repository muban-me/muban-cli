"""
Upload Dialog - Enter template metadata for upload.
"""

from pathlib import Path

from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QFormLayout,
    QLineEdit,
    QDialogButtonBox,
    QLabel,
)


class UploadDialog(QDialog):
    """Dialog for entering template upload metadata."""

    def __init__(self, file_path: str, parent=None):
        super().__init__(parent)
        self.file_path = Path(file_path)
        self.setWindowTitle("Upload Template")
        self.setMinimumWidth(400)
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
        self.author_input.setPlaceholderText("Author name (optional)")
        form.addRow("Author:", self.author_input)

        layout.addLayout(form)

        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_name(self) -> str:
        """Get the template name."""
        return self.name_input.text().strip()

    def get_author(self) -> str:
        """Get the author name."""
        return self.author_input.text().strip()
