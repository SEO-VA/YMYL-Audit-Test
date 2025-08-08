#!/usr/bin/env python3
"""
Exporters Package for YMYL Audit Tool

Document export and generation components for multiple output formats.
"""

# Import main classes for easier access
try:
    from .export_manager import ExportManager
    from .html_exporter import HTMLExporter
    from .word_exporter import WordExporter
    from .pdf_exporter import PDFExporter
except ImportError as e:
    # If imports fail, create dummy logger to prevent crashes
    import logging
    logger = logging.getLogger(__name__)
    logger.error(f"Failed to import exporter modules: {e}")
    
    # Create placeholder classes to prevent import errors
    class ExportManager:
        def __init__(self, *args, **kwargs):
            raise ImportError("ExportManager could not be imported properly")
    
    class HTMLExporter:
        def __init__(self, *args, **kwargs):
            raise ImportError("HTMLExporter could not be imported properly")
    
    class WordExporter:
        def __init__(self, *args, **kwargs):
            raise ImportError("WordExporter could not be imported properly")
    
    class PDFExporter:
        def __init__(self, *args, **kwargs):
            raise ImportError("PDFExporter could not be imported properly")

__version__ = "1.0.0"
__all__ = [
    'ExportManager',
    'HTMLExporter',
    'WordExporter', 
    'PDFExporter'
]