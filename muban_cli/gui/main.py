"""
Muban GUI - Main entry point.

Usage:
    muban-gui

Or as module:
    python -m muban_cli.gui
"""

import sys


def main():
    """Launch the Muban GUI application."""
    try:
        from PyQt6.QtWidgets import QApplication
    except ImportError:
        print("Error: PyQt6 is required for the GUI.", file=sys.stderr)
        print("Install with: pip install muban-cli[gui]", file=sys.stderr)
        sys.exit(1)

    from muban_cli.gui.main_window import MubanMainWindow

    app = QApplication(sys.argv)
    app.setApplicationName("Muban")
    app.setOrganizationName("Muban")
    app.setOrganizationDomain("muban.me")

    window = MubanMainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
