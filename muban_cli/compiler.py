"""
JRXML Template Compiler.

This module provides functionality to compile a JRXML template and its dependencies
into a ZIP package suitable for uploading to the Muban Document Generation Service.

The compiler:
1. Parses the JRXML file to find asset references (images, subreports)
2. Resolves asset paths relative to the JRXML file location
3. Creates a ZIP archive preserving the directory structure
"""

import re
import zipfile
import logging
from pathlib import Path
from typing import List, Set, Tuple, Optional
from dataclasses import dataclass, field
from xml.etree import ElementTree as ET

logger = logging.getLogger(__name__)


@dataclass
class AssetReference:
    """Represents a referenced asset in a JRXML file."""
    path: str  # The path as written in the JRXML (e.g., "assets/img/logo.png")
    source_file: Path  # The JRXML file that contains this reference
    line_number: Optional[int] = None
    asset_type: str = "image"  # "image", "subreport", "font", "directory", etc.
    is_dynamic_dir: bool = False  # True if this is a directory with dynamic filename
    dynamic_param: Optional[str] = None  # The parameter name for dynamic filename


@dataclass
class CompilationResult:
    """Result of a template compilation."""
    success: bool
    output_path: Optional[Path] = None
    main_jrxml: Optional[Path] = None
    assets_found: List[AssetReference] = field(default_factory=list)
    assets_missing: List[AssetReference] = field(default_factory=list)
    assets_included: List[Path] = field(default_factory=list)
    skipped_urls: List[str] = field(default_factory=list)  # Remote URLs skipped
    skipped_dynamic: List[str] = field(default_factory=list)  # Fully dynamic expressions
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


class JRXMLCompiler:
    """
    Compiles JRXML templates and their dependencies into a ZIP package.
    
    The compiler automatically detects:
    - Image references using the configurable REPORTS_DIR parameter
    - Directory references with dynamic filenames (includes all files)
    - Subreport references (future)
    - Font files (future)
    
    Example usage:
        compiler = JRXMLCompiler()
        result = compiler.compile("template.jrxml", "output.zip")
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
    
    # Common image extensions
    IMAGE_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.gif', '.svg', '.bmp', '.tiff', '.tif'}
    
    # Subreport extensions
    SUBREPORT_EXTENSIONS = {'.jasper', '.jrxml'}
    
    # URL prefixes to skip (remote resources don't need packaging)
    URL_PREFIXES = ('http://', 'https://', 'file://', 'ftp://')
    
    def __init__(self, reports_dir_param: str = "REPORTS_DIR"):
        """
        Initialize the compiler.
        
        Args:
            reports_dir_param: The parameter name used for the reports directory.
                              This can vary between deployments (default: REPORTS_DIR).
        """
        self.reports_dir_param = reports_dir_param
        self._detected_params: Set[str] = set()
    
    def compile(
        self,
        jrxml_path: Path,
        output_path: Optional[Path] = None,
        dry_run: bool = False
    ) -> CompilationResult:
        """
        Compile a JRXML template into a ZIP package.
        
        Args:
            jrxml_path: Path to the main JRXML file
            output_path: Output ZIP file path (default: <jrxml_name>.zip)
            dry_run: If True, don't create ZIP, just analyze dependencies
            
        Returns:
            CompilationResult with details about the compilation
        """
        result = CompilationResult(success=False)
        
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
        
        # Parse JRXML and extract asset references
        try:
            assets = self._extract_asset_references(jrxml_path, result)
            result.assets_found = assets
        except Exception as e:
            result.errors.append(f"Failed to parse JRXML: {e}")
            return result
        
        # Log detected parameter names
        if self._detected_params:
            params_str = ", ".join(sorted(self._detected_params))
            logger.info(f"Detected path parameters: {params_str}")
        
        # Resolve asset paths and check existence
        assets_to_include: List[Tuple[Path, str]] = []  # (absolute_path, archive_path)
        
        for asset in assets:
            asset_abs_path = (base_dir / asset.path).resolve()
            
            if asset.is_dynamic_dir:
                # This is a directory with dynamic filename - include all files
                if asset_abs_path.exists() and asset_abs_path.is_dir():
                    dir_files = list(asset_abs_path.iterdir())
                    file_count = 0
                    for file_path in dir_files:
                        if file_path.is_file():
                            # Build relative path for archive
                            rel_path = asset.path + file_path.name
                            assets_to_include.append((file_path, rel_path))
                            result.assets_included.append(file_path)
                            file_count += 1
                    
                    # Add warning about dynamic asset inclusion
                    result.warnings.append(
                        f"Dynamic asset: {asset.path}* (filename from {asset.dynamic_param}) - "
                        f"included all {file_count} files from directory"
                    )
                else:
                    result.assets_missing.append(asset)
                    result.warnings.append(
                        f"Directory not found: {asset.path} (referenced in {asset.source_file.name})"
                    )
            elif asset_abs_path.exists():
                result.assets_included.append(asset_abs_path)
                # Keep the relative path as-is for the archive
                assets_to_include.append((asset_abs_path, asset.path))
            else:
                result.assets_missing.append(asset)
                result.warnings.append(
                    f"Asset not found: {asset.path} (referenced in {asset.source_file.name})"
                )
        
        # Report findings
        logger.info(f"Found {len(result.assets_found)} asset references")
        logger.info(f"  - Included: {len(result.assets_included)}")
        logger.info(f"  - Missing: {len(result.assets_missing)}")
        
        if dry_run:
            result.success = True
            return result
        
        # Create ZIP archive
        try:
            self._create_zip(jrxml_path, assets_to_include, output_path)
            result.success = True
        except Exception as e:
            result.errors.append(f"Failed to create ZIP: {e}")
            return result
        
        return result
    
    def _extract_asset_references(
        self, 
        jrxml_path: Path,
        result: CompilationResult
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
                dynamic_param=dynamic_expr
            ))
        
        # Then find regular asset patterns
        for match in self.ASSET_PATTERN.finditer(content):
            param_name = match.group(1)
            asset_path = match.group(2)
            
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
                asset_type=asset_type
            ))
        
        return assets
    
    def _create_zip(
        self,
        jrxml_path: Path,
        assets: List[Tuple[Path, str]],
        output_path: Path
    ) -> None:
        """
        Create a ZIP archive with the JRXML and its assets.
        
        The ZIP structure preserves the relative paths of assets
        as they appear in the JRXML file.
        """
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
        
        logger.info(f"Created ZIP: {output_path}")
    
    def analyze(self, jrxml_path: Path) -> CompilationResult:
        """
        Analyze a JRXML file without creating a ZIP.
        
        This is equivalent to compile() with dry_run=True.
        """
        return self.compile(jrxml_path, dry_run=True)


def compile_template(
    jrxml_path: Path,
    output_path: Optional[Path] = None,
    dry_run: bool = False,
    reports_dir_param: str = "REPORTS_DIR"
) -> CompilationResult:
    """
    Convenience function to compile a JRXML template.
    
    Args:
        jrxml_path: Path to the main JRXML file
        output_path: Output ZIP file path (default: <jrxml_name>.zip)
        dry_run: If True, don't create ZIP, just analyze dependencies
        reports_dir_param: The parameter name used for the reports directory
        
    Returns:
        CompilationResult with details about the compilation
    """
    compiler = JRXMLCompiler(reports_dir_param=reports_dir_param)
    return compiler.compile(jrxml_path, output_path, dry_run)
