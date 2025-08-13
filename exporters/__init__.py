#!/usr/bin/env python3
"""
Exporters Package for YMYL Audit Tool

Document export components - Word format only.
Optimized for Google Docs compatibility.
"""

# Import Word exporter only
try:
    from .word_exporter import WordExporter
except ImportError as e:
    # If imports fail, create dummy logger to prevent crashes
    import logging
    logger = logging.getLogger(__name__)
    logger.error(f"Failed to import word exporter: {e}")
    
    # Create placeholder class to prevent import errors
    class WordExporter:
        def __init__(self, *args, **kwargs):
            raise ImportError("WordExporter could not be imported properly")

__version__ = "1.0.0"
__all__ = [
    'WordExporter'
]