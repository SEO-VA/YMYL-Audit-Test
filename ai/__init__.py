#!/usr/bin/env python3
"""
AI Package for YMYL Audit Tool

AI-powered analysis components for YMYL compliance checking.
"""

# Import main classes for easier access
try:
    from .analysis_engine import AnalysisEngine
    from .assistant_client import AssistantClient
except ImportError as e:
    # If imports fail, create dummy logger to prevent crashes
    import logging
    logger = logging.getLogger(__name__)
    logger.error(f"Failed to import AI modules: {e}")
    
    # Create placeholder classes to prevent import errors
    class AnalysisEngine:
        def __init__(self, *args, **kwargs):
            raise ImportError("AnalysisEngine could not be imported properly")
    
    class AssistantClient:
        def __init__(self, *args, **kwargs):
            raise ImportError("AssistantClient could not be imported properly")

__version__ = "1.0.0"
__all__ = [
    'AnalysisEngine',
    'AssistantClient'
]