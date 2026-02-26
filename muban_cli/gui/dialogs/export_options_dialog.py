"""
Export Options Dialog - Configure PDF, HTML, and TXT export options.
"""

from typing import Optional, Dict, Any, List

from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
    QTabWidget,
    QWidget,
    QLineEdit,
    QComboBox,
    QCheckBox,
    QDialogButtonBox,
    QGroupBox,
    QDoubleSpinBox,
    QSpinBox,
)


class ExportOptionsDialog(QDialog):
    """Dialog for configuring PDF, HTML, and TXT export options."""

    def __init__(
        self,
        parent=None,
        pdf_options: Optional[Dict[str, Any]] = None,
        html_options: Optional[Dict[str, Any]] = None,
        txt_options: Optional[Dict[str, Any]] = None,
        icc_profiles: Optional[List[str]] = None,
    ):
        super().__init__(parent)
        self._pdf_options = pdf_options or {}
        self._html_options = html_options or {}
        self._txt_options = txt_options or {}
        self._icc_profiles = icc_profiles or []
        self.setWindowTitle("Export Options")
        self.setMinimumWidth(500)
        self._setup_ui()
        self._load_values()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        # Tab widget
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        # PDF Tab
        pdf_widget = QWidget()
        pdf_layout = QVBoxLayout(pdf_widget)
        
        # PDF/A & ICC Group
        archive_group = QGroupBox("Archival & Color")
        archive_layout = QFormLayout(archive_group)
        
        self.pdfa_combo = QComboBox()
        self.pdfa_combo.addItems(["", "PDF/A-1b"])
        self.pdfa_combo.setToolTip("PDF/A conformance level for archival. Note: PDF/A and encryption are mutually exclusive.")
        archive_layout.addRow("PDF/A Conformance:", self.pdfa_combo)

        self.icc_combo = QComboBox()
        self.icc_combo.addItem("")
        for profile in self._icc_profiles:
            self.icc_combo.addItem(profile)
        self.icc_combo.setToolTip("ICC color profile for CMYK color management in professional printing.")
        archive_layout.addRow("ICC Profile:", self.icc_combo)
        pdf_layout.addWidget(archive_group)

        # Security Group
        security_group = QGroupBox("Security")
        security_layout = QFormLayout(security_group)

        self.pdf_user_password = QLineEdit()
        self.pdf_user_password.setEchoMode(QLineEdit.EchoMode.Password)
        self.pdf_user_password.setPlaceholderText("Password to open document")
        security_layout.addRow("User Password:", self.pdf_user_password)

        self.pdf_owner_password = QLineEdit()
        self.pdf_owner_password.setEchoMode(QLineEdit.EchoMode.Password)
        self.pdf_owner_password.setPlaceholderText("Password for permissions")
        security_layout.addRow("Owner Password:", self.pdf_owner_password)

        self.pdf_encryption_combo = QComboBox()
        self.pdf_encryption_combo.addItems(["128", "256"])
        self.pdf_encryption_combo.setToolTip("Encryption key length: 128-bit (compatible) or 256-bit (more secure)")
        security_layout.addRow("Encryption (bits):", self.pdf_encryption_combo)
        pdf_layout.addWidget(security_group)

        # Permissions Group
        perms_group = QGroupBox("Permissions (when password is set)")
        perms_layout = QVBoxLayout(perms_group)

        perms_row1 = QHBoxLayout()
        self.pdf_can_print = QCheckBox("Print")
        self.pdf_can_print.setChecked(True)
        self.pdf_can_print.setToolTip("Allow printing of the document")
        perms_row1.addWidget(self.pdf_can_print)

        self.pdf_can_copy = QCheckBox("Copy")
        self.pdf_can_copy.setChecked(True)
        self.pdf_can_copy.setToolTip("Allow copying text and graphics")
        perms_row1.addWidget(self.pdf_can_copy)

        self.pdf_can_modify = QCheckBox("Modify")
        self.pdf_can_modify.setChecked(False)
        self.pdf_can_modify.setToolTip("Allow modifying document content")
        perms_row1.addWidget(self.pdf_can_modify)

        self.pdf_can_annotate = QCheckBox("Annotate")
        self.pdf_can_annotate.setChecked(True)
        self.pdf_can_annotate.setToolTip("Allow adding annotations and comments")
        perms_row1.addWidget(self.pdf_can_annotate)
        perms_row1.addStretch()
        perms_layout.addLayout(perms_row1)

        perms_row2 = QHBoxLayout()
        self.pdf_can_fill_forms = QCheckBox("Fill Forms")
        self.pdf_can_fill_forms.setChecked(True)
        self.pdf_can_fill_forms.setToolTip("Allow filling form fields")
        perms_row2.addWidget(self.pdf_can_fill_forms)

        self.pdf_can_assemble = QCheckBox("Assemble")
        self.pdf_can_assemble.setChecked(False)
        self.pdf_can_assemble.setToolTip("Allow document assembly (insert/delete pages)")
        perms_row2.addWidget(self.pdf_can_assemble)

        self.pdf_high_quality_print = QCheckBox("High Quality Print")
        self.pdf_high_quality_print.setChecked(True)
        self.pdf_high_quality_print.setToolTip("Allow high-resolution printing")
        perms_row2.addWidget(self.pdf_high_quality_print)
        perms_row2.addStretch()
        perms_layout.addLayout(perms_row2)
        pdf_layout.addWidget(perms_group)

        pdf_layout.addStretch()
        self.tabs.addTab(pdf_widget, "PDF")

        # HTML Tab
        html_widget = QWidget()
        html_layout = QVBoxLayout(html_widget)

        embed_group = QGroupBox("Embedding")
        embed_layout = QHBoxLayout(embed_group)
        
        self.html_embed_fonts = QCheckBox("Embed Fonts")
        self.html_embed_fonts.setChecked(True)
        self.html_embed_fonts.setToolTip("Embed fonts in HTML. Disable for email to reduce size.")
        embed_layout.addWidget(self.html_embed_fonts)

        self.html_embed_images = QCheckBox("Embed Images")
        self.html_embed_images.setChecked(True)
        self.html_embed_images.setToolTip("Embed images directly in HTML")
        embed_layout.addWidget(self.html_embed_images)

        self.html_web_safe_fonts = QCheckBox("Web-Safe Fonts")
        self.html_web_safe_fonts.setChecked(False)
        self.html_web_safe_fonts.setToolTip("Use web-safe font fallbacks (Arial, Times, etc.)")
        embed_layout.addWidget(self.html_web_safe_fonts)
        embed_layout.addStretch()
        html_layout.addWidget(embed_group)

        layout_group = QGroupBox("Layout")
        layout_layout = QHBoxLayout(layout_group)

        self.html_remove_empty_space = QCheckBox("Remove Empty Space")
        self.html_remove_empty_space.setChecked(False)
        self.html_remove_empty_space.setToolTip("Remove empty space between rows for compact output")
        layout_layout.addWidget(self.html_remove_empty_space)

        self.html_wrap_break_word = QCheckBox("Wrap Text")
        self.html_wrap_break_word.setChecked(False)
        self.html_wrap_break_word.setToolTip("Wrap text at word boundaries")
        layout_layout.addWidget(self.html_wrap_break_word)

        self.html_ignore_margins = QCheckBox("Ignore Page Margins")
        self.html_ignore_margins.setChecked(False)
        self.html_ignore_margins.setToolTip("Ignore page margins for responsive output")
        layout_layout.addWidget(self.html_ignore_margins)
        layout_layout.addStretch()
        html_layout.addWidget(layout_group)

        html_layout.addStretch()
        self.tabs.addTab(html_widget, "HTML")

        # TXT Tab
        txt_widget = QWidget()
        txt_layout = QVBoxLayout(txt_widget)

        # Character Grid Group
        grid_group = QGroupBox("Character Grid")
        grid_layout = QFormLayout(grid_group)

        self.txt_char_width = QDoubleSpinBox()
        self.txt_char_width.setRange(0.1, 100.0)
        self.txt_char_width.setDecimals(3)
        self.txt_char_width.setValue(8.0)
        self.txt_char_width.setSpecialValueText("")
        self.txt_char_width.setToolTip(
            "Width of a single character cell in pixels. "
            "Smaller values produce wider output."
        )
        grid_layout.addRow("Character Width (px):", self.txt_char_width)

        self.txt_char_height = QDoubleSpinBox()
        self.txt_char_height.setRange(0.1, 100.0)
        self.txt_char_height.setDecimals(3)
        self.txt_char_height.setValue(13.948)
        self.txt_char_height.setSpecialValueText("")
        self.txt_char_height.setToolTip(
            "Height of a single character cell in pixels. "
            "Smaller values produce taller output."
        )
        grid_layout.addRow("Character Height (px):", self.txt_char_height)
        txt_layout.addWidget(grid_group)

        # Page Size Group
        page_group = QGroupBox("Page Size (in characters)")
        page_layout = QFormLayout(page_group)

        self.txt_page_width = QSpinBox()
        self.txt_page_width.setRange(0, 10000)
        self.txt_page_width.setSpecialValueText("Auto")
        self.txt_page_width.setValue(0)
        self.txt_page_width.setToolTip(
            "Page width in characters. When set, character width is computed "
            "automatically. Set to 0 for auto."
        )
        page_layout.addRow("Page Width (chars):", self.txt_page_width)

        self.txt_page_height = QSpinBox()
        self.txt_page_height.setRange(0, 10000)
        self.txt_page_height.setSpecialValueText("Auto")
        self.txt_page_height.setValue(0)
        self.txt_page_height.setToolTip(
            "Page height in character rows. When set, character height is "
            "computed automatically. Set to 0 for auto."
        )
        page_layout.addRow("Page Height (rows):", self.txt_page_height)
        txt_layout.addWidget(page_group)

        # Formatting Group
        fmt_group = QGroupBox("Formatting")
        fmt_layout = QVBoxLayout(fmt_group)

        fmt_row = QHBoxLayout()
        self.txt_trim_line_right = QCheckBox("Trim Trailing Whitespace")
        self.txt_trim_line_right.setChecked(False)
        self.txt_trim_line_right.setToolTip(
            "Trim trailing whitespace from each line. Reduces file size for sparse reports."
        )
        fmt_row.addWidget(self.txt_trim_line_right)
        fmt_row.addStretch()
        fmt_layout.addLayout(fmt_row)

        sep_form = QFormLayout()
        self.txt_line_separator = QLineEdit()
        self.txt_line_separator.setPlaceholderText("System default")
        self.txt_line_separator.setToolTip("Line separator string (e.g., \\n). Leave empty for system default.")
        sep_form.addRow("Line Separator:", self.txt_line_separator)

        self.txt_page_separator = QLineEdit()
        self.txt_page_separator.setPlaceholderText("None")
        self.txt_page_separator.setToolTip("String inserted between pages (e.g., --- Page Break ---).")
        sep_form.addRow("Page Separator:", self.txt_page_separator)
        fmt_layout.addLayout(sep_form)
        txt_layout.addWidget(fmt_group)

        txt_layout.addStretch()
        self.tabs.addTab(txt_widget, "TXT")

        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _load_values(self):
        """Load values from stored options."""
        # PDF options
        pdf = self._pdf_options
        if pdf.get("pdfaConformance"):
            idx = self.pdfa_combo.findText(pdf["pdfaConformance"])
            if idx >= 0:
                self.pdfa_combo.setCurrentIndex(idx)
        if pdf.get("iccProfile"):
            idx = self.icc_combo.findText(pdf["iccProfile"])
            if idx >= 0:
                self.icc_combo.setCurrentIndex(idx)
        if pdf.get("userPassword"):
            self.pdf_user_password.setText(pdf["userPassword"])
        if pdf.get("ownerPassword"):
            self.pdf_owner_password.setText(pdf["ownerPassword"])
        if pdf.get("encryptionKeyLength"):
            idx = self.pdf_encryption_combo.findText(str(pdf["encryptionKeyLength"]))
            if idx >= 0:
                self.pdf_encryption_combo.setCurrentIndex(idx)
        # Permissions
        if "canPrint" in pdf:
            self.pdf_can_print.setChecked(pdf["canPrint"])
        if "canCopy" in pdf:
            self.pdf_can_copy.setChecked(pdf["canCopy"])
        if "canModify" in pdf:
            self.pdf_can_modify.setChecked(pdf["canModify"])
        if "canAnnotate" in pdf:
            self.pdf_can_annotate.setChecked(pdf["canAnnotate"])
        if "canFillForms" in pdf:
            self.pdf_can_fill_forms.setChecked(pdf["canFillForms"])
        if "canAssemble" in pdf:
            self.pdf_can_assemble.setChecked(pdf["canAssemble"])
        if "canPrintHighQuality" in pdf:
            self.pdf_high_quality_print.setChecked(pdf["canPrintHighQuality"])

        # HTML options
        html = self._html_options
        if "embedFonts" in html:
            self.html_embed_fonts.setChecked(html["embedFonts"])
        if "embedImages" in html:
            self.html_embed_images.setChecked(html["embedImages"])
        if "useWebSafeFonts" in html:
            self.html_web_safe_fonts.setChecked(html["useWebSafeFonts"])
        if "removeEmptySpace" in html:
            self.html_remove_empty_space.setChecked(html["removeEmptySpace"])
        if "wrapBreakWord" in html:
            self.html_wrap_break_word.setChecked(html["wrapBreakWord"])
        if "ignorePageMargins" in html:
            self.html_ignore_margins.setChecked(html["ignorePageMargins"])

        # TXT options
        txt = self._txt_options
        if "characterWidth" in txt:
            self.txt_char_width.setValue(txt["characterWidth"])
        if "characterHeight" in txt:
            self.txt_char_height.setValue(txt["characterHeight"])
        if txt.get("pageWidthInChars"):
            self.txt_page_width.setValue(txt["pageWidthInChars"])
        if txt.get("pageHeightInChars"):
            self.txt_page_height.setValue(txt["pageHeightInChars"])
        if "trimLineRight" in txt:
            self.txt_trim_line_right.setChecked(txt["trimLineRight"])
        if txt.get("lineSeparator"):
            self.txt_line_separator.setText(txt["lineSeparator"])
        if txt.get("pageSeparator"):
            self.txt_page_separator.setText(txt["pageSeparator"])

    def update_icc_profiles(self, profiles: List[str]):
        """Update ICC profiles list."""
        current = self.icc_combo.currentText()
        self.icc_combo.clear()
        self.icc_combo.addItem("")
        for profile in profiles:
            self.icc_combo.addItem(profile)
        # Restore selection if still available
        if current:
            idx = self.icc_combo.findText(current)
            if idx >= 0:
                self.icc_combo.setCurrentIndex(idx)

    def get_pdf_options(self) -> Optional[Dict[str, Any]]:
        """Get PDF export options."""
        options: Dict[str, Any] = {}

        pdfa = self.pdfa_combo.currentText()
        if pdfa:
            options["pdfaConformance"] = pdfa

        icc = self.icc_combo.currentText()
        if icc:
            options["iccProfile"] = icc

        user_pwd = self.pdf_user_password.text()
        if user_pwd:
            options["userPassword"] = user_pwd

        owner_pwd = self.pdf_owner_password.text()
        if owner_pwd:
            options["ownerPassword"] = owner_pwd

        if user_pwd or owner_pwd:
            options["canPrint"] = self.pdf_can_print.isChecked()
            options["canPrintHighQuality"] = self.pdf_high_quality_print.isChecked()
            options["canModify"] = self.pdf_can_modify.isChecked()
            options["canCopy"] = self.pdf_can_copy.isChecked()
            options["canFillForms"] = self.pdf_can_fill_forms.isChecked()
            options["canAnnotate"] = self.pdf_can_annotate.isChecked()
            options["canAssemble"] = self.pdf_can_assemble.isChecked()
            options["encryptionKeyLength"] = int(self.pdf_encryption_combo.currentText())

        return options if options else None

    def get_html_options(self) -> Optional[Dict[str, Any]]:
        """Get HTML export options."""
        return {
            "embedFonts": self.html_embed_fonts.isChecked(),
            "embedImages": self.html_embed_images.isChecked(),
            "useWebSafeFonts": self.html_web_safe_fonts.isChecked(),
            "removeEmptySpace": self.html_remove_empty_space.isChecked(),
            "wrapBreakWord": self.html_wrap_break_word.isChecked(),
            "ignorePageMargins": self.html_ignore_margins.isChecked(),
        }

    def get_pdf_summary(self) -> str:
        """Get a brief summary of PDF options."""
        parts = []
        if self.pdfa_combo.currentText():
            parts.append(self.pdfa_combo.currentText())
        if self.icc_combo.currentText():
            parts.append(f"ICC: {self.icc_combo.currentText()}")
        if self.pdf_user_password.text() or self.pdf_owner_password.text():
            parts.append("Encrypted")
        return ", ".join(parts) if parts else "Default"

    def get_html_summary(self) -> str:
        """Get a brief summary of HTML options."""
        parts = []
        if not self.html_embed_fonts.isChecked():
            parts.append("No fonts")
        if not self.html_embed_images.isChecked():
            parts.append("No images")
        if self.html_web_safe_fonts.isChecked():
            parts.append("Web-safe")
        if self.html_remove_empty_space.isChecked():
            parts.append("Compact")
        return ", ".join(parts) if parts else "Default"

    def get_txt_options(self) -> Optional[Dict[str, Any]]:
        """Get TXT export options."""
        options: Dict[str, Any] = {}

        char_w = self.txt_char_width.value()
        if char_w != 8.0:
            options["characterWidth"] = char_w

        char_h = self.txt_char_height.value()
        if char_h != 13.948:
            options["characterHeight"] = char_h

        page_w = self.txt_page_width.value()
        if page_w > 0:
            options["pageWidthInChars"] = page_w

        page_h = self.txt_page_height.value()
        if page_h > 0:
            options["pageHeightInChars"] = page_h

        if self.txt_trim_line_right.isChecked():
            options["trimLineRight"] = True

        line_sep = self.txt_line_separator.text()
        if line_sep:
            options["lineSeparator"] = line_sep

        page_sep = self.txt_page_separator.text()
        if page_sep:
            options["pageSeparator"] = page_sep

        return options if options else None

    def get_txt_summary(self) -> str:
        """Get a brief summary of TXT options."""
        parts = []
        if self.txt_page_width.value() > 0:
            parts.append(f"{self.txt_page_width.value()} cols")
        if self.txt_page_height.value() > 0:
            parts.append(f"{self.txt_page_height.value()} rows")
        if self.txt_char_width.value() != 8.0:
            parts.append(f"W:{self.txt_char_width.value()}")
        if self.txt_char_height.value() != 13.948:
            parts.append(f"H:{self.txt_char_height.value()}")
        if self.txt_trim_line_right.isChecked():
            parts.append("Trim")
        return ", ".join(parts) if parts else "Default"
