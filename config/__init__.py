#!/usr/bin/env python3
"""
Config Package for YMYL Audit Tool

Configuration management and settings for the application.
"""

# Import main settings for easier access
try:
    from .settings import (
        # Core settings
        ANALYZER_ASSISTANT_ID,
        SELENIUM_TIMEOUT,
        CHUNK_API_URL,
        CHROME_OPTIONS,
        REQUEST_TIMEOUT,
        USER_AGENT,
        MAX_PARALLEL_REQUESTS,
        MAX_CONTENT_LENGTH,
        CHUNK_POLLING_INTERVAL,
        CHUNK_POLLING_TIMEOUT,
        DEFAULT_TIMEZONE,
        DEBUG_MODE_DEFAULT,
        LOG_FORMAT,
        LOG_LEVEL,
        
        # New configuration groups
        SESSION_MANAGEMENT,
        CONTENT_VALIDATION,
        AI_ANALYSIS,
        UI_SETTINGS,
        ERROR_HANDLING,
        PERFORMANCE,
        FEATURE_FLAGS,
        SECURITY,
        EXPORT_CONFIG,
        
        # Utility functions
        get_setting,
        validate_settings,
        get_timeout_config
    )
except ImportError as e:
    # If imports fail, create dummy logger and fallback values
    import logging
    logger = logging.getLogger(__name__)
    logger.error(f"Failed to import config modules: {e}")
    
    # Fallback values for critical settings
    ANALYZER_ASSISTANT_ID = "asst_WzODK9EapCaZoYkshT6x9xEH"
    SELENIUM_TIMEOUT = 180
    CHUNK_API_URL = "https://chunk.dejan.ai/"
    CHROME_OPTIONS = ['--headless=new', '--no-sandbox', '--disable-dev-shm-usage', '--disable-gpu']
    REQUEST_TIMEOUT = 30
    USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    DEFAULT_EXPORT_FORMATS = ['html', 'docx', 'pdf', 'markdown']
    MAX_PARALLEL_REQUESTS = 10
    MAX_CONTENT_LENGTH = 1000000
    CHUNK_POLLING_INTERVAL = 0.2
    CHUNK_POLLING_TIMEOUT = 30
    DEFAULT_TIMEZONE = "Europe/Malta"
    DEBUG_MODE_DEFAULT = True
    LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    LOG_LEVEL = 'INFO'
    
    # Empty configuration groups
    SESSION_MANAGEMENT = {}
    CONTENT_VALIDATION = {}
    AI_ANALYSIS = {}
    UI_SETTINGS = {}
    ERROR_HANDLING = {}
    PERFORMANCE = {}
    FEATURE_FLAGS = {}
    SECURITY = {}
    EXPORT_CONFIG = {}
    
    # Dummy utility functions
    def get_setting(key_path, default=None):
        return default
    
    def validate_settings():
        return True, []
    
    def get_timeout_config():
        return {
            'request_timeout': REQUEST_TIMEOUT,
            'selenium_timeout': SELENIUM_TIMEOUT,
            'chunk_polling_timeout': CHUNK_POLLING_TIMEOUT
        }

__version__ = "1.0.0"
__all__ = [
    # Core settings
    'ANALYZER_ASSISTANT_ID', 'SELENIUM_TIMEOUT', 'CHUNK_API_URL', 'CHROME_OPTIONS',
    'REQUEST_TIMEOUT', 'USER_AGENT', 'DEFAULT_EXPORT_FORMATS', 'MAX_PARALLEL_REQUESTS',
    'MAX_CONTENT_LENGTH', 'CHUNK_POLLING_INTERVAL', 'CHUNK_POLLING_TIMEOUT',
    'DEFAULT_TIMEZONE', 'DEBUG_MODE_DEFAULT', 'LOG_FORMAT', 'LOG_LEVEL',
    
    # Configuration groups
    'SESSION_MANAGEMENT', 'CONTENT_VALIDATION', 'AI_ANALYSIS', 'UI_SETTINGS',
    'ERROR_HANDLING', 'PERFORMANCE', 'FEATURE_FLAGS', 'SECURITY', 'EXPORT_CONFIG',
    
    # Utility functions
    'get_setting', 'validate_settings', 'get_timeout_config'
]