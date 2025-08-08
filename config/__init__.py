#!/usr/bin/env python3
"""
Configuration module for YMYL Audit Tool
Centralized configuration management
"""

try:
    from .settings import (
        ANALYZER_ASSISTANT_ID,
        DEFAULT_EXPORT_FORMATS,
        MAX_PARALLEL_REQUESTS,
        SELENIUM_TIMEOUT,
        CHUNK_API_URL,
        DEFAULT_TIMEZONE,
        LOG_FORMAT,
        LOG_LEVEL
    )
except ImportError:
    # Fallback values if settings import fails
    ANALYZER_ASSISTANT_ID = "asst_WzODK9EapCaZoYkshT6x9xEH"
    DEFAULT_EXPORT_FORMATS = ["html", "pdf", "docx", "markdown"]
    MAX_PARALLEL_REQUESTS = 10
    SELENIUM_TIMEOUT = 180
    CHUNK_API_URL = "https://chunk.dejan.ai/"
    DEFAULT_TIMEZONE = "Europe/Malta"
    LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    LOG_LEVEL = 'INFO'

__all__ = [
    'ANALYZER_ASSISTANT_ID',
    'DEFAULT_EXPORT_FORMATS', 
    'MAX_PARALLEL_REQUESTS',
    'SELENIUM_TIMEOUT',
    'CHUNK_API_URL',
    'DEFAULT_TIMEZONE',
    'LOG_FORMAT',
    'LOG_LEVEL'
]
