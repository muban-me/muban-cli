"""
Custom error dialog with copy functionality for correlation IDs.
"""

import re
from typing import Optional

from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QApplication,
    QWidget,
    QStyle,
)
from PyQt6.QtCore import Qt


class ErrorDialog(QDialog):
    """
    Error dialog that displays error messages with copy functionality.
    
    Automatically extracts and highlights correlation IDs for easy copying
    to support tickets.
    """
    
    # Pattern to match correlation ID in error messages
    CORRELATION_ID_PATTERN = re.compile(r'\(Correlation ID: ([a-f0-9-]+)\)', re.IGNORECASE)
    
    def __init__(
        self,
        parent: Optional[QWidget],
        title: str,
        message: str,
        is_critical: bool = True
    ):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.message = message
        self.correlation_id = self._extract_correlation_id(message)
        
        self._setup_ui(is_critical)
        self.setMinimumWidth(450)
        
    def _extract_correlation_id(self, message: str) -> Optional[str]:
        """Extract correlation ID from error message."""
        match = self.CORRELATION_ID_PATTERN.search(message)
        return match.group(1) if match else None
    
    def _setup_ui(self, is_critical: bool):
        """Set up the dialog UI."""
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        
        # Icon and message row
        message_layout = QHBoxLayout()
        message_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        # Use Qt standard icons for cross-platform consistency
        icon_label = QLabel()
        style = self.style()
        if style:
            icon_type = (
                QStyle.StandardPixmap.SP_MessageBoxCritical 
                if is_critical 
                else QStyle.StandardPixmap.SP_MessageBoxWarning
            )
            icon = style.standardIcon(icon_type)
            icon_label.setPixmap(icon.pixmap(32, 32))
        message_layout.addWidget(icon_label)
        
        # Error message as label (word-wrapped)
        message_label = QLabel(self.message)
        message_label.setWordWrap(True)
        message_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        message_layout.addWidget(message_label, 1)  # stretch factor 1
        
        layout.addLayout(message_layout)
        
        # Correlation ID section (if present)
        if self.correlation_id:
            corr_layout = QHBoxLayout()
            
            corr_label = QLabel(f"<b>Correlation ID:</b> {self.correlation_id}")
            corr_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            corr_layout.addWidget(corr_label)
            
            copy_id_btn = QPushButton("Copy ID")
            copy_id_btn.setMaximumWidth(80)
            copy_id_btn.clicked.connect(self._copy_correlation_id)
            copy_id_btn.setToolTip("Copy correlation ID for support ticket")
            corr_layout.addWidget(copy_id_btn)
            
            layout.addLayout(corr_layout)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        copy_all_btn = QPushButton("Copy All")
        copy_all_btn.clicked.connect(self._copy_all)
        copy_all_btn.setToolTip("Copy full error message")
        button_layout.addWidget(copy_all_btn)
        
        button_layout.addStretch()
        
        ok_btn = QPushButton("OK")
        ok_btn.setDefault(True)
        ok_btn.clicked.connect(self.accept)
        button_layout.addWidget(ok_btn)
        
        layout.addLayout(button_layout)
    
    def _copy_correlation_id(self):
        """Copy only the correlation ID to clipboard."""
        if self.correlation_id:
            clipboard = QApplication.clipboard()
            if clipboard:
                clipboard.setText(self.correlation_id)
    
    def _copy_all(self):
        """Copy the full error message to clipboard."""
        clipboard = QApplication.clipboard()
        if clipboard:
            clipboard.setText(self.message)


def show_error_dialog(
    parent: Optional[QWidget],
    title: str,
    message: str,
    is_critical: bool = True
) -> None:
    """
    Show an error dialog with copy functionality.
    
    Args:
        parent: Parent widget
        title: Dialog title
        message: Error message (may contain correlation ID)
        is_critical: True for critical error (red), False for warning (yellow)
    """
    dialog = ErrorDialog(parent, title, message, is_critical)
    dialog.exec()
