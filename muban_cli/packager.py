"""
JRXML Template Packager.

This module provides functionality to package a JRXML template and its dependencies
into a ZIP package suitable for uploading to the Muban Document Generation Service.

The packager:
1. Parses the JRXML file to find asset references (images, subreports)
2. Resolves asset paths relative to the JRXML file location
3. Creates a ZIP archive preserving the directory structure
4. Optionally bundles custom fonts with fonts.xml configuration
"""

import re
import zipfile
import logging
from pathlib import Path
from typing import List, Set, Tuple, Optional, Dict
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class FontSpec:
    """Specification for a font to include in the package."""
    file_path: Path  # Local path to the font file (TTF/OTF)
    name: str  # Font family name as used in JRXML templates
    face: str  # Font face: normal, bold, italic, boldItalic
    embedded: bool = True  # Whether to embed in PDF output


@dataclass
class AssetReference:
    """Represents a referenced asset in a JRXML file."""
    path: str  # The path as written in the JRXML (e.g., "assets/img/logo.png")
    source_file: Path  # The JRXML file that contains this reference
    line_number: Optional[int] = None
    asset_type: str = "image"  # "image", "subreport", "font", "directory", etc.
    is_dynamic_dir: bool = False  # True if this is a directory with dynamic filename
    dynamic_param: Optional[str] = None  # The parameter name for dynamic filename
    subreport_source: Optional[str] = None  # If from subreport, the subreport .jrxml path
    reports_dir_value: str = "./"  # The REPORTS_DIR default value from the source file


@dataclass
class PackageResult:
    """Result of a template packaging operation."""
    success: bool
    output_path: Optional[Path] = None
    main_jrxml: Optional[Path] = None
    assets_found: List[AssetReference] = field(default_factory=list)
    assets_missing: List[AssetReference] = field(default_factory=list)
    assets_included: List[Path] = field(default_factory=list)
    fonts_included: List[FontSpec] = field(default_factory=list)  # Fonts bundled in package
    skipped_urls: List[str] = field(default_factory=list)  # Remote URLs skipped
    skipped_dynamic: List[str] = field(default_factory=list)  # Fully dynamic expressions
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


# Backward compatibility alias
CompilationResult = PackageResult


class JRXMLPackager:
    """
    Packages JRXML templates and their dependencies into a ZIP package.
    
    The packager automatically detects:
    - Image references using the configurable REPORTS_DIR parameter
    - Directory references with dynamic filenames (includes all files)
    - Subreport references (future)
    - Font files (future)
    
    Example usage:
        packager = JRXMLPackager()
        result = packager.package("template.jrxml", "output.zip")
        if result.success:
            print(f"Created: {result.output_path}")
        else:
            for error in result.errors:
                print(f"Error: {error}")
    """
    
    # Regex patterns for extracting asset paths
    # Pattern 1: $P{PARAM_NAME} + "path/to/asset"
    ASSET_PATTERN = re.compile(
        r'\$P\{(\w+)\}\s*\+\s*"([^"]+)"',
        re.MULTILINE
    )
    
    # Pattern 2: $P{PARAM_NAME} + "path/to/dir/" + $P|$F|$V{OTHER_PARAM}
    # This detects directory references where the filename is dynamic
    # Supports: $P{} (parameters), $F{} (fields), $V{} (variables)
    DYNAMIC_DIR_PATTERN = re.compile(
        r'\$P\{(\w+)\}\s*\+\s*"([^"]+/)"\s*\+\s*\$([PFV])\{([^}]+)\}',
        re.MULTILINE
    )
    
    # Pattern 3: All image/subreport expressions - to detect fully dynamic ones
    # We'll check if they contain a literal string; if not, they're fully dynamic
    IMAGE_EXPRESSION_PATTERN = re.compile(
        r'<element\s+kind="(?:image|subreport)"[^>]*>.*?<expression>\s*<!\[CDATA\[(.*?)\]\]>\s*</expression>',
        re.MULTILINE | re.DOTALL
    )
    
    # Pattern to check if an expression contains a literal string path
    HAS_LITERAL_STRING = re.compile(r'"[^"]+"')
    
    # Pattern to extract REPORTS_DIR parameter default value
    # Matches: <parameter name="REPORTS_DIR" ...><defaultValueExpression><![CDATA["value"]]></defaultValueExpression>
    REPORTS_DIR_DEFAULT_PATTERN = re.compile(
        r'<parameter\s+name="REPORTS_DIR"[^>]*>.*?<defaultValueExpression>\s*<!\[CDATA\["([^"]*)"\]\]>\s*</defaultValueExpression>',
        re.MULTILINE | re.DOTALL
    )
    
    # Common image extensions
    IMAGE_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.gif', '.svg', '.bmp', '.tiff', '.tif'}
    
    # Subreport extensions
    SUBREPORT_EXTENSIONS = {'.jasper', '.jrxml'}
    
    # URL prefixes to skip (remote resources don't need packaging)
    URL_PREFIXES = ('http://', 'https://', 'file://', 'ftp://')
    
    def __init__(self, reports_dir_param: str = "REPORTS_DIR"):
        """
        Initialize the packager.
        
        Args:
            reports_dir_param: The parameter name used for the reports directory.
                              This can vary between deployments (default: REPORTS_DIR).
        """
        self.reports_dir_param = reports_dir_param
        self._detected_params: Set[str] = set()
    
    def package(
        self,
        jrxml_path: Path,
        output_path: Optional[Path] = None,
        dry_run: bool = False,
        fonts: Optional[List[FontSpec]] = None
    ) -> PackageResult:
        """
        Package a JRXML template into a ZIP package.
        
        Args:
            jrxml_path: Path to the main JRXML file
            output_path: Output ZIP file path (default: <jrxml_name>.zip)
            dry_run: If True, don't create ZIP, just analyze dependencies
            fonts: Optional list of FontSpec objects to include in the package
            
        Returns:
            PackageResult with details about the packaging operation
        """
        result = PackageResult(success=False)
        fonts = fonts or []
        
        # Validate input
        jrxml_path = Path(jrxml_path).resolve()
        if not jrxml_path.exists():
            result.errors.append(f"JRXML file not found: {jrxml_path}")
            return result
        
        if not jrxml_path.suffix.lower() == '.jrxml':
            result.warnings.append(f"File does not have .jrxml extension: {jrxml_path}")
        
        result.main_jrxml = jrxml_path
        base_dir = jrxml_path.parent
        
        # Set default output path
        if output_path is None:
            output_path = jrxml_path.with_suffix('.zip')
        else:
            output_path = Path(output_path).resolve()
        
        result.output_path = output_path
        
        # Parse JRXML and extract asset references (with recursive subreport analysis)
        try:
            processed_files: Set[Path] = set()  # Track processed files to avoid loops
            assets = self._extract_asset_references_recursive(
                jrxml_path, base_dir, result, processed_files
            )
            result.assets_found = assets
        except Exception as e:
            result.errors.append(f"Failed to parse JRXML: {e}")
            return result
        
        # Log detected parameter names
        if self._detected_params:
            params_str = ", ".join(sorted(self._detected_params))
            logger.info(f"Detected path parameters: {params_str}")
        
        # Resolve asset paths and check existence
        # Each asset is resolved relative to: source_file.parent / REPORTS_DIR / asset.path
        assets_to_include: List[Tuple[Path, str]] = []  # (absolute_path, archive_path)
        
        for asset in assets:
            # Resolve path using the REPORTS_DIR value from the source file
            # This simulates: cd source_file.parent && resolve REPORTS_DIR + asset.path
            # Use string concatenation first (POSIX semantics: "../" + "/path" = "..//path" = "../path")
            source_dir = asset.source_file.parent
            combined_path = asset.reports_dir_value + asset.path
            # Normalize double slashes (POSIX: // equals /)
            while '//' in combined_path:
                combined_path = combined_path.replace('//', '/')
            # Also handle backslash version
            while '\\\\' in combined_path:
                combined_path = combined_path.replace('\\\\', '\\')
            asset_abs_path = (source_dir / combined_path).resolve()
            
            # Calculate archive path (relative to main template root)
            try:
                archive_path = str(asset_abs_path.relative_to(base_dir)).replace('\\', '/')
            except ValueError:
                # Asset is outside main template directory - use asset.path as fallback
                archive_path = asset.path.replace('\\', '/')
            
            if asset.is_dynamic_dir:
                # This is a directory with dynamic filename - include all files
                if asset_abs_path.exists() and asset_abs_path.is_dir():
                    dir_files = list(asset_abs_path.iterdir())
                    file_count = 0
                    for file_path in dir_files:
                        if file_path.is_file():
                            # Build relative path for archive (based on effective dir path)
                            rel_path = archive_path + "/" + file_path.name if archive_path else file_path.name
                            assets_to_include.append((file_path, rel_path))
                            result.assets_included.append(file_path)
                            file_count += 1
                    
                    # Add warning about dynamic asset inclusion
                    result.warnings.append(
                        f"Dynamic asset: {archive_path}* (filename from {asset.dynamic_param}) - "
                        f"included all {file_count} files from directory"
                    )
                else:
                    result.assets_missing.append(asset)
                    result.warnings.append(
                        f"Directory not found: {archive_path} (referenced in {asset.source_file.name})"
                    )
            elif asset_abs_path.exists():
                result.assets_included.append(asset_abs_path)
                # Use the computed archive path (relative to main template root)
                assets_to_include.append((asset_abs_path, archive_path))
            else:
                result.assets_missing.append(asset)
                result.warnings.append(
                    f"Asset not found: {archive_path} (referenced in {asset.source_file.name})"
                )
        
        # Report findings
        logger.info(f"Found {len(result.assets_found)} asset references")
        logger.info(f"  - Included: {len(result.assets_included)}")
        logger.info(f"  - Missing: {len(result.assets_missing)}")
        
        # Store fonts in result
        result.fonts_included = fonts
        
        if dry_run:
            result.success = True
            return result
        
        # Create ZIP archive
        try:
            self._create_zip(jrxml_path, assets_to_include, output_path, fonts)
            result.success = True
        except Exception as e:
            result.errors.append(f"Failed to create ZIP: {e}")
            return result
        
        return result
    
    def _extract_asset_references(
        self, 
        jrxml_path: Path,
        result: PackageResult
    ) -> List[AssetReference]:
        """
        Extract all asset references from a JRXML file.
        
        This method parses the JRXML and finds all expressions that reference
        external files using a path parameter (like REPORTS_DIR).
        
        It also detects dynamic directory patterns like:
            $P{REPORTS_DIR} + "assets/img/faksymile/" + $P{filename_param}
            $P{REPORTS_DIR} + "assets/img/faksymile/" + $F{filename_field}
            $P{REPORTS_DIR} + "assets/img/faksymile/" + $V{filename_variable}
        
        Fully dynamic paths (no literal string) are detected and reported.
        """
        assets: List[AssetReference] = []
        seen_paths: Set[str] = set()
        dynamic_dirs: Set[str] = set()  # Track directories with dynamic filenames
        
        # Read the file content for regex parsing
        content = jrxml_path.read_text(encoding='utf-8')
        
        # Extract REPORTS_DIR default value from this file
        reports_dir_value = "./"  # Default fallback
        reports_dir_match = self.REPORTS_DIR_DEFAULT_PATTERN.search(content)
        if reports_dir_match:
            reports_dir_value = reports_dir_match.group(1)
            logger.debug(f"Found REPORTS_DIR default value: '{reports_dir_value}' in {jrxml_path.name}")
        
        # Detect fully dynamic expressions (no literal path string - can't resolve)
        # Find all image/subreport expressions and check if they have a literal string
        for match in self.IMAGE_EXPRESSION_PATTERN.finditer(content):
            expr = match.group(1).strip()
            # If expression contains no literal string, it's fully dynamic
            if not self.HAS_LITERAL_STRING.search(expr):
                if expr not in result.skipped_dynamic:
                    result.skipped_dynamic.append(expr)
        
        # First, find dynamic directory patterns (path + "/" + $P|$F|$V{param})
        for match in self.DYNAMIC_DIR_PATTERN.finditer(content):
            param_name = match.group(1)
            dir_path = match.group(2)  # Path ending with /
            expr_type = match.group(3)  # P, F, or V
            dynamic_param = match.group(4)  # The parameter/field/variable name
            
            # Only match if parameter is the reports directory parameter
            if param_name != self.reports_dir_param:
                continue
            
            # Build the full expression reference (e.g., $P{name}, $F{name}, $V{name})
            expr_prefix = {"P": "$P", "F": "$F", "V": "$V"}.get(expr_type, "$P")
            dynamic_expr = f"{expr_prefix}{{{dynamic_param}}}"
            
            # Track detected parameter names
            self._detected_params.add(param_name)
            
            # Skip duplicates
            if dir_path in seen_paths:
                continue
            seen_paths.add(dir_path)
            dynamic_dirs.add(dir_path)
            
            # Calculate line number
            line_number = content[:match.start()].count('\n') + 1
            
            assets.append(AssetReference(
                path=dir_path,
                source_file=jrxml_path,
                line_number=line_number,
                asset_type="directory",
                is_dynamic_dir=True,
                dynamic_param=dynamic_expr,
                reports_dir_value=reports_dir_value
            ))
        
        # Then find regular asset patterns
        for match in self.ASSET_PATTERN.finditer(content):
            param_name = match.group(1)
            asset_path = match.group(2)
            
            # Only match if parameter is the reports directory parameter
            if param_name != self.reports_dir_param:
                continue
            
            # Track detected parameter names
            self._detected_params.add(param_name)
            
            # Skip URLs - remote resources don't need packaging
            if asset_path.lower().startswith(self.URL_PREFIXES):
                if asset_path not in result.skipped_urls:
                    result.skipped_urls.append(asset_path)
                logger.debug(f"Skipping remote URL: {asset_path}")
                continue
            
            # Skip if this is part of a dynamic directory pattern we already found
            if asset_path.endswith('/') and asset_path in dynamic_dirs:
                continue
            
            # Skip duplicates
            if asset_path in seen_paths:
                continue
            seen_paths.add(asset_path)
            
            # Determine asset type from extension
            ext = Path(asset_path).suffix.lower()
            if ext in self.IMAGE_EXTENSIONS:
                asset_type = "image"
            elif ext in self.SUBREPORT_EXTENSIONS:
                asset_type = "subreport"
            else:
                asset_type = "unknown"
            
            # Calculate line number
            line_number = content[:match.start()].count('\n') + 1
            
            assets.append(AssetReference(
                path=asset_path,
                source_file=jrxml_path,
                line_number=line_number,
                asset_type=asset_type,
                reports_dir_value=reports_dir_value
            ))
        
        return assets
    
    def _extract_asset_references_recursive(
        self,
        jrxml_path: Path,
        base_dir: Path,
        result: PackageResult,
        processed_files: Set[Path]
    ) -> List[AssetReference]:
        """
        Recursively extract asset references from a JRXML file and its subreports.
        
        When a subreport reference (.jasper) is found, this method looks for
        the corresponding .jrxml source file and recursively extracts its assets.
        This ensures all nested assets from subreports are included in the package.
        
        Args:
            jrxml_path: Path to the JRXML file to analyze
            base_dir: Base directory for resolving relative paths
            result: PackageResult to accumulate warnings/errors
            processed_files: Set of already processed files to prevent loops
            
        Returns:
            List of all asset references (including those from subreports)
        """
        # Avoid infinite loops
        resolved_path = jrxml_path.resolve()
        if resolved_path in processed_files:
            return []
        processed_files.add(resolved_path)
        
        # Get direct assets from this file
        assets = self._extract_asset_references(jrxml_path, result)
        
        # Find subreports and recursively analyze their source files
        subreport_assets: List[AssetReference] = []
        
        for asset in assets:
            if asset.asset_type == "subreport" and asset.path.endswith('.jasper'):
                # Look for corresponding .jrxml file
                jrxml_source_path = asset.path[:-7] + '.jrxml'  # Replace .jasper with .jrxml
                jrxml_abs_path = (base_dir / jrxml_source_path).resolve()
                
                if jrxml_abs_path.exists():
                    logger.debug(f"Analyzing subreport source: {jrxml_source_path}")
                    
                    # Recursively extract assets from subreport
                    nested_assets = self._extract_asset_references_recursive(
                        jrxml_abs_path, base_dir, result, processed_files
                    )
                    
                    # Track subreport source for context
                    for nested_asset in nested_assets:
                        # Update source_file to show where the asset was found
                        if nested_asset.source_file == jrxml_abs_path:
                            nested_asset.subreport_source = jrxml_source_path
                    
                    subreport_assets.extend(nested_assets)
                else:
                    logger.debug(f"Subreport source not found: {jrxml_source_path}")
        
        # Combine and deduplicate
        all_assets = assets + subreport_assets
        
        # Remove duplicates while preserving order
        seen_paths: Set[str] = set()
        unique_assets: List[AssetReference] = []
        for asset in all_assets:
            if asset.path not in seen_paths:
                seen_paths.add(asset.path)
                unique_assets.append(asset)
        
        return unique_assets

    def _create_zip(
        self,
        jrxml_path: Path,
        assets: List[Tuple[Path, str]],
        output_path: Path,
        fonts: Optional[List[FontSpec]] = None
    ) -> None:
        """
        Create a ZIP archive with the JRXML and its assets.
        
        The ZIP structure preserves the relative paths of assets
        as they appear in the JRXML file. If fonts are provided,
        creates a fonts.xml configuration and includes font files
        in a fonts/ directory.
        """
        fonts = fonts or []
        
        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            # Add the main JRXML file at the root
            zf.write(jrxml_path, jrxml_path.name)
            logger.debug(f"Added: {jrxml_path.name}")
            
            # Add all assets with their relative paths
            for abs_path, archive_path in assets:
                zf.write(abs_path, archive_path)
                logger.debug(f"Added: {archive_path}")
            
            # Add fonts if provided
            if fonts:
                # Generate fonts.xml content
                fonts_xml = self._generate_fonts_xml(fonts)
                zf.writestr('fonts.xml', fonts_xml)
                logger.debug("Added: fonts.xml")
                
                # Add font files to fonts/ directory
                for font in fonts:
                    archive_font_path = f"fonts/{font.file_path.name}"
                    zf.write(font.file_path, archive_font_path)
                    logger.debug(f"Added: {archive_font_path}")
        
        logger.info(f"Created ZIP: {output_path}")
    
    def _generate_fonts_xml(self, fonts: List[FontSpec]) -> str:
        """
        Generate fonts.xml content for JasperReports font configuration.
        
        Groups fonts by family name and generates proper XML structure.
        """
        # Group fonts by family name
        families: Dict[str, List[FontSpec]] = {}
        for font in fonts:
            if font.name not in families:
                families[font.name] = []
            families[font.name].append(font)
        
        # Build XML
        lines = ['<?xml version="1.0" encoding="UTF-8"?>', '<fontFamilies>']
        
        for family_name, family_fonts in families.items():
            lines.append(f'    <fontFamily name="{family_name}">')
            
            # Add font faces
            for font in family_fonts:
                archive_path = f"fonts/{font.file_path.name}"
                lines.append(f'        <{font.face}>{archive_path}</{font.face}>')
            
            # Add common properties (use first font's embedded setting)
            lines.append('        <pdfEncoding>Identity-H</pdfEncoding>')
            embedded_value = 'true' if family_fonts[0].embedded else 'false'
            lines.append(f'        <pdfEmbedded>{embedded_value}</pdfEmbedded>')
            
            lines.append('    </fontFamily>')
        
        lines.append('</fontFamilies>')
        
        return '\n'.join(lines)
    
    def analyze(self, jrxml_path: Path) -> PackageResult:
        """
        Analyze a JRXML file without creating a ZIP.
        
        This is equivalent to package() with dry_run=True.
        """
        return self.package(jrxml_path, dry_run=True)


# Backward compatibility alias
JRXMLCompiler = JRXMLPackager


def package_template(
    jrxml_path: Path,
    output_path: Optional[Path] = None,
    dry_run: bool = False,
    reports_dir_param: str = "REPORTS_DIR"
) -> PackageResult:
    """
    Convenience function to package a JRXML template.
    
    Args:
        jrxml_path: Path to the main JRXML file
        output_path: Output ZIP file path (default: <jrxml_name>.zip)
        dry_run: If True, don't create ZIP, just analyze dependencies
        reports_dir_param: The parameter name used for the reports directory
        
    Returns:
        PackageResult with details about the packaging operation
    """
    packager = JRXMLPackager(reports_dir_param=reports_dir_param)
    return packager.package(jrxml_path, output_path, dry_run)


# Backward compatibility alias
compile_template = package_template
