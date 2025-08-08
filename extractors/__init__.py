#!/usr/bin/env python3
"""
Extractors Package for YMYL Audit Tool

Content extraction components for web scraping and data processing.
"""

# Import main classes for easier access
try:
    from .content_extractor import ContentExtractor
except ImportError as e:
    # If imports fail, create dummy logger to prevent crashes
    import logging
    logger = logging.getLogger(__name__)
    logger.error(f"Failed to import extractor modules: {e}")
    
    # Create placeholder class to prevent import errors
    class ContentExtractor:
        def __init__(self, *args, **kwargs):
            raise ImportError("ContentExtractor could not be imported properly")

__version__ = "1.0.0"
__all__ = [
    'ContentExtractor'
]