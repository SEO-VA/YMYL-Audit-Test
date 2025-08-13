#!/usr/bin/env python3
"""
Exporters Package for YMYL Audit Tool

Document export and generation components for multiple output formats.
"""

# Import main classes for easier access
    try:
    from .word_exporter import WordExporter
    except ImportError as e:
    import logging
    logger = logging.getLogger(__name__)
    logger.error(f"Failed to import word exporter: {e}")
    
    class WordExporter:
        def __init__(self, *args, **kwargs):
            raise ImportError("WordExporter could not be imported properly")
 
__version__ = "1.0.0"
__all__ = ['WordExporter']