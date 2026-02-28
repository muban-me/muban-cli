"""
Muban GUI - Main entry point.

Usage:
    muban-gui
    muban-gui --debug

Or as module:
    python -m muban_cli.gui
"""

import argparse
import logging
import sys
from pathlib import Path


def main():
    """Launch the Muban GUI application."""
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Muban GUI - Document Generation")
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug mode (logs full request bodies to ~/.muban/debug.log)"
    )
    args = parser.parse_args()
    
    # Configure logging based on debug flag
    if args.debug:
        # Write to file in .muban config directory (console doesn't work on Windows GUI)
        config_dir = Path.home() / ".muban"
        config_dir.mkdir(exist_ok=True)
        log_file = config_dir / "debug.log"
        
        # Set up file handler explicitly (basicConfig doesn't always work)
        file_handler = logging.FileHandler(str(log_file), mode="w", encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        ))
        
        # Add handler to root logger and set level
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.DEBUG)
        root_logger.addHandler(file_handler)
        
        # Also ensure muban_cli logger is at DEBUG level
        logging.getLogger("muban_cli").setLevel(logging.DEBUG)
        logging.getLogger("muban_cli").info("Debug mode enabled - logging to %s", log_file)
        
        # Also print to console where it works
        print(f"Debug mode enabled - logs written to: {log_file}")
    
    try:
        from PyQt6.QtWidgets import QApplication
        from PyQt6.QtGui import QIcon
    except ImportError:
        print("Error: PyQt6 is required for the GUI.", file=sys.stderr)
        print("Install with: pip install muban-cli[gui]", file=sys.stderr)
        sys.exit(1)

    from muban_cli.gui.main_window import MubanMainWindow

    app = QApplication(sys.argv)
    app.setStyle("Fusion")  # Disabled for comparison - cross-platform style
    app.setApplicationName("Muban")
    app.setOrganizationName("Muban")
    app.setOrganizationDomain("muban.me")

    # Set application icon
    icon_path = Path(__file__).parent / "resources" / "logo.png"
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))

    window = MubanMainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
