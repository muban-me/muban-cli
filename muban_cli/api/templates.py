"""
Templates API - Template management and document generation.
"""

import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List
from urllib.parse import urljoin

import requests

from ._http import HTTPClient
from ..exceptions import APIError, ValidationError

logger = logging.getLogger(__name__)


class TemplatesAPI:
    """
    API for template management and document generation.
    
    Handles:
    - Template CRUD operations
    - Template parameters and fields
    - Document generation
    - Fonts and ICC profiles
    """
    
    def __init__(self, http: HTTPClient):
        """
        Initialize Templates API.
        
        Args:
            http: HTTP client instance
        """
        self._http = http
    
    def list(
        self,
        page: int = 1,
        size: int = 20,
        search: Optional[str] = None,
        description: Optional[str] = None,
        sort_by: Optional[str] = None,
        sort_dir: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        List templates with pagination.
        
        Args:
            page: Page number (1-indexed)
            size: Items per page
            search: Search term (searches across name, description, metadata)
            description: Filter by description specifically
            sort_by: Sort field (name, author, created, fileSize)
            sort_dir: Sort direction (asc, desc)
        
        Returns:
            Paginated list of templates
        """
        params: Dict[str, Any] = {"page": page, "size": size}
        if search:
            params["search"] = search
        if description:
            params["description"] = description
        if sort_by:
            params["sortBy"] = sort_by
        if sort_dir:
            params["sortDir"] = sort_dir
        
        return self._http.request("GET", "templates", params=params)
    
    def get(self, template_id: str) -> Dict[str, Any]:
        """
        Get template details.
        
        Args:
            template_id: Template UUID
        
        Returns:
            Template details
        """
        return self._http.request("GET", f"templates/{template_id}")
    
    def get_parameters(self, template_id: str) -> Dict[str, Any]:
        """
        Get template parameters.
        
        Args:
            template_id: Template UUID
        
        Returns:
            List of template parameters
        """
        return self._http.request("GET", f"templates/{template_id}/params")
    
    def get_fields(self, template_id: str) -> Dict[str, Any]:
        """
        Get template fields.
        
        Args:
            template_id: Template UUID
        
        Returns:
            List of template fields
        """
        return self._http.request("GET", f"templates/{template_id}/fields")
    
    def upload(
        self,
        file_path: Path,
        name: str,
        author: str,
        description: Optional[str] = None,
        metadata: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Upload a new template.
        
        Args:
            file_path: Path to ZIP file
            name: Template name
            author: Template author
            description: Optional human-readable description (max 1000 chars)
            metadata: Optional metadata (JSON string for S2S integration)
        
        Returns:
            Uploaded template details
        """
        if not file_path.exists():
            raise ValidationError(f"File not found: {file_path}")
        
        if not file_path.suffix.lower() == '.zip':
            raise ValidationError("Template must be a ZIP file")
        
        with open(file_path, 'rb') as f:
            files = {
                'file': (file_path.name, f, 'application/zip'),
            }
            data = {
                'name': name,
                'author': author,
            }
            if description:
                data['description'] = description
            if metadata:
                data['metadata'] = metadata
            
            url = urljoin(self._http.base_url, "templates/upload")
            headers = self._http._get_headers()
            
            response = self._http.session.post(
                url,
                data=data,
                files=files,
                headers=headers,
                timeout=self._http.config.timeout,
                verify=self._http.config.verify_ssl,
            )
            
            return self._http._handle_response(response)
    
    def download(
        self,
        template_id: str,
        output_path: Optional[Path] = None
    ) -> Path:
        """
        Download a template.
        
        Args:
            template_id: Template UUID
            output_path: Optional output path
        
        Returns:
            Path to downloaded file
        """
        if output_path is None:
            output_path = Path(f"{template_id}.zip")
        
        return self._http.download(f"templates/{template_id}/download", output_path)
    
    def delete(self, template_id: str) -> Dict[str, Any]:
        """
        Delete a template.
        
        Args:
            template_id: Template UUID
        
        Returns:
            Success response
        """
        return self._http.request(
            "DELETE",
            f"templates/{template_id}",
            expected_status=[200, 204]
        )
    
    def generate(
        self,
        template_id: str,
        output_format: str,
        parameters: List[Dict[str, Any]],
        output_path: Optional[Path] = None,
        filename: Optional[str] = None,
        data: Optional[Dict[str, Any]] = None,
        document_locale: Optional[str] = None,
        pdf_export_options: Optional[Dict[str, Any]] = None,
        html_export_options: Optional[Dict[str, Any]] = None,
        txt_export_options: Optional[Dict[str, Any]] = None,
        ignore_pagination: bool = False
    ) -> Path:
        """
        Generate a document from a template.
        
        Args:
            template_id: Template UUID
            output_format: Output format (pdf, xlsx, docx, rtf, html, txt)
            parameters: List of parameter name/value pairs
            output_path: Optional output path
            filename: Optional custom filename
            data: Optional JSON data source
            document_locale: Optional locale (e.g., 'en_US', 'pl_PL')
            pdf_export_options: PDF-specific options
            html_export_options: HTML-specific options
            txt_export_options: TXT-specific options
            ignore_pagination: Whether to ignore pagination
        
        Returns:
            Path to generated document
        """
        request_data: Dict[str, Any] = {"parameters": parameters}
        
        if filename:
            request_data["filename"] = filename
        if data:
            request_data["data"] = data
        if document_locale:
            request_data["documentLocale"] = document_locale
        if pdf_export_options:
            request_data["pdfExportOptions"] = pdf_export_options
        if html_export_options:
            request_data["htmlExportOptions"] = html_export_options
        if txt_export_options:
            request_data["txtExportOptions"] = txt_export_options
        if ignore_pagination:
            request_data["ignorePagination"] = ignore_pagination
        
        logger.debug("Generate document request body: %s", json.dumps(request_data, indent=2, ensure_ascii=False))
        
        url = urljoin(self._http.base_url, f"templates/{template_id}/generate/{output_format}")
        headers = self._http._get_headers({"Content-Type": "application/json"})
        
        try:
            response = self._http.session.post(
                url,
                json=request_data,
                headers=headers,
                timeout=self._http.config.timeout * 2,
                verify=self._http.config.verify_ssl,
                stream=True,
            )
        except requests.exceptions.RequestException as e:
            raise APIError(f"Document generation failed: {e}")
        
        if response.status_code != 200:
            self._http._handle_response(response)
        
        if output_path is None:
            content_disposition = response.headers.get('Content-Disposition', '')
            if 'filename=' in content_disposition:
                fname = content_disposition.split('filename=')[1].strip('"\'')
            else:
                fname = filename or f"document.{output_format}"
            output_path = Path(fname)
        
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        return output_path
    
    def generate_raw(
        self,
        template_id: str,
        output_format: str,
        request_data: Dict[str, Any],
        output_path: Optional[Path] = None
    ) -> Path:
        """
        Generate a document with a raw request body.
        
        Args:
            template_id: Template UUID
            output_format: Output format (pdf, xlsx, docx, rtf, html)
            request_data: Full request body as dict
            output_path: Optional output path
        
        Returns:
            Path to generated document
        """
        url = urljoin(self._http.base_url, f"templates/{template_id}/generate/{output_format}")
        headers = self._http._get_headers({"Content-Type": "application/json"})
        
        try:
            response = self._http.session.post(
                url,
                json=request_data,
                headers=headers,
                timeout=self._http.config.timeout * 2,
                verify=self._http.config.verify_ssl,
                stream=True,
            )
        except requests.exceptions.RequestException as e:
            raise APIError(f"Document generation failed: {e}")
        
        if response.status_code != 200:
            self._http._handle_response(response)
        
        if output_path is None:
            content_disposition = response.headers.get('Content-Disposition', '')
            if 'filename=' in content_disposition:
                fname = content_disposition.split('filename=')[1].strip('"\'')
            else:
                fname = f"document.{output_format}"
            output_path = Path(fname)
        
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        return output_path
    
    def get_fonts(self) -> Dict[str, Any]:
        """Get available fonts."""
        return self._http.request("GET", "templates/fonts")
    
    def get_icc_profiles(self) -> Dict[str, Any]:
        """Get available ICC profiles."""
        return self._http.request("GET", "templates/icc-profiles")
