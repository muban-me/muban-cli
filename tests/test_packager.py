"""
Tests for the JRXML Template Packager.
"""

import pytest
import tempfile
import zipfile
from pathlib import Path
from unittest.mock import patch

from muban_cli.packager import JRXMLPackager, AssetReference, PackageResult


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def packager():
    """Create a JRXMLPackager (packager) instance."""
    return JRXMLPackager()


@pytest.fixture
def sample_jrxml_content():
    """Sample JRXML content with various asset references."""
    return '''<?xml version="1.0" encoding="UTF-8"?>
<jasperReport name="test-report">
    <parameter name="REPORTS_DIR" class="java.lang.String">
        <defaultValueExpression><![CDATA["./"]]></defaultValueExpression>
    </parameter>
    
    <detail>
        <band height="100">
            <element kind="image" x="0" y="0" width="100" height="50">
                <expression><![CDATA[$P{REPORTS_DIR} + "assets/img/logo.png"]]></expression>
            </element>
            <element kind="image" x="100" y="0" width="100" height="50">
                <expression><![CDATA[$P{REPORTS_DIR} + "assets/img/banner.jpg"]]></expression>
            </element>
        </band>
    </detail>
</jasperReport>
'''


@pytest.fixture
def sample_jrxml_with_subreport():
    """Sample JRXML with subreport reference."""
    return '''<?xml version="1.0" encoding="UTF-8"?>
<jasperReport name="main-report">
    <parameter name="REPORTS_DIR" class="java.lang.String">
        <defaultValueExpression><![CDATA["./"]]></defaultValueExpression>
    </parameter>
    
    <detail>
        <band height="100">
            <element kind="subreport" x="0" y="0" width="500" height="100">
                <expression><![CDATA[$P{REPORTS_DIR} + "subreports/details.jasper"]]></expression>
            </element>
        </band>
    </detail>
</jasperReport>
'''


@pytest.fixture
def subreport_jrxml_content():
    """Sample subreport JRXML with assets and "../" REPORTS_DIR."""
    return '''<?xml version="1.0" encoding="UTF-8"?>
<jasperReport name="details-subreport">
    <parameter name="REPORTS_DIR" class="java.lang.String">
        <defaultValueExpression><![CDATA["../"]]></defaultValueExpression>
    </parameter>
    
    <detail>
        <band height="50">
            <element kind="image" x="0" y="0" width="100" height="50">
                <expression><![CDATA[$P{REPORTS_DIR} + "assets/img/icon.png"]]></expression>
            </element>
        </band>
    </detail>
</jasperReport>
'''


class TestJRXMLPackagerPatterns:
    """Test regex pattern matching."""
    
    def test_asset_pattern_matches_simple_path(self, packager):
        """Test ASSET_PATTERN matches simple asset paths."""
        content = '$P{REPORTS_DIR} + "assets/img/logo.png"'
        match = packager.ASSET_PATTERN.search(content)
        
        assert match is not None
        assert match.group(1) == "REPORTS_DIR"
        assert match.group(2) == "assets/img/logo.png"
    
    def test_asset_pattern_matches_various_extensions(self, packager):
        """Test ASSET_PATTERN matches various file extensions."""
        extensions = ['.png', '.jpg', '.jpeg', '.svg', '.gif', '.jasper', '.jrxml']
        
        for ext in extensions:
            content = f'$P{{REPORTS_DIR}} + "assets/file{ext}"'
            match = packager.ASSET_PATTERN.search(content)
            assert match is not None, f"Failed to match extension {ext}"
    
    def test_dynamic_dir_pattern_matches_parameter(self, packager):
        """Test DYNAMIC_DIR_PATTERN matches $P{} dynamic filename."""
        content = '$P{REPORTS_DIR} + "assets/img/faksymile/" + $P{filename}'
        match = packager.DYNAMIC_DIR_PATTERN.search(content)
        
        assert match is not None
        assert match.group(1) == "REPORTS_DIR"
        assert match.group(2) == "assets/img/faksymile/"
        assert match.group(3) == "P"
        assert match.group(4) == "filename"
    
    def test_dynamic_dir_pattern_matches_field(self, packager):
        """Test DYNAMIC_DIR_PATTERN matches $F{} dynamic filename."""
        content = '$P{REPORTS_DIR} + "images/" + $F{imageName}'
        match = packager.DYNAMIC_DIR_PATTERN.search(content)
        
        assert match is not None
        assert match.group(3) == "F"
        assert match.group(4) == "imageName"
    
    def test_dynamic_dir_pattern_matches_variable(self, packager):
        """Test DYNAMIC_DIR_PATTERN matches $V{} dynamic filename."""
        content = '$P{REPORTS_DIR} + "output/" + $V{generatedName}'
        match = packager.DYNAMIC_DIR_PATTERN.search(content)
        
        assert match is not None
        assert match.group(3) == "V"
        assert match.group(4) == "generatedName"
    
    def test_reports_dir_default_pattern(self, packager):
        """Test REPORTS_DIR default value extraction."""
        content = '''
        <parameter name="REPORTS_DIR" class="java.lang.String">
            <defaultValueExpression><![CDATA["./"]]></defaultValueExpression>
        </parameter>
        '''
        match = packager.REPORTS_DIR_DEFAULT_PATTERN.search(content)
        
        assert match is not None
        assert match.group(1) == "./"
    
    def test_reports_dir_default_pattern_parent(self, packager):
        """Test REPORTS_DIR default value extraction with parent path."""
        content = '''
        <parameter name="REPORTS_DIR" class="java.lang.String">
            <defaultValueExpression><![CDATA["../"]]></defaultValueExpression>
        </parameter>
        '''
        match = packager.REPORTS_DIR_DEFAULT_PATTERN.search(content)
        
        assert match is not None
        assert match.group(1) == "../"
    
    def test_has_literal_string_pattern(self, packager):
        """Test HAS_LITERAL_STRING pattern."""
        # Should match
        assert packager.HAS_LITERAL_STRING.search('$P{DIR} + "path"') is not None
        assert packager.HAS_LITERAL_STRING.search('"literal"') is not None
        
        # Should not match
        assert packager.HAS_LITERAL_STRING.search('$P{DIR} + $P{PATH}') is None
        assert packager.HAS_LITERAL_STRING.search('$F{imagePath}') is None


class TestAssetExtraction:
    """Test asset reference extraction from JRXML files."""
    
    def test_extract_simple_assets(self, temp_dir, packager, sample_jrxml_content):
        """Test extracting simple asset references."""
        jrxml_path = temp_dir / "test.jrxml"
        jrxml_path.write_text(sample_jrxml_content, encoding='utf-8')
        
        result = PackageResult(success=False)
        assets = packager._extract_asset_references(jrxml_path, result)
        
        assert len(assets) == 2
        paths = [a.path for a in assets]
        assert "assets/img/logo.png" in paths
        assert "assets/img/banner.jpg" in paths
    
    def test_extract_reports_dir_value(self, temp_dir, packager, sample_jrxml_content):
        """Test REPORTS_DIR default value is extracted."""
        jrxml_path = temp_dir / "test.jrxml"
        jrxml_path.write_text(sample_jrxml_content, encoding='utf-8')
        
        result = PackageResult(success=False)
        assets = packager._extract_asset_references(jrxml_path, result)
        
        # All assets should have reports_dir_value = "./"
        for asset in assets:
            assert asset.reports_dir_value == "./"
    
    def test_extract_subreport_reports_dir_value(self, temp_dir, packager, subreport_jrxml_content):
        """Test REPORTS_DIR default value is extracted from subreport."""
        jrxml_path = temp_dir / "subreport.jrxml"
        jrxml_path.write_text(subreport_jrxml_content, encoding='utf-8')
        
        result = PackageResult(success=False)
        assets = packager._extract_asset_references(jrxml_path, result)
        
        # All assets should have reports_dir_value = "../"
        for asset in assets:
            assert asset.reports_dir_value == "../"
    
    def test_skip_non_reports_dir_params(self, temp_dir, packager):
        """Test that non-REPORTS_DIR parameters are skipped."""
        content = '''<?xml version="1.0" encoding="UTF-8"?>
<jasperReport name="test">
    <parameter name="REPORTS_DIR" class="java.lang.String">
        <defaultValueExpression><![CDATA["./"]]></defaultValueExpression>
    </parameter>
    <detail>
        <band>
            <textField>
                <expression><![CDATA[$P{SOME_PARAM} + "not/an/asset"]]></expression>
            </textField>
            <element kind="image">
                <expression><![CDATA[$P{REPORTS_DIR} + "real/asset.png"]]></expression>
            </element>
        </band>
    </detail>
</jasperReport>
'''
        jrxml_path = temp_dir / "test.jrxml"
        jrxml_path.write_text(content, encoding='utf-8')
        
        result = PackageResult(success=False)
        assets = packager._extract_asset_references(jrxml_path, result)
        
        # Only the REPORTS_DIR asset should be found
        assert len(assets) == 1
        assert assets[0].path == "real/asset.png"
    
    def test_skip_url_assets(self, temp_dir, packager):
        """Test that URL assets are skipped."""
        content = '''<?xml version="1.0" encoding="UTF-8"?>
<jasperReport name="test">
    <parameter name="REPORTS_DIR" class="java.lang.String">
        <defaultValueExpression><![CDATA["./"]]></defaultValueExpression>
    </parameter>
    <detail>
        <band>
            <element kind="image">
                <expression><![CDATA[$P{REPORTS_DIR} + "https://example.com/image.png"]]></expression>
            </element>
            <element kind="image">
                <expression><![CDATA[$P{REPORTS_DIR} + "local/image.png"]]></expression>
            </element>
        </band>
    </detail>
</jasperReport>
'''
        jrxml_path = temp_dir / "test.jrxml"
        jrxml_path.write_text(content, encoding='utf-8')
        
        result = PackageResult(success=False)
        assets = packager._extract_asset_references(jrxml_path, result)
        
        # Only local asset should be found
        assert len(assets) == 1
        assert assets[0].path == "local/image.png"
        
        # URL should be in skipped list
        assert len(result.skipped_urls) == 1
        assert "https://example.com/image.png" in result.skipped_urls[0]
    
    def test_detect_fully_dynamic_expressions(self, temp_dir, packager):
        """Test that fully dynamic expressions are detected."""
        content = '''<?xml version="1.0" encoding="UTF-8"?>
<jasperReport name="test">
    <parameter name="REPORTS_DIR" class="java.lang.String">
        <defaultValueExpression><![CDATA["./"]]></defaultValueExpression>
    </parameter>
    <detail>
        <band>
            <element kind="image" x="0" y="0" width="100" height="50">
                <expression><![CDATA[$P{REPORTS_DIR} + $P{dynamicPath}]]></expression>
            </element>
        </band>
    </detail>
</jasperReport>
'''
        jrxml_path = temp_dir / "test.jrxml"
        jrxml_path.write_text(content, encoding='utf-8')
        
        result = PackageResult(success=False)
        packager._extract_asset_references(jrxml_path, result)
        
        # Fully dynamic expression should be detected
        assert len(result.skipped_dynamic) == 1


class TestRecursiveSubreportAnalysis:
    """Test recursive subreport analysis."""
    
    def test_recursive_subreport_assets(self, temp_dir, packager):
        """Test that assets from subreports are included."""
        # Create directory structure
        subreports_dir = temp_dir / "subreports"
        subreports_dir.mkdir()
        assets_dir = temp_dir / "assets" / "img"
        assets_dir.mkdir(parents=True)
        
        # Create main template
        main_content = '''<?xml version="1.0" encoding="UTF-8"?>
<jasperReport name="main">
    <parameter name="REPORTS_DIR" class="java.lang.String">
        <defaultValueExpression><![CDATA["./"]]></defaultValueExpression>
    </parameter>
    <detail>
        <band>
            <element kind="subreport">
                <expression><![CDATA[$P{REPORTS_DIR} + "subreports/child.jasper"]]></expression>
            </element>
        </band>
    </detail>
</jasperReport>
'''
        main_jrxml = temp_dir / "main.jrxml"
        main_jrxml.write_text(main_content, encoding='utf-8')
        
        # Create subreport
        subreport_content = '''<?xml version="1.0" encoding="UTF-8"?>
<jasperReport name="child">
    <parameter name="REPORTS_DIR" class="java.lang.String">
        <defaultValueExpression><![CDATA["../"]]></defaultValueExpression>
    </parameter>
    <detail>
        <band>
            <element kind="image">
                <expression><![CDATA[$P{REPORTS_DIR} + "assets/img/nested-icon.png"]]></expression>
            </element>
        </band>
    </detail>
</jasperReport>
'''
        subreport_jrxml = subreports_dir / "child.jrxml"
        subreport_jrxml.write_text(subreport_content, encoding='utf-8')
        
        # Create .jasper file (compiler looks for it)
        (subreports_dir / "child.jasper").write_bytes(b"dummy jasper")
        
        # Create asset files
        (assets_dir / "nested-icon.png").write_bytes(b"dummy png")
        
        # Run compilation
        result = packager.package(main_jrxml, dry_run=True)
        
        assert result.success
        paths = [a.path for a in result.assets_found]
        
        # Should include both subreport and nested asset
        assert "subreports/child.jasper" in paths
        assert "subreports/child.jrxml" in paths
        assert "assets/img/nested-icon.png" in paths
    
    def test_subreport_source_tracking(self, temp_dir, packager):
        """Test that subreport source is tracked for nested assets."""
        # Create directory structure
        subreports_dir = temp_dir / "subreports"
        subreports_dir.mkdir()
        assets_dir = temp_dir / "assets"
        assets_dir.mkdir()
        
        # Create main template
        main_content = '''<?xml version="1.0" encoding="UTF-8"?>
<jasperReport name="main">
    <parameter name="REPORTS_DIR" class="java.lang.String">
        <defaultValueExpression><![CDATA["./"]]></defaultValueExpression>
    </parameter>
    <detail>
        <band>
            <element kind="subreport">
                <expression><![CDATA[$P{REPORTS_DIR} + "subreports/sub.jasper"]]></expression>
            </element>
        </band>
    </detail>
</jasperReport>
'''
        main_jrxml = temp_dir / "main.jrxml"
        main_jrxml.write_text(main_content, encoding='utf-8')
        
        # Create subreport
        subreport_content = '''<?xml version="1.0" encoding="UTF-8"?>
<jasperReport name="sub">
    <parameter name="REPORTS_DIR" class="java.lang.String">
        <defaultValueExpression><![CDATA["../"]]></defaultValueExpression>
    </parameter>
    <detail>
        <band>
            <element kind="image">
                <expression><![CDATA[$P{REPORTS_DIR} + "assets/from-sub.png"]]></expression>
            </element>
        </band>
    </detail>
</jasperReport>
'''
        (subreports_dir / "sub.jrxml").write_text(subreport_content, encoding='utf-8')
        (subreports_dir / "sub.jasper").write_bytes(b"dummy")
        (assets_dir / "from-sub.png").write_bytes(b"dummy")
        
        result = packager.package(main_jrxml, dry_run=True)
        
        # Find the nested asset
        nested_asset = next((a for a in result.assets_found if a.path == "assets/from-sub.png"), None)
        assert nested_asset is not None
        assert nested_asset.subreport_source == "subreports/sub.jrxml"

    def test_jrxml_source_included_alongside_jasper(self, temp_dir, packager):
        """Test that raw .jrxml source files are included alongside .jasper subreports."""
        subreports_dir = temp_dir / "subreports"
        subreports_dir.mkdir()

        main_content = '''<?xml version="1.0" encoding="UTF-8"?>
<jasperReport name="main">
    <parameter name="REPORTS_DIR" class="java.lang.String">
        <defaultValueExpression><![CDATA["./"]]></defaultValueExpression>
    </parameter>
    <detail>
        <band>
            <element kind="subreport">
                <expression><![CDATA[$P{REPORTS_DIR} + "subreports/report.jasper"]]></expression>
            </element>
        </band>
    </detail>
</jasperReport>
'''
        main_jrxml = temp_dir / "main.jrxml"
        main_jrxml.write_text(main_content, encoding='utf-8')

        subreport_content = '''<?xml version="1.0" encoding="UTF-8"?>
<jasperReport name="report">
    <parameter name="REPORTS_DIR" class="java.lang.String">
        <defaultValueExpression><![CDATA["./"]]></defaultValueExpression>
    </parameter>
</jasperReport>
'''
        (subreports_dir / "report.jrxml").write_text(subreport_content, encoding='utf-8')
        (subreports_dir / "report.jasper").write_bytes(b"dummy")

        result = packager.package(main_jrxml, dry_run=True)
        paths = [a.path for a in result.assets_found]

        assert "subreports/report.jasper" in paths
        assert "subreports/report.jrxml" in paths

    def test_jrxml_source_not_included_when_missing(self, temp_dir, packager):
        """Test that missing .jrxml source files are silently skipped."""
        subreports_dir = temp_dir / "subreports"
        subreports_dir.mkdir()

        main_content = '''<?xml version="1.0" encoding="UTF-8"?>
<jasperReport name="main">
    <parameter name="REPORTS_DIR" class="java.lang.String">
        <defaultValueExpression><![CDATA["./"]]></defaultValueExpression>
    </parameter>
    <detail>
        <band>
            <element kind="subreport">
                <expression><![CDATA[$P{REPORTS_DIR} + "subreports/report.jasper"]]></expression>
            </element>
        </band>
    </detail>
</jasperReport>
'''
        main_jrxml = temp_dir / "main.jrxml"
        main_jrxml.write_text(main_content, encoding='utf-8')

        # Only .jasper, no .jrxml source
        (subreports_dir / "report.jasper").write_bytes(b"dummy")

        result = packager.package(main_jrxml, dry_run=True)
        paths = [a.path for a in result.assets_found]

        assert "subreports/report.jasper" in paths
        assert "subreports/report.jrxml" not in paths


class TestPOSIXPathNormalization:
    """Test POSIX-style path normalization."""
    
    def test_double_slash_normalization(self, temp_dir, packager):
        """Test that double slashes are normalized."""
        # Create structure where subreport uses "../" and asset starts with "/"
        subreports_dir = temp_dir / "subreports"
        subreports_dir.mkdir()
        img_dir = temp_dir / "img"
        img_dir.mkdir()
        
        # Main template
        main_content = '''<?xml version="1.0" encoding="UTF-8"?>
<jasperReport name="main">
    <parameter name="REPORTS_DIR" class="java.lang.String">
        <defaultValueExpression><![CDATA["./"]]></defaultValueExpression>
    </parameter>
    <detail>
        <band>
            <element kind="subreport">
                <expression><![CDATA[$P{REPORTS_DIR} + "subreports/test.jasper"]]></expression>
            </element>
        </band>
    </detail>
</jasperReport>
'''
        main_jrxml = temp_dir / "main.jrxml"
        main_jrxml.write_text(main_content, encoding='utf-8')
        
        # Subreport with leading slash in asset path (POSIX: "../" + "/img" = "..//img" = "../img")
        subreport_content = '''<?xml version="1.0" encoding="UTF-8"?>
<jasperReport name="test">
    <parameter name="REPORTS_DIR" class="java.lang.String">
        <defaultValueExpression><![CDATA["../"]]></defaultValueExpression>
    </parameter>
    <detail>
        <band>
            <element kind="image">
                <expression><![CDATA[$P{REPORTS_DIR} + "/img/logo.png"]]></expression>
            </element>
        </band>
    </detail>
</jasperReport>
'''
        (subreports_dir / "test.jrxml").write_text(subreport_content, encoding='utf-8')
        (subreports_dir / "test.jasper").write_bytes(b"dummy")
        (img_dir / "logo.png").write_bytes(b"dummy png")
        
        result = packager.package(main_jrxml, dry_run=True)
        
        assert result.success
        # The asset should be found and resolved correctly
        assert len(result.assets_included) >= 1
        
        # Check that img/logo.png is in included assets
        included_paths = [str(p.relative_to(temp_dir)).replace('\\', '/') for p in result.assets_included]
        assert "img/logo.png" in included_paths


class TestDynamicDirectoryAssets:
    """Test dynamic directory asset handling."""
    
    def test_dynamic_directory_includes_all_files(self, temp_dir, packager):
        """Test that dynamic directories include all files."""
        # Create directory with multiple files
        faksymile_dir = temp_dir / "assets" / "img" / "faksymile"
        faksymile_dir.mkdir(parents=True)
        
        (faksymile_dir / "person1.png").write_bytes(b"dummy1")
        (faksymile_dir / "person2.png").write_bytes(b"dummy2")
        (faksymile_dir / "person3.png").write_bytes(b"dummy3")
        
        # Create template with dynamic directory reference
        content = '''<?xml version="1.0" encoding="UTF-8"?>
<jasperReport name="test">
    <parameter name="REPORTS_DIR" class="java.lang.String">
        <defaultValueExpression><![CDATA["./"]]></defaultValueExpression>
    </parameter>
    <detail>
        <band>
            <element kind="image">
                <expression><![CDATA[$P{REPORTS_DIR} + "assets/img/faksymile/" + $P{filename}]]></expression>
            </element>
        </band>
    </detail>
</jasperReport>
'''
        jrxml_path = temp_dir / "test.jrxml"
        jrxml_path.write_text(content, encoding='utf-8')
        
        result = packager.package(jrxml_path, dry_run=True)
        
        assert result.success
        # Should include all 3 files from the directory
        assert len(result.assets_included) == 3


class TestZIPCreation:
    """Test ZIP package creation."""
    
    def test_create_zip_with_assets(self, temp_dir, packager):
        """Test creating a ZIP with assets."""
        # Create assets
        assets_dir = temp_dir / "assets" / "img"
        assets_dir.mkdir(parents=True)
        (assets_dir / "logo.png").write_bytes(b"logo data")
        (assets_dir / "icon.svg").write_bytes(b"icon data")
        
        # Create template
        content = '''<?xml version="1.0" encoding="UTF-8"?>
<jasperReport name="test">
    <parameter name="REPORTS_DIR" class="java.lang.String">
        <defaultValueExpression><![CDATA["./"]]></defaultValueExpression>
    </parameter>
    <detail>
        <band>
            <element kind="image">
                <expression><![CDATA[$P{REPORTS_DIR} + "assets/img/logo.png"]]></expression>
            </element>
            <element kind="image">
                <expression><![CDATA[$P{REPORTS_DIR} + "assets/img/icon.svg"]]></expression>
            </element>
        </band>
    </detail>
</jasperReport>
'''
        jrxml_path = temp_dir / "test.jrxml"
        jrxml_path.write_text(content, encoding='utf-8')
        
        output_path = temp_dir / "output.zip"
        result = packager.package(jrxml_path, output_path)
        
        assert result.success
        assert output_path.exists()
        
        # Verify ZIP contents
        with zipfile.ZipFile(output_path, 'r') as zf:
            names = zf.namelist()
            assert "test.jrxml" in names
            assert "assets/img/logo.png" in names
            assert "assets/img/icon.svg" in names
    
    def test_dry_run_no_zip(self, temp_dir, packager, sample_jrxml_content):
        """Test that dry run doesn't create a ZIP file."""
        jrxml_path = temp_dir / "test.jrxml"
        jrxml_path.write_text(sample_jrxml_content, encoding='utf-8')
        
        output_path = temp_dir / "output.zip"
        result = packager.package(jrxml_path, output_path, dry_run=True)
        
        assert result.success
        assert not output_path.exists()


class TestPackageResult:
    """Test PackageResult tracking."""
    
    def test_missing_assets_tracked(self, temp_dir, packager):
        """Test that missing assets are tracked in result."""
        content = '''<?xml version="1.0" encoding="UTF-8"?>
<jasperReport name="test">
    <parameter name="REPORTS_DIR" class="java.lang.String">
        <defaultValueExpression><![CDATA["./"]]></defaultValueExpression>
    </parameter>
    <detail>
        <band>
            <element kind="image">
                <expression><![CDATA[$P{REPORTS_DIR} + "nonexistent/image.png"]]></expression>
            </element>
        </band>
    </detail>
</jasperReport>
'''
        jrxml_path = temp_dir / "test.jrxml"
        jrxml_path.write_text(content, encoding='utf-8')
        
        result = packager.package(jrxml_path, dry_run=True)
        
        assert result.success  # Dry run still succeeds
        assert len(result.assets_missing) == 1
        assert result.assets_missing[0].path == "nonexistent/image.png"
    
    def test_warnings_for_missing_assets(self, temp_dir, packager):
        """Test that warnings are generated for missing assets."""
        content = '''<?xml version="1.0" encoding="UTF-8"?>
<jasperReport name="test">
    <parameter name="REPORTS_DIR" class="java.lang.String">
        <defaultValueExpression><![CDATA["./"]]></defaultValueExpression>
    </parameter>
    <detail>
        <band>
            <element kind="image">
                <expression><![CDATA[$P{REPORTS_DIR} + "missing/file.png"]]></expression>
            </element>
        </band>
    </detail>
</jasperReport>
'''
        jrxml_path = temp_dir / "test.jrxml"
        jrxml_path.write_text(content, encoding='utf-8')
        
        result = packager.package(jrxml_path, dry_run=True)
        
        assert len(result.warnings) >= 1
        assert any("missing" in w.lower() or "not found" in w.lower() for w in result.warnings)


class TestCustomReportsDirParam:
    """Test custom REPORTS_DIR parameter name."""
    
    def test_custom_param_name(self, temp_dir):
        """Test using a custom parameter name instead of REPORTS_DIR."""
        packager = JRXMLPackager(reports_dir_param="TEMPLATE_PATH")
        
        content = '''<?xml version="1.0" encoding="UTF-8"?>
<jasperReport name="test">
    <parameter name="TEMPLATE_PATH" class="java.lang.String">
        <defaultValueExpression><![CDATA["./"]]></defaultValueExpression>
    </parameter>
    <detail>
        <band>
            <element kind="image">
                <expression><![CDATA[$P{TEMPLATE_PATH} + "img/logo.png"]]></expression>
            </element>
            <element kind="image">
                <expression><![CDATA[$P{REPORTS_DIR} + "ignored/image.png"]]></expression>
            </element>
        </band>
    </detail>
</jasperReport>
'''
        jrxml_path = temp_dir / "test.jrxml"
        jrxml_path.write_text(content, encoding='utf-8')
        
        result = PackageResult(success=False)
        assets = packager._extract_asset_references(jrxml_path, result)
        
        # Only TEMPLATE_PATH asset should be found
        assert len(assets) == 1
        assert assets[0].path == "img/logo.png"


class TestParseFontsXml:
    """Test _parse_fonts_xml method for extracting font paths from fonts.xml."""
    
    def test_parse_valid_fonts_xml(self, temp_dir, packager):
        """Test parsing a valid fonts.xml with multiple font families."""
        fonts_xml_content = '''<?xml version="1.0" encoding="UTF-8"?>
<fontFamilies>
    <fontFamily name="Open Sans">
        <normal>fonts/OpenSans-Regular.ttf</normal>
        <bold>fonts/OpenSans-Bold.ttf</bold>
        <italic>fonts/OpenSans-Italic.ttf</italic>
        <boldItalic>fonts/OpenSans-BoldItalic.ttf</boldItalic>
        <pdfEncoding>Identity-H</pdfEncoding>
        <pdfEmbedded>true</pdfEmbedded>
    </fontFamily>
    <fontFamily name="Roboto">
        <normal>fonts/Roboto-Regular.ttf</normal>
        <bold>fonts/Roboto-Bold.ttf</bold>
        <pdfEncoding>Identity-H</pdfEncoding>
        <pdfEmbedded>true</pdfEmbedded>
    </fontFamily>
</fontFamilies>
'''
        fonts_xml_path = temp_dir / "fonts.xml"
        fonts_xml_path.write_text(fonts_xml_content, encoding='utf-8')
        
        font_files = packager._parse_fonts_xml(fonts_xml_path)
        
        # Should find 6 font files (4 from Open Sans + 2 from Roboto)
        assert len(font_files) == 6
        
        # Check archive paths are preserved
        archive_paths = [f[0] for f in font_files]
        assert "fonts/OpenSans-Regular.ttf" in archive_paths
        assert "fonts/OpenSans-Bold.ttf" in archive_paths
        assert "fonts/Roboto-Regular.ttf" in archive_paths
        
    def test_parse_empty_fonts_xml(self, temp_dir, packager):
        """Test parsing an empty fonts.xml."""
        fonts_xml_content = '''<?xml version="1.0" encoding="UTF-8"?>
<fontFamilies>
</fontFamilies>
'''
        fonts_xml_path = temp_dir / "fonts.xml"
        fonts_xml_path.write_text(fonts_xml_content, encoding='utf-8')
        
        font_files = packager._parse_fonts_xml(fonts_xml_path)
        
        assert len(font_files) == 0
        
    def test_parse_fonts_xml_with_partial_faces(self, temp_dir, packager):
        """Test parsing fonts.xml where font family has only some face types."""
        fonts_xml_content = '''<?xml version="1.0" encoding="UTF-8"?>
<fontFamilies>
    <fontFamily name="Simple Font">
        <normal>fonts/Simple.ttf</normal>
        <pdfEncoding>Identity-H</pdfEncoding>
        <pdfEmbedded>true</pdfEmbedded>
    </fontFamily>
</fontFamilies>
'''
        fonts_xml_path = temp_dir / "fonts.xml"
        fonts_xml_path.write_text(fonts_xml_content, encoding='utf-8')
        
        font_files = packager._parse_fonts_xml(fonts_xml_path)
        
        # Should find only 1 font file (normal only)
        assert len(font_files) == 1
        assert font_files[0][0] == "fonts/Simple.ttf"
        
    def test_parse_invalid_fonts_xml(self, temp_dir, packager):
        """Test parsing invalid XML returns empty list."""
        fonts_xml_path = temp_dir / "fonts.xml"
        fonts_xml_path.write_text("not valid xml <><>", encoding='utf-8')
        
        font_files = packager._parse_fonts_xml(fonts_xml_path)
        
        # Should return empty list on parse error
        assert len(font_files) == 0
        
    def test_parse_fonts_xml_resolves_paths_relative_to_xml(self, temp_dir, packager):
        """Test that font paths are resolved relative to fonts.xml location."""
        subdir = temp_dir / "config"
        subdir.mkdir()
        
        fonts_xml_content = '''<?xml version="1.0" encoding="UTF-8"?>
<fontFamilies>
    <fontFamily name="Test">
        <normal>../fonts/Test.ttf</normal>
    </fontFamily>
</fontFamilies>
'''
        fonts_xml_path = subdir / "fonts.xml"
        fonts_xml_path.write_text(fonts_xml_content, encoding='utf-8')
        
        font_files = packager._parse_fonts_xml(fonts_xml_path)
        
        assert len(font_files) == 1
        archive_path, abs_path = font_files[0]
        assert archive_path == "../fonts/Test.ttf"
        # Absolute path should be resolved relative to config/ directory
        assert abs_path == (temp_dir / "fonts" / "Test.ttf").resolve()


class TestPackageWithFontsXml:
    """Test package() method with fonts_xml_path parameter."""
    
    def test_package_with_fonts_xml_includes_fonts(self, temp_dir, packager, sample_jrxml_content):
        """Test that packaging with fonts.xml includes referenced font files."""
        # Create JRXML
        jrxml_path = temp_dir / "test.jrxml"
        jrxml_path.write_text(sample_jrxml_content, encoding='utf-8')
        
        # Create required assets
        (temp_dir / "assets" / "img").mkdir(parents=True)
        (temp_dir / "assets" / "img" / "logo.png").write_bytes(b"PNG")
        (temp_dir / "assets" / "img" / "banner.jpg").write_bytes(b"JPG")
        
        # Create fonts directory and font files
        fonts_dir = temp_dir / "fonts"
        fonts_dir.mkdir()
        (fonts_dir / "Regular.ttf").write_bytes(b"TTF-regular")
        (fonts_dir / "Bold.ttf").write_bytes(b"TTF-bold")
        
        # Create fonts.xml
        fonts_xml_content = '''<?xml version="1.0" encoding="UTF-8"?>
<fontFamilies>
    <fontFamily name="Test Font">
        <normal>fonts/Regular.ttf</normal>
        <bold>fonts/Bold.ttf</bold>
        <pdfEncoding>Identity-H</pdfEncoding>
        <pdfEmbedded>true</pdfEmbedded>
    </fontFamily>
</fontFamilies>
'''
        fonts_xml_path = temp_dir / "fonts.xml"
        fonts_xml_path.write_text(fonts_xml_content, encoding='utf-8')
        
        # Package with fonts.xml
        output_path = temp_dir / "output.zip"
        result = packager.package(jrxml_path, output_path, fonts_xml_path=fonts_xml_path)
        
        assert result.success
        assert output_path.exists()
        
        # Verify ZIP contents include fonts
        with zipfile.ZipFile(output_path, 'r') as zf:
            names = zf.namelist()
            assert "fonts.xml" in names
            assert "fonts/Regular.ttf" in names
            assert "fonts/Bold.ttf" in names
            
    def test_package_fonts_xml_sets_fonts_xml_files_in_result(self, temp_dir, packager, sample_jrxml_content):
        """Test that fonts_xml_files is populated in result when using fonts.xml."""
        # Create JRXML
        jrxml_path = temp_dir / "test.jrxml"
        jrxml_path.write_text(sample_jrxml_content, encoding='utf-8')
        
        # Create required assets
        (temp_dir / "assets" / "img").mkdir(parents=True)
        (temp_dir / "assets" / "img" / "logo.png").write_bytes(b"PNG")
        (temp_dir / "assets" / "img" / "banner.jpg").write_bytes(b"JPG")
        
        # Create font files
        fonts_dir = temp_dir / "fonts"
        fonts_dir.mkdir()
        (fonts_dir / "Test.ttf").write_bytes(b"TTF")
        
        # Create fonts.xml
        fonts_xml_content = '''<?xml version="1.0" encoding="UTF-8"?>
<fontFamilies>
    <fontFamily name="Test">
        <normal>fonts/Test.ttf</normal>
    </fontFamily>
</fontFamilies>
'''
        fonts_xml_path = temp_dir / "fonts.xml"
        fonts_xml_path.write_text(fonts_xml_content, encoding='utf-8')
        
        # Package (dry run to check result)
        result = packager.package(jrxml_path, dry_run=True, fonts_xml_path=fonts_xml_path)
        
        assert result.success
        assert len(result.fonts_xml_files) == 1
        assert result.fonts_xml_files[0] == (fonts_dir / "Test.ttf").resolve()
        # fonts_included should be empty when using fonts_xml_path
        assert len(result.fonts_included) == 0
        
    def test_package_fonts_xml_missing_font_files_still_succeeds(self, temp_dir, packager, sample_jrxml_content):
        """Test that packaging succeeds even if fonts.xml references missing fonts."""
        # Create JRXML
        jrxml_path = temp_dir / "test.jrxml"
        jrxml_path.write_text(sample_jrxml_content, encoding='utf-8')
        
        # Create required assets
        (temp_dir / "assets" / "img").mkdir(parents=True)
        (temp_dir / "assets" / "img" / "logo.png").write_bytes(b"PNG")
        (temp_dir / "assets" / "img" / "banner.jpg").write_bytes(b"JPG")
        
        # Create fonts.xml referencing non-existent fonts
        fonts_xml_content = '''<?xml version="1.0" encoding="UTF-8"?>
<fontFamilies>
    <fontFamily name="Missing">
        <normal>fonts/NonExistent.ttf</normal>
    </fontFamily>
</fontFamilies>
'''
        fonts_xml_path = temp_dir / "fonts.xml"
        fonts_xml_path.write_text(fonts_xml_content, encoding='utf-8')
        
        # Package should still succeed (with warning logged)
        output_path = temp_dir / "output.zip"
        result = packager.package(jrxml_path, output_path, fonts_xml_path=fonts_xml_path)
        
        assert result.success
        
        # ZIP should have fonts.xml but not the missing font file
        with zipfile.ZipFile(output_path, 'r') as zf:
            names = zf.namelist()
            assert "fonts.xml" in names
            assert "fonts/NonExistent.ttf" not in names


def _create_docx_with_images(docx_path: Path, alt_texts: list, header_alt_texts: list = None):
    """
    Create a minimal DOCX file (ZIP with Open XML) containing images with specified ALT texts.
    
    Args:
        docx_path: Path to write the DOCX file
        alt_texts: List of ALT text strings for images in the main document
        header_alt_texts: Optional list of ALT text strings for images in header1.xml
    """
    # Minimal [Content_Types].xml
    content_types = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
    <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
    <Default Extension="xml" ContentType="application/xml"/>
    <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
</Types>'''
    
    # Minimal _rels/.rels
    rels = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
    <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>'''
    
    # Build drawing elements for each ALT text
    wp_ns = 'http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing'
    
    def build_drawings(alt_text_list):
        drawings = ''
        for i, alt_text in enumerate(alt_text_list):
            # XML-escape the alt text for safe embedding in attribute values
            escaped = alt_text.replace('&', '&amp;').replace('"', '&quot;').replace('<', '&lt;').replace('>', '&gt;') if alt_text else ''
            descr_attr = f' descr="{escaped}"' if alt_text else ''
            drawings += f'''
            <w:r>
                <w:drawing>
                    <wp:inline xmlns:wp="{wp_ns}">
                        <wp:docPr id="{i + 1}" name="Picture {i + 1}"{descr_attr}/>
                    </wp:inline>
                </w:drawing>
            </w:r>'''
        return drawings
    
    # Main document
    document_xml = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"
            xmlns:wp="{wp_ns}">
    <w:body>
        <w:p>{build_drawings(alt_texts)}
        </w:p>
    </w:body>
</w:document>'''
    
    with zipfile.ZipFile(docx_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        zf.writestr('[Content_Types].xml', content_types)
        zf.writestr('_rels/.rels', rels)
        zf.writestr('word/document.xml', document_xml)
        
        # Add header if alt texts provided
        if header_alt_texts:
            header_xml = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:hdr xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"
       xmlns:wp="{wp_ns}">
    <w:p>{build_drawings(header_alt_texts)}
    </w:p>
</w:hdr>'''
            zf.writestr('word/header1.xml', header_xml)


class TestDocxImageExtraction:
    """Test DOCX image asset reference extraction from ALT text."""
    
    def test_no_images_no_assets(self, temp_dir, packager):
        """Test DOCX with no images returns no assets."""
        docx_path = temp_dir / "template.docx"
        _create_docx_with_images(docx_path, [])
        
        result = PackageResult(success=False)
        assets = packager._extract_docx_image_references(docx_path, result)
        
        assert len(assets) == 0
        assert len(result.skipped_dynamic) == 0
    
    def test_image_without_prefix_ignored(self, temp_dir, packager):
        """Test images without 'image:' prefix are ignored."""
        docx_path = temp_dir / "template.docx"
        _create_docx_with_images(docx_path, ["A decorative logo", "Some alt text"])
        
        result = PackageResult(success=False)
        assets = packager._extract_docx_image_references(docx_path, result)
        
        assert len(assets) == 0
    
    def test_static_file_path(self, temp_dir, packager):
        """Test static file path extraction (image:assets/logo.png)."""
        docx_path = temp_dir / "template.docx"
        _create_docx_with_images(docx_path, ["image:assets/logo.png"])
        
        result = PackageResult(success=False)
        assets = packager._extract_docx_image_references(docx_path, result)
        
        assert len(assets) == 1
        assert assets[0].path == "assets/logo.png"
        assert assets[0].asset_type == "image"
        assert assets[0].reports_dir_value == ""
        assert not assets[0].is_dynamic_dir
    
    def test_static_file_path_nested(self, temp_dir, packager):
        """Test static nested file path."""
        docx_path = temp_dir / "template.docx"
        _create_docx_with_images(docx_path, ["image:assets/img/stamps/company.png"])
        
        result = PackageResult(success=False)
        assets = packager._extract_docx_image_references(docx_path, result)
        
        assert len(assets) == 1
        assert assets[0].path == "assets/img/stamps/company.png"
    
    def test_simple_key_no_path_skipped(self, temp_dir, packager):
        """Test simple key without path (API-provided) produces no asset."""
        docx_path = temp_dir / "template.docx"
        _create_docx_with_images(docx_path, ["image:facsimile"])
        
        result = PackageResult(success=False)
        assets = packager._extract_docx_image_references(docx_path, result)
        
        # Simple keys are API-provided, nothing to bundle
        assert len(assets) == 0
        assert len(result.skipped_dynamic) == 0
    
    def test_spel_ternary_extracts_both_paths(self, temp_dir, packager):
        """Test SpEL ternary expression extracts both path candidates."""
        docx_path = temp_dir / "template.docx"
        _create_docx_with_images(docx_path, [
            "image:${ gender == 'F' ? 'assets/female.png' : 'assets/male.png' }"
        ])
        
        result = PackageResult(success=False)
        assets = packager._extract_docx_image_references(docx_path, result)
        
        paths = sorted([a.path for a in assets])
        assert len(paths) == 2
        assert "assets/female.png" in paths
        assert "assets/male.png" in paths
    
    def test_spel_ternary_filters_non_path_literals(self, temp_dir, packager):
        """Test SpEL ternary filters out comparison values that aren't paths."""
        docx_path = temp_dir / "template.docx"
        _create_docx_with_images(docx_path, [
            "image:${ 'female'.equals(customer_gender) ? 'pictures/female.png' : 'pictures/male.png' }"
        ])
        
        result = PackageResult(success=False)
        assets = packager._extract_docx_image_references(docx_path, result)
        
        paths = [a.path for a in assets]
        # 'female' should be filtered out (no / or extension)
        assert "female" not in paths
        assert "pictures/female.png" in paths
        assert "pictures/male.png" in paths
    
    def test_spel_dynamic_directory_concatenation(self, temp_dir, packager):
        """Test SpEL concatenation with dynamic directory pattern."""
        docx_path = temp_dir / "template.docx"
        _create_docx_with_images(docx_path, [
            "image:${'assets/signatures/' + manager + '.png'}"
        ])
        
        result = PackageResult(success=False)
        assets = packager._extract_docx_image_references(docx_path, result)
        
        assert len(assets) == 1
        assert assets[0].path == "assets/signatures/"
        assert assets[0].is_dynamic_dir is True
        assert assets[0].dynamic_param == "manager"
        assert assets[0].asset_type == "directory"
    
    def test_spel_dynamic_directory_double_quoted(self, temp_dir, packager):
        """Test SpEL concatenation with double-quoted directory."""
        docx_path = temp_dir / "template.docx"
        _create_docx_with_images(docx_path, [
            'image:${"assets/signatures/" + manager + ".png"}'
        ])
        
        result = PackageResult(success=False)
        assets = packager._extract_docx_image_references(docx_path, result)
        
        assert len(assets) == 1
        assert assets[0].path == "assets/signatures/"
        assert assets[0].is_dynamic_dir is True
        assert assets[0].dynamic_param == "manager"
    
    def test_fully_dynamic_expression_skipped(self, temp_dir, packager):
        """Test fully dynamic expression (no path literals) is reported as skipped."""
        docx_path = temp_dir / "template.docx"
        _create_docx_with_images(docx_path, ["image:${imagePath}"])
        
        result = PackageResult(success=False)
        assets = packager._extract_docx_image_references(docx_path, result)
        
        assert len(assets) == 0
        assert len(result.skipped_dynamic) == 1
        assert "${imagePath}" in result.skipped_dynamic[0]
    
    def test_multiple_images_mixed(self, temp_dir, packager):
        """Test multiple images with mixed types."""
        docx_path = temp_dir / "template.docx"
        _create_docx_with_images(docx_path, [
            "image:assets/logo.png",                                     # static
            "image:facsimile",                                           # simple key (API)
            "image:${ x ? 'assets/a.png' : 'assets/b.png' }",          # ternary
            "image:${dynamicOnly}",                                      # fully dynamic
            "A regular image without prefix",                            # no prefix
        ])
        
        result = PackageResult(success=False)
        assets = packager._extract_docx_image_references(docx_path, result)
        
        paths = [a.path for a in assets]
        # Static + ternary paths
        assert "assets/logo.png" in paths
        assert "assets/a.png" in paths
        assert "assets/b.png" in paths
        # Simple key and fully dynamic are NOT in assets
        assert len(assets) == 3
        # Fully dynamic is in skipped
        assert len(result.skipped_dynamic) == 1
    
    def test_deduplication(self, temp_dir, packager):
        """Test that duplicate paths across multiple images are deduplicated."""
        docx_path = temp_dir / "template.docx"
        _create_docx_with_images(docx_path, [
            "image:assets/logo.png",
            "image:assets/logo.png",  # duplicate
        ])
        
        result = PackageResult(success=False)
        assets = packager._extract_docx_image_references(docx_path, result)
        
        assert len(assets) == 1
        assert assets[0].path == "assets/logo.png"
    
    def test_header_images_scanned(self, temp_dir, packager):
        """Test that images in header XML parts are also scanned."""
        docx_path = temp_dir / "template.docx"
        _create_docx_with_images(
            docx_path,
            alt_texts=["image:assets/body-logo.png"],
            header_alt_texts=["image:assets/header-logo.png"]
        )
        
        result = PackageResult(success=False)
        assets = packager._extract_docx_image_references(docx_path, result)
        
        paths = [a.path for a in assets]
        assert "assets/body-logo.png" in paths
        assert "assets/header-logo.png" in paths
        assert len(assets) == 2
    
    def test_risk_level_ternary(self, temp_dir, packager):
        """Test risk-level indicator example from handbook."""
        docx_path = temp_dir / "template.docx"
        _create_docx_with_images(docx_path, [
            "image:${ risk > 80 ? 'assets/exclamation.png' : 'assets/info.png' }"
        ])
        
        result = PackageResult(success=False)
        assets = packager._extract_docx_image_references(docx_path, result)
        
        paths = sorted([a.path for a in assets])
        assert "assets/exclamation.png" in paths
        assert "assets/info.png" in paths


class TestDocxPackageIntegration:
    """Test full DOCX packaging with image assets."""
    
    def test_package_docx_with_static_assets(self, temp_dir, packager):
        """Test packaging DOCX with static image assets."""
        # Create DOCX with image reference
        docx_path = temp_dir / "template.docx"
        _create_docx_with_images(docx_path, ["image:assets/logo.png"])
        
        # Create the referenced asset
        (temp_dir / "assets").mkdir()
        (temp_dir / "assets" / "logo.png").write_bytes(b"PNG_DATA")
        
        # Package
        output_path = temp_dir / "output.zip"
        result = packager.package(docx_path, output_path)
        
        assert result.success
        assert result.template_type == "DOCX"
        assert len(result.assets_found) == 1
        assert len(result.assets_included) == 1
        assert len(result.assets_missing) == 0
        
        # Verify ZIP contents
        with zipfile.ZipFile(output_path, 'r') as zf:
            names = zf.namelist()
            assert "template.docx" in names
            assert "assets/logo.png" in names
    
    def test_package_docx_missing_asset_reported(self, temp_dir, packager):
        """Test that missing assets are reported in warnings."""
        docx_path = temp_dir / "template.docx"
        _create_docx_with_images(docx_path, ["image:assets/missing.png"])
        
        output_path = temp_dir / "output.zip"
        result = packager.package(docx_path, output_path)
        
        assert result.success
        assert len(result.assets_found) == 1
        assert len(result.assets_missing) == 1
        assert len(result.assets_included) == 0
        assert any("missing.png" in w for w in result.warnings)
    
    def test_package_docx_dynamic_directory(self, temp_dir, packager):
        """Test packaging DOCX with dynamic directory includes all files."""
        docx_path = temp_dir / "template.docx"
        _create_docx_with_images(docx_path, [
            "image:${'assets/signatures/' + manager + '.png'}"
        ])
        
        # Create directory with multiple files
        sig_dir = temp_dir / "assets" / "signatures"
        sig_dir.mkdir(parents=True)
        (sig_dir / "alice.png").write_bytes(b"ALICE")
        (sig_dir / "bob.png").write_bytes(b"BOB")
        (sig_dir / "charlie.png").write_bytes(b"CHARLIE")
        
        output_path = temp_dir / "output.zip"
        result = packager.package(docx_path, output_path)
        
        assert result.success
        assert len(result.assets_included) == 3
        assert any("Dynamic asset" in w for w in result.warnings)
        assert any("included all 3 files" in w for w in result.warnings)
        
        # Verify ZIP contents
        with zipfile.ZipFile(output_path, 'r') as zf:
            names = zf.namelist()
            assert "template.docx" in names
            assert "assets/signatures/alice.png" in names
            assert "assets/signatures/bob.png" in names
            assert "assets/signatures/charlie.png" in names
    
    def test_package_docx_spel_ternary_with_assets(self, temp_dir, packager):
        """Test packaging DOCX with SpEL ternary, both files exist."""
        docx_path = temp_dir / "template.docx"
        _create_docx_with_images(docx_path, [
            "image:${ gender == 'F' ? 'assets/female.png' : 'assets/male.png' }"
        ])
        
        # Create both image files
        (temp_dir / "assets").mkdir()
        (temp_dir / "assets" / "female.png").write_bytes(b"FEMALE")
        (temp_dir / "assets" / "male.png").write_bytes(b"MALE")
        
        output_path = temp_dir / "output.zip"
        result = packager.package(docx_path, output_path)
        
        assert result.success
        assert len(result.assets_included) == 2
        
        with zipfile.ZipFile(output_path, 'r') as zf:
            names = zf.namelist()
            assert "assets/female.png" in names
            assert "assets/male.png" in names
    
    def test_package_docx_dry_run(self, temp_dir, packager):
        """Test dry run analyzes assets without creating ZIP."""
        docx_path = temp_dir / "template.docx"
        _create_docx_with_images(docx_path, ["image:assets/logo.png"])
        
        # Create asset
        (temp_dir / "assets").mkdir()
        (temp_dir / "assets" / "logo.png").write_bytes(b"PNG")
        
        output_path = temp_dir / "output.zip"
        result = packager.package(docx_path, output_path, dry_run=True)
        
        assert result.success
        assert len(result.assets_found) == 1
        assert not output_path.exists()  # No ZIP created
    
    def test_package_docx_no_images_still_works(self, temp_dir, packager):
        """Test DOCX without any image references packages correctly."""
        docx_path = temp_dir / "template.docx"
        _create_docx_with_images(docx_path, [])
        
        output_path = temp_dir / "output.zip"
        result = packager.package(docx_path, output_path)
        
        assert result.success
        assert len(result.assets_found) == 0
        
        with zipfile.ZipFile(output_path, 'r') as zf:
            names = zf.namelist()
            assert "template.docx" in names
    
    def test_package_docx_with_fonts_and_assets(self, temp_dir, packager):
        """Test packaging DOCX with both image assets and fonts."""
        from muban_cli.packager import FontSpec
        
        docx_path = temp_dir / "template.docx"
        _create_docx_with_images(docx_path, ["image:assets/stamp.png"])
        
        # Create asset
        (temp_dir / "assets").mkdir()
        (temp_dir / "assets" / "stamp.png").write_bytes(b"STAMP")
        
        # Create font file
        font_path = temp_dir / "Arial.ttf"
        font_path.write_bytes(b"TTF_DATA")
        fonts = [FontSpec(file_path=font_path, name="Arial", face="normal")]
        
        output_path = temp_dir / "output.zip"
        result = packager.package(docx_path, output_path, fonts=fonts)
        
        assert result.success
        assert len(result.assets_included) == 1
        assert len(result.fonts_included) == 1
        
        with zipfile.ZipFile(output_path, 'r') as zf:
            names = zf.namelist()
            assert "template.docx" in names
            assert "assets/stamp.png" in names
            assert "fonts.xml" in names
            assert "fonts/Arial.ttf" in names