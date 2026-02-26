"""
Tests for GUI components using pytest-qt.

These tests require a display environment. On CI, use xvfb-run or similar.
"""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

# Skip all tests if PyQt6 is not available or display is not available
pytestmark = pytest.mark.skipif(
    not pytest.importorskip("PyQt6", reason="PyQt6 required"),
    reason="PyQt6 not available"
)

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QIcon, QColor


class TestIcons:
    """Tests for custom icon creation functions."""

    def test_get_text_color_returns_qcolor(self, qtbot):
        """Test get_text_color returns a QColor object."""
        from muban_cli.gui.icons import get_text_color
        
        color = get_text_color()
        assert isinstance(color, QColor)
        assert color.isValid()

    def test_create_play_icon(self, qtbot):
        """Test creating a play icon."""
        from muban_cli.gui.icons import create_play_icon
        
        icon = create_play_icon()
        assert isinstance(icon, QIcon)
        assert not icon.isNull()
        
        # Test with custom size
        icon_large = create_play_icon(size=32)
        assert not icon_large.isNull()

    def test_create_arrow_up_icon(self, qtbot):
        """Test creating an up arrow icon."""
        from muban_cli.gui.icons import create_arrow_up_icon
        
        icon = create_arrow_up_icon()
        assert isinstance(icon, QIcon)
        assert not icon.isNull()

    def test_create_arrow_down_icon(self, qtbot):
        """Test creating a down arrow icon."""
        from muban_cli.gui.icons import create_arrow_down_icon
        
        icon = create_arrow_down_icon()
        assert isinstance(icon, QIcon)
        assert not icon.isNull()

    def test_create_arrow_left_icon(self, qtbot):
        """Test creating a left arrow icon."""
        from muban_cli.gui.icons import create_arrow_left_icon
        
        icon = create_arrow_left_icon()
        assert isinstance(icon, QIcon)
        assert not icon.isNull()

    def test_create_arrow_right_icon(self, qtbot):
        """Test creating a right arrow icon."""
        from muban_cli.gui.icons import create_arrow_right_icon
        
        icon = create_arrow_right_icon()
        assert isinstance(icon, QIcon)
        assert not icon.isNull()

    def test_create_login_icon(self, qtbot):
        """Test creating a login icon."""
        from muban_cli.gui.icons import create_login_icon
        
        icon = create_login_icon()
        assert isinstance(icon, QIcon)
        assert not icon.isNull()
        
        # Test with custom size
        icon_small = create_login_icon(size=12)
        assert not icon_small.isNull()

    def test_create_logout_icon(self, qtbot):
        """Test creating a logout icon."""
        from muban_cli.gui.icons import create_logout_icon
        
        icon = create_logout_icon()
        assert isinstance(icon, QIcon)
        assert not icon.isNull()


class TestMainWindow:
    """Tests for the main window widget."""

    @pytest.fixture
    def mock_config_manager(self):
        """Create a mock config manager."""
        with patch('muban_cli.gui.tabs.package_tab.get_config_manager') as mock_pkg, \
             patch('muban_cli.gui.tabs.templates_tab.get_config_manager') as mock_tmpl, \
             patch('muban_cli.gui.tabs.generate_tab.get_config_manager') as mock_gen, \
             patch('muban_cli.gui.tabs.settings_tab.get_config_manager') as mock_settings, \
             patch('muban_cli.gui.tabs.server_info_tab.get_config_manager') as mock_server:
            
            # Create mock config
            mock_config = MagicMock()
            mock_config.token = None
            mock_config.server_url = "https://api.muban.me"
            mock_config.default_author = "Test Author"
            
            manager = MagicMock()
            manager.load.return_value = mock_config
            manager.get.return_value = mock_config
            
            mock_pkg.return_value = manager
            mock_tmpl.return_value = manager
            mock_gen.return_value = manager
            mock_settings.return_value = manager
            mock_server.return_value = manager
            
            yield manager

    def test_main_window_creation(self, qtbot, mock_config_manager):
        """Test main window can be created."""
        from muban_cli.gui.main_window import MubanMainWindow
        
        window = MubanMainWindow()
        qtbot.addWidget(window)
        
        assert window is not None
        assert "muban" in window.windowTitle().lower()

    def test_main_window_has_tabs(self, qtbot, mock_config_manager):
        """Test main window has expected tabs."""
        from muban_cli.gui.main_window import MubanMainWindow
        
        window = MubanMainWindow()
        qtbot.addWidget(window)
        
        assert window.tabs is not None
        assert window.tabs.count() == 5
        
        # Check tab names
        tab_names = [window.tabs.tabText(i) for i in range(window.tabs.count())]
        assert "Package" in tab_names
        assert "Templates" in tab_names
        assert "Generate" in tab_names
        assert "Server Info" in tab_names
        assert "Settings" in tab_names

    def test_main_window_has_menu(self, qtbot, mock_config_manager):
        """Test main window has menu bar."""
        from muban_cli.gui.main_window import MubanMainWindow
        
        window = MubanMainWindow()
        qtbot.addWidget(window)
        
        menubar = window.menuBar()
        assert menubar is not None

    def test_main_window_has_statusbar(self, qtbot, mock_config_manager):
        """Test main window has status bar."""
        from muban_cli.gui.main_window import MubanMainWindow
        
        window = MubanMainWindow()
        qtbot.addWidget(window)
        
        assert window.statusbar is not None

    def test_show_status_message(self, qtbot, mock_config_manager):
        """Test showing status bar message."""
        from muban_cli.gui.main_window import MubanMainWindow
        
        window = MubanMainWindow()
        qtbot.addWidget(window)
        
        window.show_status("Test message", timeout=1000)
        assert window.statusbar.currentMessage() == "Test message"

    def test_window_minimum_size(self, qtbot, mock_config_manager):
        """Test window has minimum size set."""
        from muban_cli.gui.main_window import MubanMainWindow
        
        window = MubanMainWindow()
        qtbot.addWidget(window)
        
        min_size = window.minimumSize()
        assert min_size.width() >= 1000
        assert min_size.height() >= 750


class TestPackageTab:
    """Tests for the Package tab widget."""

    @pytest.fixture
    def mock_config(self):
        """Create mock config for package tab."""
        with patch('muban_cli.gui.tabs.package_tab.get_config_manager') as mock:
            config = MagicMock()
            config.token = None
            config.default_author = "Test Author"
            
            manager = MagicMock()
            manager.load.return_value = config
            manager.get.return_value = config
            mock.return_value = manager
            yield manager

    def test_package_tab_creation(self, qtbot, mock_config):
        """Test package tab can be created."""
        from muban_cli.gui.tabs.package_tab import PackageTab
        
        tab = PackageTab()
        qtbot.addWidget(tab)
        
        assert tab is not None

    def test_package_tab_has_file_input(self, qtbot, mock_config):
        """Test package tab has template file input."""
        from muban_cli.gui.tabs.package_tab import PackageTab
        
        tab = PackageTab()
        qtbot.addWidget(tab)
        
        assert hasattr(tab, 'template_input')
        assert tab.template_input is not None

    def test_package_tab_has_package_button(self, qtbot, mock_config):
        """Test package tab has package button."""
        from muban_cli.gui.tabs.package_tab import PackageTab
        
        tab = PackageTab()
        qtbot.addWidget(tab)
        
        assert hasattr(tab, 'package_btn')
        assert tab.package_btn is not None
        assert "package" in tab.package_btn.text().lower()

    def test_package_tab_has_dry_run_checkbox(self, qtbot, mock_config):
        """Test package tab has dry run checkbox."""
        from muban_cli.gui.tabs.package_tab import PackageTab
        
        tab = PackageTab()
        qtbot.addWidget(tab)
        
        assert hasattr(tab, 'dry_run_cb')
        assert tab.dry_run_cb is not None

    def test_set_template_path(self, qtbot, mock_config, tmp_path):
        """Test setting template path."""
        from muban_cli.gui.tabs.package_tab import PackageTab
        
        tab = PackageTab()
        qtbot.addWidget(tab)
        
        test_path = str(tmp_path / "test.jrxml")
        tab.template_input.setText(test_path)
        
        assert tab.template_input.text() == test_path


class TestPackageWorker:
    """Tests for the PackageWorker thread."""

    def test_package_worker_creation(self, tmp_path):
        """Test PackageWorker can be created."""
        from muban_cli.gui.tabs.package_tab import PackageWorker
        
        jrxml_path = tmp_path / "test.jrxml"
        jrxml_path.write_text('<?xml version="1.0"?><jasperReport/>')
        
        worker = PackageWorker(
            template_path=jrxml_path,
            output_path=None,
            fonts=[],
            reports_dir_param="REPORTS_DIR",
            dry_run=True,
        )
        
        assert worker is not None
        assert worker.template_path == jrxml_path
        assert worker.dry_run is True

    def test_package_worker_with_fonts_xml(self, tmp_path):
        """Test PackageWorker with fonts_xml_path."""
        from muban_cli.gui.tabs.package_tab import PackageWorker
        
        jrxml_path = tmp_path / "test.jrxml"
        jrxml_path.write_text('<?xml version="1.0"?><jasperReport/>')
        
        fonts_xml = tmp_path / "fonts.xml"
        fonts_xml.write_text('<?xml version="1.0"?><fontFamilies/>')
        
        worker = PackageWorker(
            template_path=jrxml_path,
            output_path=None,
            fonts=[],
            reports_dir_param="REPORTS_DIR",
            fonts_xml_path=fonts_xml,
        )
        
        assert worker.fonts_xml_path == fonts_xml


class TestUploadWorker:
    """Tests for the UploadWorker thread."""

    def test_upload_worker_creation(self, tmp_path):
        """Test UploadWorker can be created."""
        from muban_cli.gui.tabs.package_tab import UploadWorker
        
        mock_client = MagicMock()
        file_path = tmp_path / "test.zip"
        file_path.write_bytes(b"PK fake zip")
        
        worker = UploadWorker(
            client=mock_client,
            file_path=file_path,
            name="Test Template",
            author="Test Author",
        )
        
        assert worker is not None
        assert worker.name == "Test Template"
        assert worker.author == "Test Author"


class TestSettingsTab:
    """Tests for the Settings tab widget."""

    @pytest.fixture
    def mock_config(self):
        """Create mock config for settings tab."""
        with patch('muban_cli.gui.tabs.settings_tab.get_config_manager') as mock:
            config = MagicMock()
            config.token = "test-token"
            config.server_url = "https://api.muban.me"
            config.default_author = "Test Author"
            config.timeout = 30
            config.verify_ssl = True
            
            manager = MagicMock()
            manager.load.return_value = config
            manager.get.return_value = config
            mock.return_value = manager
            yield manager

    def test_settings_tab_creation(self, qtbot, mock_config):
        """Test settings tab can be created."""
        from muban_cli.gui.tabs.settings_tab import SettingsTab
        
        tab = SettingsTab()
        qtbot.addWidget(tab)
        
        assert tab is not None

    def test_settings_tab_has_server_url_input(self, qtbot, mock_config):
        """Test settings tab has server URL input."""
        from muban_cli.gui.tabs.settings_tab import SettingsTab
        
        tab = SettingsTab()
        qtbot.addWidget(tab)
        
        assert hasattr(tab, 'server_url_input')
        assert tab.server_url_input is not None


class TestTemplatesTab:
    """Tests for the Templates tab widget."""

    @pytest.fixture
    def mock_config(self):
        """Create mock config for templates tab."""
        with patch('muban_cli.gui.tabs.templates_tab.get_config_manager') as mock:
            config = MagicMock()
            config.token = "test-token"
            config.server_url = "https://api.muban.me"
            
            manager = MagicMock()
            manager.load.return_value = config
            manager.get.return_value = config
            mock.return_value = manager
            yield manager

    def test_templates_tab_creation(self, qtbot, mock_config):
        """Test templates tab can be created."""
        from muban_cli.gui.tabs.templates_tab import TemplatesTab
        
        tab = TemplatesTab()
        qtbot.addWidget(tab)
        
        assert tab is not None

    def test_templates_tab_has_table(self, qtbot, mock_config):
        """Test templates tab has templates table."""
        from muban_cli.gui.tabs.templates_tab import TemplatesTab
        
        tab = TemplatesTab()
        qtbot.addWidget(tab)
        
        assert hasattr(tab, 'table')
        assert tab.table is not None


class TestGenerateTab:
    """Tests for the Generate tab widget."""

    @pytest.fixture
    def mock_config(self):
        """Create mock config for generate tab."""
        with patch('muban_cli.gui.tabs.generate_tab.get_config_manager') as mock:
            config = MagicMock()
            config.token = "test-token"
            config.server_url = "https://api.muban.me"
            
            manager = MagicMock()
            manager.load.return_value = config
            manager.get.return_value = config
            mock.return_value = manager
            yield manager

    def test_generate_tab_creation(self, qtbot, mock_config):
        """Test generate tab can be created."""
        from muban_cli.gui.tabs.generate_tab import GenerateTab
        
        tab = GenerateTab()
        qtbot.addWidget(tab)
        
        assert tab is not None


class TestServerInfoTab:
    """Tests for the Server Info tab widget."""

    @pytest.fixture
    def mock_config(self):
        """Create mock config for server info tab."""
        with patch('muban_cli.gui.tabs.server_info_tab.get_config_manager') as mock:
            config = MagicMock()
            config.token = "test-token"
            config.server_url = "https://api.muban.me"
            
            manager = MagicMock()
            manager.load.return_value = config
            manager.get.return_value = config
            mock.return_value = manager
            yield manager

    def test_server_info_tab_creation(self, qtbot, mock_config):
        """Test server info tab can be created."""
        from muban_cli.gui.tabs.server_info_tab import ServerInfoTab
        
        tab = ServerInfoTab()
        qtbot.addWidget(tab)
        
        assert tab is not None


class TestFontDialog:
    """Tests for the Font dialog."""

    def test_font_dialog_creation(self, qtbot, tmp_path):
        """Test font dialog can be created."""
        from muban_cli.gui.dialogs.font_dialog import FontDialog
        
        font_file = tmp_path / "TestFont-Regular.ttf"
        font_file.write_bytes(b"fake font")
        
        dialog = FontDialog(str(font_file))
        qtbot.addWidget(dialog)
        
        assert dialog is not None
        assert dialog.file_path == font_file

    def test_font_dialog_has_buttons(self, qtbot, tmp_path):
        """Test font dialog has OK/Cancel buttons."""
        from muban_cli.gui.dialogs.font_dialog import FontDialog
        
        font_file = tmp_path / "TestFont-Bold.ttf"
        font_file.write_bytes(b"fake font")
        
        dialog = FontDialog(str(font_file))
        qtbot.addWidget(dialog)
        
        # Dialog should have a title and form fields
        assert dialog.windowTitle() == "Add Font"
        assert hasattr(dialog, 'name_input')
        assert hasattr(dialog, 'face_checkboxes')
    
    def test_font_dialog_all_faces_checked_by_default(self, qtbot, tmp_path):
        """Test all font faces are checked by default."""
        from muban_cli.gui.dialogs.font_dialog import FontDialog

        font_file = tmp_path / "MyFont.ttf"
        font_file.write_bytes(b"fake font")

        dialog = FontDialog(str(font_file))
        qtbot.addWidget(dialog)

        assert dialog.face_checkboxes["normal"].isChecked()
        assert dialog.face_checkboxes["bold"].isChecked()
        assert dialog.face_checkboxes["italic"].isChecked()
        assert dialog.face_checkboxes["boldItalic"].isChecked()

    def test_font_dialog_get_font_spec(self, qtbot, tmp_path):
        """Test getting FontSpec from dialog (backward compat)."""
        from muban_cli.gui.dialogs.font_dialog import FontDialog
        
        font_file = tmp_path / "TestFont.ttf"
        font_file.write_bytes(b"fake font")
        
        dialog = FontDialog(str(font_file))
        qtbot.addWidget(dialog)
        
        dialog.name_input.setText("Test Font")
        # normal is already checked by default for this filename
        dialog.embedded_cb.setChecked(True)
        
        spec = dialog.get_font_spec()
        assert spec.name == "Test Font"
        assert spec.face == "normal"
        assert spec.embedded is True

    def test_font_dialog_multi_face_selection(self, qtbot, tmp_path):
        """Test selecting multiple faces returns multiple FontSpecs."""
        from muban_cli.gui.dialogs.font_dialog import FontDialog

        font_file = tmp_path / "MyFont.ttf"
        font_file.write_bytes(b"fake font")

        dialog = FontDialog(str(font_file))
        qtbot.addWidget(dialog)

        dialog.name_input.setText("My Font")
        # Select multiple faces
        dialog.face_checkboxes["normal"].setChecked(True)
        dialog.face_checkboxes["bold"].setChecked(True)
        dialog.face_checkboxes["italic"].setChecked(True)
        dialog.face_checkboxes["boldItalic"].setChecked(False)

        specs = dialog.get_font_specs()
        assert len(specs) == 3
        faces = {s.face for s in specs}
        assert faces == {"normal", "bold", "italic"}
        # All should share the same file, name, and embedded flag
        for s in specs:
            assert s.file_path == font_file
            assert s.name == "My Font"
            assert s.embedded is True

    def test_font_dialog_selected_faces(self, qtbot, tmp_path):
        """Test selected_faces helper method."""
        from muban_cli.gui.dialogs.font_dialog import FontDialog

        font_file = tmp_path / "MyFont.ttf"
        font_file.write_bytes(b"fake font")

        dialog = FontDialog(str(font_file))
        qtbot.addWidget(dialog)

        # Uncheck default, check specific ones
        for cb in dialog.face_checkboxes.values():
            cb.setChecked(False)
        dialog.face_checkboxes["bold"].setChecked(True)
        dialog.face_checkboxes["boldItalic"].setChecked(True)

        assert dialog.selected_faces() == ["bold", "boldItalic"]


class TestUploadDialog:
    """Tests for the Upload dialog."""

    def test_upload_dialog_creation(self, qtbot, tmp_path):
        """Test upload dialog can be created."""
        from muban_cli.gui.dialogs.upload_dialog import UploadDialog
        
        zip_file = tmp_path / "template.zip"
        zip_file.write_bytes(b"PK fake zip")
        
        dialog = UploadDialog(str(zip_file))
        qtbot.addWidget(dialog)
        
        assert dialog is not None

    def test_upload_dialog_has_name_input(self, qtbot, tmp_path):
        """Test upload dialog has name input field."""
        from muban_cli.gui.dialogs.upload_dialog import UploadDialog
        
        zip_file = tmp_path / "template.zip"
        zip_file.write_bytes(b"PK fake zip")
        
        dialog = UploadDialog(str(zip_file))
        qtbot.addWidget(dialog)
        
        assert hasattr(dialog, 'name_input')

    def test_upload_dialog_default_name_from_file(self, qtbot, tmp_path):
        """Test upload dialog uses filename as default name."""
        from muban_cli.gui.dialogs.upload_dialog import UploadDialog
        
        zip_file = tmp_path / "my-template.zip"
        zip_file.write_bytes(b"PK fake zip")
        
        dialog = UploadDialog(str(zip_file))
        qtbot.addWidget(dialog)
        
        assert dialog.name_input.text() == "my-template"
    
    def test_upload_dialog_with_default_author(self, qtbot, tmp_path):
        """Test upload dialog with default author."""
        from muban_cli.gui.dialogs.upload_dialog import UploadDialog
        
        zip_file = tmp_path / "template.zip"
        zip_file.write_bytes(b"PK fake zip")
        
        dialog = UploadDialog(str(zip_file), default_author="John Doe")
        qtbot.addWidget(dialog)
        
        assert dialog.author_input.text() == "John Doe"
    
    def test_upload_dialog_get_values(self, qtbot, tmp_path):
        """Test getting values from upload dialog."""
        from muban_cli.gui.dialogs.upload_dialog import UploadDialog
        
        zip_file = tmp_path / "template.zip"
        zip_file.write_bytes(b"PK fake zip")
        
        dialog = UploadDialog(str(zip_file))
        qtbot.addWidget(dialog)
        
        dialog.name_input.setText("My Report Template")
        dialog.author_input.setText("Jane Smith")
        
        assert dialog.get_name() == "My Report Template"
        assert dialog.get_author() == "Jane Smith"


class TestExportOptionsDialog:
    """Tests for the Export Options dialog."""

    def test_export_options_dialog_creation(self, qtbot):
        """Test export options dialog can be created."""
        from muban_cli.gui.dialogs.export_options_dialog import ExportOptionsDialog
        
        dialog = ExportOptionsDialog()
        qtbot.addWidget(dialog)
        
        assert dialog is not None
        assert dialog.windowTitle() == "Export Options"

    def test_export_options_dialog_has_tabs(self, qtbot):
        """Test export options dialog has PDF/HTML/TXT tabs."""
        from muban_cli.gui.dialogs.export_options_dialog import ExportOptionsDialog
        
        dialog = ExportOptionsDialog()
        qtbot.addWidget(dialog)
        
        assert hasattr(dialog, 'tabs')
        assert dialog.tabs.count() == 3
        assert dialog.tabs.tabText(0) == "PDF"
        assert dialog.tabs.tabText(1) == "HTML"
        assert dialog.tabs.tabText(2) == "TXT"

    def test_export_options_dialog_with_icc_profiles(self, qtbot):
        """Test export options dialog with ICC profiles."""
        from muban_cli.gui.dialogs.export_options_dialog import ExportOptionsDialog
        
        icc_profiles = ["sRGB", "Adobe RGB", "CMYK"]
        dialog = ExportOptionsDialog(icc_profiles=icc_profiles)
        qtbot.addWidget(dialog)
        
        # ICC combo should have the profiles
        assert dialog.icc_combo.count() > 1  # "" + 3 profiles

    def test_export_options_dialog_pdf_options(self, qtbot):
        """Test export options dialog with PDF options."""
        from muban_cli.gui.dialogs.export_options_dialog import ExportOptionsDialog
        
        pdf_options = {
            "pdfaConformance": "PDF/A-1b",
            "userPassword": "secret"
        }
        dialog = ExportOptionsDialog(pdf_options=pdf_options)
        qtbot.addWidget(dialog)
        
        assert dialog.pdfa_combo.currentText() == "PDF/A-1b"

    def test_export_options_dialog_get_options(self, qtbot):
        """Test getting options from export dialog."""
        from muban_cli.gui.dialogs.export_options_dialog import ExportOptionsDialog
        
        dialog = ExportOptionsDialog()
        qtbot.addWidget(dialog)
        
        # Set some values
        dialog.pdfa_combo.setCurrentText("PDF/A-1b")
        
        # Should be able to get options
        pdf_opts = dialog.get_pdf_options()
        assert isinstance(pdf_opts, dict)

    def test_export_options_dialog_txt_defaults(self, qtbot):
        """Test TXT tab default values return None (no custom options)."""
        from muban_cli.gui.dialogs.export_options_dialog import ExportOptionsDialog

        dialog = ExportOptionsDialog()
        qtbot.addWidget(dialog)

        # Default values should produce None (nothing customized)
        txt_opts = dialog.get_txt_options()
        assert txt_opts is None

    def test_export_options_dialog_txt_options(self, qtbot):
        """Test TXT export options are read correctly."""
        from muban_cli.gui.dialogs.export_options_dialog import ExportOptionsDialog

        txt_options = {
            "characterWidth": 6.0,
            "characterHeight": 12.0,
            "pageWidthInChars": 80,
            "pageHeightInChars": 60,
            "trimLineRight": True,
            "lineSeparator": "\\n",
            "pageSeparator": "---",
        }
        dialog = ExportOptionsDialog(txt_options=txt_options)
        qtbot.addWidget(dialog)

        assert dialog.txt_char_width.value() == 6.0
        assert dialog.txt_char_height.value() == 12.0
        assert dialog.txt_page_width.value() == 80
        assert dialog.txt_page_height.value() == 60
        assert dialog.txt_trim_line_right.isChecked()

        opts = dialog.get_txt_options()
        assert opts is not None
        assert opts["characterWidth"] == 6.0
        assert opts["pageWidthInChars"] == 80
        assert opts["trimLineRight"] is True

    def test_export_options_dialog_txt_summary(self, qtbot):
        """Test TXT summary label generation."""
        from muban_cli.gui.dialogs.export_options_dialog import ExportOptionsDialog

        dialog = ExportOptionsDialog()
        qtbot.addWidget(dialog)

        assert dialog.get_txt_summary() == "Default"

        dialog.txt_page_width.setValue(80)
        dialog.txt_trim_line_right.setChecked(True)
        summary = dialog.get_txt_summary()
        assert "80 cols" in summary
        assert "Trim" in summary


class TestDataEditorDialog:
    """Tests for the Data Editor dialog."""

    def test_data_editor_dialog_creation(self, qtbot):
        """Test data editor dialog can be created."""
        from muban_cli.gui.dialogs.data_editor_dialog import DataEditorDialog
        
        dialog = DataEditorDialog()
        qtbot.addWidget(dialog)
        
        assert dialog is not None

    def test_data_editor_dialog_with_initial_data(self, qtbot):
        """Test data editor dialog with initial JSON data."""
        from muban_cli.gui.dialogs.data_editor_dialog import DataEditorDialog
        
        initial_data = '{"name": "test", "count": 42}'
        dialog = DataEditorDialog(data=initial_data)
        qtbot.addWidget(dialog)
        
        # Should show the initial data
        assert "test" in dialog.get_data()

    def test_data_editor_dialog_validation(self, qtbot):
        """Test data editor dialog JSON validation."""
        from muban_cli.gui.dialogs.data_editor_dialog import DataEditorDialog
        
        dialog = DataEditorDialog()
        qtbot.addWidget(dialog)
        
        # Set valid JSON
        dialog.editor.setPlainText('{"valid": true}')
        dialog._validate_json()
        assert "Valid JSON" in dialog.status_label.text()
        
        # Set invalid JSON
        dialog.editor.setPlainText('{invalid json')
        dialog._validate_json()
        assert "Valid JSON" not in dialog.status_label.text()

    def test_data_editor_format_json(self, qtbot):
        """Test data editor JSON formatting."""
        from muban_cli.gui.dialogs.data_editor_dialog import DataEditorDialog
        
        dialog = DataEditorDialog()
        qtbot.addWidget(dialog)
        
        # Set compact JSON
        dialog.editor.setPlainText('{"a":1,"b":2}')
        dialog._format_json()
        
        # Should be formatted with indentation
        formatted = dialog.editor.toPlainText()
        assert "\n" in formatted


class TestCodeEditor:
    """Tests for the CodeEditor widget."""

    def test_code_editor_creation(self, qtbot):
        """Test code editor can be created."""
        from muban_cli.gui.dialogs.data_editor_dialog import CodeEditor
        
        editor = CodeEditor()
        qtbot.addWidget(editor)
        
        assert editor is not None

    def test_code_editor_has_line_numbers(self, qtbot):
        """Test code editor has line number area."""
        from muban_cli.gui.dialogs.data_editor_dialog import CodeEditor
        
        editor = CodeEditor()
        qtbot.addWidget(editor)
        
        assert hasattr(editor, 'line_number_area')
        assert editor.line_number_area is not None

    def test_code_editor_line_number_width(self, qtbot):
        """Test code editor line number width calculation."""
        from muban_cli.gui.dialogs.data_editor_dialog import CodeEditor
        
        editor = CodeEditor()
        qtbot.addWidget(editor)
        
        # Should have a positive width for line numbers
        width = editor.line_number_area_width()
        assert width > 0

    def test_code_editor_set_text(self, qtbot):
        """Test setting text in code editor."""
        from muban_cli.gui.dialogs.data_editor_dialog import CodeEditor
        
        editor = CodeEditor()
        qtbot.addWidget(editor)
        
        editor.setPlainText("line 1\nline 2\nline 3")
        
        assert editor.blockCount() == 3


class TestLineNumberArea:
    """Tests for the LineNumberArea widget."""

    def test_line_number_area_creation(self, qtbot):
        """Test line number area can be created."""
        from muban_cli.gui.dialogs.data_editor_dialog import CodeEditor
        
        editor = CodeEditor()
        qtbot.addWidget(editor)
        
        assert editor.line_number_area is not None

    def test_line_number_area_size_hint(self, qtbot):
        """Test line number area size hint."""
        from muban_cli.gui.dialogs.data_editor_dialog import CodeEditor
        
        editor = CodeEditor()
        qtbot.addWidget(editor)
        
        size = editor.line_number_area.sizeHint()
        assert size.width() > 0


class TestErrorDialog:
    """Tests for the ErrorDialog with copy functionality."""

    def test_error_dialog_creation(self, qtbot):
        """Test error dialog can be created."""
        from muban_cli.gui.error_dialog import ErrorDialog
        
        dialog = ErrorDialog(None, "Test Error", "Something went wrong")
        qtbot.addWidget(dialog)
        
        assert dialog is not None
        assert dialog.windowTitle() == "Test Error"
        assert dialog.message == "Something went wrong"
        assert dialog.correlation_id is None

    def test_error_dialog_extracts_correlation_id(self, qtbot):
        """Test error dialog extracts correlation ID from message."""
        from muban_cli.gui.error_dialog import ErrorDialog
        
        message = "[TEMPLATE_FILL_ERROR] Failed to fill template (Correlation ID: abc-123-def)"
        dialog = ErrorDialog(None, "Generation Error", message)
        qtbot.addWidget(dialog)
        
        assert dialog.correlation_id == "abc-123-def"

    def test_error_dialog_extracts_uuid_correlation_id(self, qtbot):
        """Test error dialog extracts UUID correlation ID."""
        from muban_cli.gui.error_dialog import ErrorDialog
        
        message = "API error (Correlation ID: 00154aac-eb74-4867-a009-c9762fa0e059)"
        dialog = ErrorDialog(None, "Error", message)
        qtbot.addWidget(dialog)
        
        assert dialog.correlation_id == "00154aac-eb74-4867-a009-c9762fa0e059"

    def test_error_dialog_no_correlation_id(self, qtbot):
        """Test error dialog handles messages without correlation ID."""
        from muban_cli.gui.error_dialog import ErrorDialog
        
        dialog = ErrorDialog(None, "Error", "Simple error message")
        qtbot.addWidget(dialog)
        
        assert dialog.correlation_id is None

    def test_error_dialog_warning_style(self, qtbot):
        """Test error dialog can be created as warning."""
        from muban_cli.gui.error_dialog import ErrorDialog
        
        dialog = ErrorDialog(None, "Warning", "This is a warning", is_critical=False)
        qtbot.addWidget(dialog)
        
        assert dialog is not None

    def test_show_error_dialog_function(self, qtbot, monkeypatch):
        """Test show_error_dialog helper function."""
        from muban_cli.gui.error_dialog import show_error_dialog, ErrorDialog
        
        # Mock the exec method to avoid blocking
        monkeypatch.setattr(ErrorDialog, 'exec', lambda self: None)
        
        # Should not raise
        show_error_dialog(None, "Test", "Test message")
