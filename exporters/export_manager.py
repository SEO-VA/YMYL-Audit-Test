#!/usr/bin/env python3
"""
Export Manager for YMYL Audit Tool

Coordinates multiple export formats and provides a unified interface.
"""

import time
from datetime import datetime
from typing import Dict, Optional, List, Any
from exporters.html_exporter import HTMLExporter
from exporters.word_exporter import WordExporter
from exporters.pdf_exporter import PDFExporter
from config.settings import DEFAULT_EXPORT_FORMATS
from utils.logging_utils import setup_logger, format_processing_step

logger = setup_logger(__name__)


class ExportManager:
    """
    Manages export operations across multiple formats.
    
    Features:
    - Unified export interface
    - Format validation and selection
    - Progress tracking
    - Error handling and recovery
    - Export statistics and metadata
    """
    
    def __init__(self):
        """Initialize the ExportManager."""
        self.exporters = {
            'html': HTMLExporter(),
            'docx': WordExporter(),
            'pdf': PDFExporter()
        }
        self.supported_formats = list(self.exporters.keys()) + ['markdown']
        logger.info(f"ExportManager initialized with formats: {', '.join(self.supported_formats)}")

    def export_all_formats(self, 
                          markdown_content: str, 
                          title: str = "YMYL Compliance Audit Report",
                          formats: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Export report in all requested formats.
        
        Args:
            markdown_content (str): Markdown content to export
            title (str): Document title
            formats (list): List of formats to export (defaults to all)
            
        Returns:
            dict: Export results with data and metadata
        """
        logger.info(f"Starting multi-format export ({len(markdown_content):,} characters)")
        
        if formats is None:
            formats = DEFAULT_EXPORT_FORMATS
        
        # Validate formats
        valid_formats = self._validate_formats(formats)
        if not valid_formats:
            return self._create_error_result("No valid formats specified")
        
        # Validate content
        if not self._validate_content(markdown_content):
            return self._create_error_result("Invalid markdown content")
        
        start_time = time.time()
        results = {
            'success': True,
            'formats': {},
            'errors': {},
            'metadata': {
                'title': title,
                'formats_requested': formats,
                'formats_processed': [],
                'export_timestamp': datetime.now().isoformat(),
                'content_length': len(markdown_content),
                'processing_time': 0
            }
        }
        
        # Process each format
        for fmt in valid_formats:
            try:
                logger.info(f"Exporting to {fmt.upper()} format...")
                
                if fmt == 'markdown':
                    # Special case for markdown - just encode as UTF-8
                    results['formats'][fmt] = markdown_content.encode('utf-8')
                    results['metadata']['formats_processed'].append(fmt)
                else:
                    # Use appropriate exporter
                    exporter = self.exporters[fmt]
                    exported_data = exporter.convert(markdown_content, title)
                    results['formats'][fmt] = exported_data
                    results['metadata']['formats_processed'].append(fmt)
                
                logger.info(f"Successfully exported {fmt.upper()} format")
                
            except Exception as e:
                error_msg = f"Export failed for {fmt}: {str(e)}"
                logger.error(error_msg)
                results['errors'][fmt] = error_msg
        
        # Calculate final metadata
        processing_time = time.time() - start_time
        results['metadata']['processing_time'] = processing_time
        results['metadata']['successful_formats'] = len(results['formats'])
        results['metadata']['failed_formats'] = len(results['errors'])
        
        # Determine overall success
        if not results['formats']:
            results['success'] = False
            results['error'] = "All export formats failed"
        elif results['errors']:
            results['success'] = 'partial'  # Some succeeded, some failed
        
        logger.info(f"Multi-format export completed in {processing_time:.2f}s: "
                   f"{len(results['formats'])} successful, {len(results['errors'])} failed")
        
        return results

    def export_single_format(self, 
                            markdown_content: str, 
                            format_name: str,
                            title: str = "YMYL Compliance Audit Report") -> Dict[str, Any]:
        """
        Export report in a single format.
        
        Args:
            markdown_content (str): Markdown content to export
            format_name (str): Format to export ('html', 'docx', 'pdf', 'markdown')
            title (str): Document title
            
        Returns:
            dict: Export result with data and metadata
        """
        logger.info(f"Starting single format export: {format_name.upper()}")
        
        # Validate format
        if format_name not in self.supported_formats:
            return self._create_error_result(f"Unsupported format: {format_name}")
        
        # Validate content
        if not self._validate_content(markdown_content):
            return self._create_error_result("Invalid markdown content")
        
        start_time = time.time()
        
        try:
            if format_name == 'markdown':
                exported_data = markdown_content.encode('utf-8')
            else:
                exporter = self.exporters[format_name]
                exported_data = exporter.convert(markdown_content, title)
            
            processing_time = time.time() - start_time
            
            result = {
                'success': True,
                'format': format_name,
                'data': exported_data,
                'metadata': {
                    'title': title,
                    'format': format_name,
                    'export_timestamp': datetime.now().isoformat(),
                    'content_length': len(markdown_content),
                    'exported_size': len(exported_data),
                    'processing_time': processing_time
                }
            }
            
            logger.info(f"Successfully exported {format_name.upper()} format in {processing_time:.2f}s")
            return result
            
        except Exception as e:
            error_msg = f"Export failed for {format_name}: {str(e)}"
            logger.error(error_msg)
            return self._create_error_result(error_msg)

    def get_export_info(self, markdown_content: str) -> Dict[str, Any]:
        """
        Get information about exports without actually performing them.
        
        Args:
            markdown_content (str): Markdown content to analyze
            
        Returns:
            dict: Export information and estimates
        """
        info = {
            'content_analysis': {
                'character_count': len(markdown_content),
                'word_count_estimate': len(markdown_content.split()),
                'line_count': len(markdown_content.split('\n')),
                'is_valid': self._validate_content(markdown_content)
            },
            'supported_formats': self.supported_formats,
            'format_estimates': {}
        }
        
        # Get format-specific information
        for fmt_name, exporter in self.exporters.items():
            try:
                if hasattr(exporter, 'get_document_info'):
                    info['format_estimates'][fmt_name] = exporter.get_document_info(markdown_content)
                else:
                    info['format_estimates'][fmt_name] = {'available': False}
            except Exception as e:
                info['format_estimates'][fmt_name] = {'error': str(e)}
        
        # Markdown format info (simple)
        info['format_estimates']['markdown'] = {
            'file_size_estimate': f"{len(markdown_content.encode('utf-8')) // 1024}KB",
            'character_count': len(markdown_content),
            'encoding': 'UTF-8'
        }
        
        return info

    def validate_export_request(self, formats: List[str], content: str) -> Dict[str, Any]:
        """
        Validate an export request before processing.
        
        Args:
            formats (list): Requested export formats
            content (str): Content to export
            
        Returns:
            dict: Validation results
        """
        validation = {
            'valid': True,
            'errors': [],
            'warnings': [],
            'valid_formats': [],
            'invalid_formats': [],
            'content_valid': False
        }
        
        # Validate content
        validation['content_valid'] = self._validate_content(content)
        if not validation['content_valid']:
            validation['errors'].append("Content is empty or invalid")
            validation['valid'] = False
        
        # Validate formats
        for fmt in formats:
            if fmt in self.supported_formats:
                validation['valid_formats'].append(fmt)
            else:
                validation['invalid_formats'].append(fmt)
                validation['errors'].append(f"Unsupported format: {fmt}")
        
        if not validation['valid_formats']:
            validation['errors'].append("No valid formats specified")
            validation['valid'] = False
        
        # Content size warnings
        content_size = len(content)
        if content_size > 1000000:  # 1MB
            validation['warnings'].append(f"Large content size: {content_size:,} characters")
        
        if content_size > 2000000:  # 2MB
            validation['errors'].append("Content too large for reliable export")
            validation['valid'] = False
        
        return validation

    def get_format_capabilities(self) -> Dict[str, Dict[str, Any]]:
        """
        Get information about each export format's capabilities.
        
        Returns:
            dict: Format capabilities information
        """
        capabilities = {
            'html': {
                'name': 'HTML',
                'description': 'Styled web document',
                'features': ['responsive design', 'CSS styling', 'web browser compatible'],
                'best_for': ['web viewing', 'sharing online', 'responsive display'],
                'file_extension': '.html',
                'mime_type': 'text/html'
            },
            'docx': {
                'name
