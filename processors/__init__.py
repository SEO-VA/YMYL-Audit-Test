#!/usr/bin/env python3
"""
Processors Package for YMYL Audit Tool

Content processing components for chunk processing and data transformation.
"""

# Import main classes for easier access
try:
    from .chunk_processor import ChunkProcessor
except ImportError as e:
    # If imports fail, create dummy logger to prevent crashes
    import logging
    logger = logging.getLogger(__name__)
    logger.error(f"Failed to import processor modules: {e}")
    
    # Create placeholder class to prevent import errors
    class ChunkProcessor:
        def __init__(self, *args, **kwargs):
            raise ImportError("ChunkProcessor could not be imported properly")

__version__ = "1.0.0"
__all__ = [
    'ChunkProcessor'
]