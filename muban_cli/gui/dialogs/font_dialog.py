"""
Font Dialog - Add/edit font configuration.
"""

from pathlib import Path

from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QFormLayout,
    QLineEdit,
    QComboBox,
    QCheckBox,
    QDialogButtonBox,
    QLabel,
)

from muban_cli.packager import FontSpec


class FontDialog(QDialog):
    """Dialog for configuring a font."""

    def __init__(self, file_path: str, parent=None):
        super().__init__(parent)
        self.file_path = Path(file_path)
        self.setWindowTitle("Add Font")
        self.setMinimumWidth(400)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        # File info
        file_label = QLabel(f"<b>File:</b> {self.file_path.name}")
        layout.addWidget(file_label)

        # Form
        form = QFormLayout()

        # Font name
        self.name_input = QLineEdit()
        # Try to guess font name from filename
        guessed_name = self.file_path.stem.replace("-", " ").replace("_", " ")
        # Remove common suffixes
        for suffix in ["Regular", "Bold", "Italic", "BoldItalic", "Light", "Medium"]:
            guessed_name = guessed_name.replace(suffix, "").strip()
        self.name_input.setText(guessed_name or self.file_path.stem)
        form.addRow("Font Name:", self.name_input)

        # Font face
        self.face_combo = QComboBox()
        self.face_combo.addItems(["normal", "bold", "italic", "boldItalic"])
        # Try to guess face from filename
        filename_lower = self.file_path.stem.lower()
        if "bolditalic" in filename_lower or "bold_italic" in filename_lower:
            self.face_combo.setCurrentText("boldItalic")
        elif "bold" in filename_lower:
            self.face_combo.setCurrentText("bold")
        elif "italic" in filename_lower:
            self.face_combo.setCurrentText("italic")
        form.addRow("Face:", self.face_combo)

        # Embedded
        self.embedded_cb = QCheckBox("Embed font in PDF")
        self.embedded_cb.setChecked(True)
        form.addRow("", self.embedded_cb)

        layout.addLayout(form)

        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_font_spec(self) -> FontSpec:
        """Get the configured FontSpec."""
        return FontSpec(
            file_path=self.file_path,
            name=self.name_input.text().strip(),
            face=self.face_combo.currentText(),
            embedded=self.embedded_cb.isChecked(),
        )
