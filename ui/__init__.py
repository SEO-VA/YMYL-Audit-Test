#!/usr/bin/env python3
"""
UI Package for YMYL Audit Tool

User interface components and Streamlit-specific functionality.
"""

# Import main functions for easier access
try:
    from .components import (
        create_page_header,
        create_sidebar_config,
        create_how_it_works_section,
        create_url_input_section,
        create_debug_logger,
        create_simple_progress_tracker,
        create_ai_analysis_section,
        create_results_tabs,
        create_ai_processing_interface,
        display_error_message,
        display_success_message,
        create_info_panel
    )
except ImportError as e:
    # If imports fail, create dummy logger to prevent crashes
    import logging
    logger = logging.getLogger(__name__)
    logger.error(f"Failed to import UI modules: {e}")
    
    # Create placeholder functions to prevent import errors
    def create_page_header(*args, **kwargs):
        raise ImportError("UI components could not be imported properly")
    
    def create_sidebar_config(*args, **kwargs):
        raise ImportError("UI components could not be imported properly")
    
    def create_how_it_works_section(*args, **kwargs):
        raise ImportError("UI components could not be imported properly")
    
    def create_url_input_section(*args, **kwargs):
        raise ImportError("UI components could not be imported properly")
    
    def create_debug_logger(*args, **kwargs):
        raise ImportError("UI components could not be imported properly")
    
    def create_simple_progress_tracker(*args, **kwargs):
        raise ImportError("UI components could not be imported properly")
    
    def create_ai_analysis_section(*args, **kwargs):
        raise ImportError("UI components could not be imported properly")
    
    def create_results_tabs(*args, **kwargs):
        raise ImportError("UI components could not be imported properly")
    
    def create_ai_processing_interface(*args, **kwargs):
        raise ImportError("UI components could not be imported properly")
    
    def display_error_message(*args, **kwargs):
        raise ImportError("UI components could not be imported properly")
    
    def display_success_message(*args, **kwargs):
        raise ImportError("UI components could not be imported properly")
    
    def create_info_panel(*args, **kwargs):
        raise ImportError("UI components could not be imported properly")

__version__ = "1.0.0"
__all__ = [
    'create_page_header',
    'create_sidebar_config', 
    'create_how_it_works_section',
    'create_url_input_section',
    'create_debug_logger',
    'create_simple_progress_tracker',
    'create_ai_analysis_section',
    'create_results_tabs',
    'create_ai_processing_interface',
    'display_error_message',
    'display_success_message',
    'create_info_panel'
]