"""
Font Dialog - Add/edit font configuration.

Supports selecting multiple font faces for a single font file,
so users don't have to add the same file repeatedly.
"""

from pathlib import Path
from typing import List

from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
    QLineEdit,
    QCheckBox,
    QDialogButtonBox,
    QGroupBox,
    QLabel,
    QMessageBox,
)

from muban_cli.packager import FontSpec

# Supported JasperReports font faces
FONT_FACES = ["normal", "bold", "italic", "boldItalic"]

FACE_LABELS = {
    "normal": "Normal",
    "bold": "Bold",
    "italic": "Italic",
    "boldItalic": "Bold Italic",
}


class FontDialog(QDialog):
    """Dialog for configuring a font with multi-face selection."""

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

        layout.addLayout(form)

        # Font faces - multi-select checkboxes
        faces_group = QGroupBox("Font Faces")
        faces_layout = QHBoxLayout(faces_group)
        self.face_checkboxes: dict[str, QCheckBox] = {}
        for face in FONT_FACES:
            cb = QCheckBox(FACE_LABELS[face])
            self.face_checkboxes[face] = cb
            faces_layout.addWidget(cb)
        layout.addWidget(faces_group)

        # All faces checked by default (most common use case)
        for cb in self.face_checkboxes.values():
            cb.setChecked(True)

        # Embedded
        embedded_form = QFormLayout()
        self.embedded_cb = QCheckBox("Embed font in PDF")
        self.embedded_cb.setChecked(True)
        embedded_form.addRow("", self.embedded_cb)
        layout.addLayout(embedded_form)

        # Buttons
        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.button_box.accepted.connect(self._validate_and_accept)
        self.button_box.rejected.connect(self.reject)
        layout.addWidget(self.button_box)

    def _validate_and_accept(self):
        """Validate at least one face is selected before accepting."""
        if not self.selected_faces():
            QMessageBox.warning(
                self, "Validation Error", "Please select at least one font face."
            )
            return
        self.accept()

    def selected_faces(self) -> List[str]:
        """Return list of selected face names."""
        return [face for face, cb in self.face_checkboxes.items() if cb.isChecked()]

    def get_font_specs(self) -> List[FontSpec]:
        """Get a FontSpec for each selected face."""
        name = self.name_input.text().strip()
        embedded = self.embedded_cb.isChecked()
        return [
            FontSpec(
                file_path=self.file_path,
                name=name,
                face=face,
                embedded=embedded,
            )
            for face in self.selected_faces()
        ]

    def get_font_spec(self) -> FontSpec:
        """Get a single FontSpec (first selected face). Kept for backward compatibility."""
        specs = self.get_font_specs()
        return specs[0] if specs else FontSpec(
            file_path=self.file_path,
            name=self.name_input.text().strip(),
            face="normal",
            embedded=self.embedded_cb.isChecked(),
        )
