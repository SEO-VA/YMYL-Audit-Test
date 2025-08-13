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
                'name': 'Microsoft Word',
                'description': 'Editable business document',
                'features': ['professional formatting', 'editable', 'widely supported'],
                'best_for': ['business reports', 'editing', 'collaboration'],
                'file_extension': '.docx',
                'mime_type': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
            },
            'pdf': {
                'name': 'PDF',
                'description': 'Portable document format',
                'features': ['fixed formatting', 'print-ready', 'universal compatibility'],
                'best_for': ['presentations', 'archival', 'professional distribution'],
                'file_extension': '.pdf',
                'mime_type': 'application/pdf'
            },
            'markdown': {
                'name': 'Markdown',
                'description': 'Plain text with formatting syntax',
                'features': ['lightweight', 'version control friendly', 'platform independent'],
                'best_for': ['developers', 'documentation', 'version control'],
                'file_extension': '.md',
                'mime_type': 'text/markdown'
            }
        }
        
        return capabilities

    def _validate_formats(self, formats: List[str]) -> List[str]:
        """
        Validate and filter requested formats.
        
        Args:
            formats (list): Requested formats
            
        Returns:
            list: Valid formats only
        """
        valid_formats = []
        for fmt in formats:
            if fmt in self.supported_formats:
                valid_formats.append(fmt)
            else:
                logger.warning(f"Skipping unsupported format: {fmt}")
        
        return valid_formats

    def _validate_content(self, content: str) -> bool:
        """
        Validate markdown content.
        
        Args:
            content (str): Content to validate
            
        Returns:
            bool: True if valid, False otherwise
        """
        try:
            if not content or not content.strip():
                logger.error("Content is empty")
                return False
            
            # Check for reasonable size limits
            if len(content) > 5000000:  # 5MB limit
                logger.error(f"Content too large: {len(content):,} characters")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Content validation error: {e}")
            return False

    def _create_error_result(self, error_message: str) -> Dict[str, Any]:
        """
        Create standardized error result.
        
        Args:
            error_message (str): Error description
            
        Returns:
            dict: Error result structure
        """
        return {
            'success': False,
            'error': error_message,
            'formats': {},
            'metadata': {
                'export_timestamp': datetime.now().isoformat(),
                'error': error_message
            }
        }

    def get_recommended_formats(self, use_case: str = "general") -> List[str]:
        """
        Get recommended export formats for different use cases.
        
        Args:
            use_case (str): Use case ('general', 'business', 'web', 'archive')
            
        Returns:
            list: Recommended formats
        """
        recommendations = {
            'general': ['html', 'pdf', 'markdown'],
            'business': ['docx', 'pdf'],
            'web': ['html', 'markdown'],
            'archive': ['pdf', 'html'],
            'development': ['markdown', 'html'],
            'presentation': ['pdf', 'html']
        }
        
        return recommendations.get(use_case, ['html', 'pdf', 'markdown'])

    def create_filename(self, base_name: str, format_name: str, include_timestamp: bool = True) -> str:
        """
        Create appropriate filename for export format.
        
        Args:
            base_name (str): Base filename (without extension)
            format_name (str): Export format
            include_timestamp (bool): Whether to include timestamp
            
        Returns:
            str: Complete filename with extension
        """
        # Clean base name
        clean_name = "".join(c for c in base_name if c.isalnum() or c in (' ', '-', '_')).strip()
        clean_name = clean_name.replace(' ', '_').lower()
        
        # Add timestamp if requested
        if include_timestamp:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            clean_name = f"{clean_name}_{timestamp}"
        
        # Get file extension
        capabilities = self.get_format_capabilities()
        extension = capabilities.get(format_name, {}).get('file_extension', f'.{format_name}')
        
        return f"{clean_name}{extension}"

    def get_export_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about export capabilities and performance.
        
        Returns:
            dict: Export statistics
        """
        stats = {
            'supported_formats': len(self.supported_formats),
            'available_exporters': len(self.exporters),
            'formats': self.supported_formats,
            'capabilities': self.get_format_capabilities(),
            'recommendations': {
                use_case: self.get_recommended_formats(use_case)
                for use_case in ['general', 'business', 'web', 'archive', 'development', 'presentation']
            }
        }
        
        return stats

    def cleanup(self):
        """Clean up any resources used by exporters."""
        try:
            for exporter in self.exporters.values():
                if hasattr(exporter, 'cleanup'):
                    exporter.cleanup()
            logger.info("ExportManager cleanup completed")
        except Exception as e:
            logger.warning(f"Error during cleanup: {e}")

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit with cleanup."""
        self.cleanup()
