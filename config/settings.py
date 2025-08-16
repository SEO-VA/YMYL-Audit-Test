#!/usr/bin/env python3
"""
Configuration settings for YMYL Audit Tool
UPDATED: Single request architecture settings
"""

# AI Processing Configuration
ANALYZER_ASSISTANT_ID = "asst_WzODK9EapCaZoYkshT6x9xEH"

# Single Request Configuration
SINGLE_REQUEST_TIMEOUT = 300  # 5 minutes for full content analysis
MAX_CONTENT_SIZE_FOR_AI = 2000000  # 2MB limit for single request

# Selenium/Browser Configuration (unchanged)
SELENIUM_TIMEOUT = 180
SELENIUM_SHORT_TIMEOUT = 30
CHUNK_API_URL = "https://chunk.dejan.ai/"

# Browser Options (unchanged)
CHROME_OPTIONS = [
    '--headless=new',
    '--no-sandbox',
    '--disable-dev-shm-usage',
    '--disable-gpu'
]

# HTTP Configuration (unchanged)
REQUEST_TIMEOUT = 30
USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'

# Export Configuration (unchanged)
DEFAULT_EXPORT_FORMAT = 'docx'
SUPPORTED_EXPORT_FORMATS = ['docx']

# Content Processing Configuration (unchanged)
MAX_CONTENT_LENGTH = 1000000  # 1MB limit for content processing
CHUNK_POLLING_INTERVAL = 0.2
CHUNK_POLLING_TIMEOUT = 30

# UI Configuration (unchanged)
DEFAULT_TIMEZONE = "Europe/Malta"
DEBUG_MODE_DEFAULT = True

# Logging Configuration (unchanged)
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
LOG_LEVEL = 'INFO'

# Session management settings (simplified)
SESSION_MANAGEMENT = {
    'ANALYSIS_KEYS': [
        "latest_result",
        "ai_analysis_result", 
        "ai_report",
        "ai_stats",
        "analysis_statistics",
        "current_url_analysis",
        "processing_start_time"
    ],
    'MAX_HISTORY_ITEMS': 5,
    'AUTO_CLEANUP_THRESHOLD': 3600,
    'ENABLE_STALE_DETECTION': True,
    'DEBUG_SESSION_STATE': False
}

# Content validation settings (unchanged)
CONTENT_VALIDATION = {
    'MIN_CHUNK_LENGTH': 10,
    'MAX_SAFE_CONTENT_LENGTH': 500000,
    'MIN_CHUNKS_FOR_ANALYSIS': 1,
    'MIN_QUALITY_SCORE': 0.5,
    'ENABLE_CONTENT_HASHING': True
}

# AI Analysis Configuration (updated for single request)
AI_ANALYSIS = {
    'SINGLE_REQUEST_TIMEOUT': SINGLE_REQUEST_TIMEOUT,
    'MAX_RETRIES': 3,
    'RETRY_BACKOFF_MULTIPLIER': 2,
    'ENABLE_PROGRESS_TRACKING': True,
    'PROGRESS_UPDATE_INTERVAL': 0.5,
    'MAX_CONTENT_SIZE': MAX_CONTENT_SIZE_FOR_AI
}

# UI Enhancement Settings (simplified)
UI_SETTINGS = {
    'SHOW_ANALYSIS_CONTEXT': True,
    'SHOW_FRESHNESS_INDICATORS': True,
    'AUTO_SCROLL_TO_RESULTS': True,
    'SHOW_PROCESSING_STATS': True,
    'MAX_LOG_LINES': 50,
    'ENABLE_DEBUG_OPTIONS': True,
    'SIMPLE_PROGRESS_MODE': True,
    'SHOW_TECHNICAL_LOGS': False,
    'MAX_USER_FRIENDLY_MESSAGES': 5,
    'CONSOLIDATE_STATUS_MESSAGES': True
}

# Error Handling Configuration (unchanged)
ERROR_HANDLING = {
    'SHOW_DETAILED_ERRORS': False,
    'ENABLE_ERROR_REPORTING': True,
    'MAX_ERROR_MESSAGE_LENGTH': 200,
    'RETRY_CONFIG': {
        'content_extraction': {'max_retries': 3, 'backoff': 1.5},
        'chunk_processing': {'max_retries': 2, 'backoff': 2.0},
        'ai_analysis': {'max_retries': 3, 'backoff': 2.0}
    }
}

# Performance Monitoring (updated)
PERFORMANCE = {
    'ENABLE_MONITORING': True,
    'LOG_PERFORMANCE_METRICS': True,
    'THRESHOLDS': {
        'content_extraction': 30,
        'chunk_processing': 120,
        'single_ai_analysis': 300  # Updated for single request
    },
    'MONITOR_MEMORY_USAGE': True,
    'AUTO_CLEANUP_LARGE_OBJECTS': True
}

# Feature Flags (updated)
FEATURE_FLAGS = {
    'EXPERIMENTAL_FEATURES': False,
    'ENHANCED_PROGRESS_TRACKING': True,
    'CONTENT_VALIDATION': True,
    'STALE_RESULTS_DETECTION': True,
    'SESSION_STATE_DEBUG': False,
    'ADVANCED_ANALYTICS': True,
    'SINGLE_REQUEST_MODE': True  # NEW: Flag for single request architecture
}

# Security Configuration (unchanged)
SECURITY = {
    'SANITIZE_INPUTS': True,
    'MAX_URL_LENGTH': 2048,
    'ALLOWED_URL_SCHEMES': ['http', 'https'],
    'VALIDATE_CONTENT_TYPES': True,
    'MAX_FILE_SIZES': {
        'content': MAX_CONTENT_LENGTH,
        'json_output': 5 * 1024 * 1024,
        'exported_reports': 10 * 1024 * 1024,
        'ai_single_request': MAX_CONTENT_SIZE_FOR_AI  # NEW
    }
}

# Export and Download Configuration (unchanged)
EXPORT_CONFIG = {
    'FILENAME_PATTERN': 'ymyl_compliance_report_{timestamp}',
    'DEFAULT_FORMAT': 'docx',
    'SUPPORTED_FORMATS': ['docx'],
    'INCLUDE_METADATA': True,
    'GOOGLE_DOCS_COMPATIBLE': True,
    'MAX_EXPORT_SIZE': 50 * 1024 * 1024,
    'WORD_SETTINGS': {
        'USE_BUILTIN_STYLES': True,
        'EMOJI_TO_TEXT': True,
        'GOOGLE_DOCS_OPTIMIZED': True
    }
}


def get_setting(key_path: str, default=None):
    """Get setting value using dot notation."""
    try:
        import sys
        current_module = sys.modules[__name__]
        
        parts = key_path.split('.')
        value = current_module
        
        for part in parts:
            if hasattr(value, part):
                value = getattr(value, part)
            elif isinstance(value, dict) and part in value:
                value = value[part]
            else:
                return default
        
        return value
        
    except Exception:
        return default


def validate_settings():
    """Validate configuration settings."""
    errors = []
    
    try:
        # Validate timeout settings
        if SINGLE_REQUEST_TIMEOUT <= 0:
            errors.append("SINGLE_REQUEST_TIMEOUT must be positive")
        
        # Validate content limits
        if MAX_CONTENT_SIZE_FOR_AI <= 0:
            errors.append("MAX_CONTENT_SIZE_FOR_AI must be positive")
        
        if MAX_CONTENT_SIZE_FOR_AI > 10 * 1024 * 1024:  # 10MB warning
            errors.append("MAX_CONTENT_SIZE_FOR_AI is very large, may cause performance issues")
        
        # Validate session management
        max_history = SESSION_MANAGEMENT.get('MAX_HISTORY_ITEMS', 0)
        if max_history <= 0:
            errors.append("SESSION_MANAGEMENT.MAX_HISTORY_ITEMS must be positive")
        
        # Validate AI analysis settings
        max_retries = AI_ANALYSIS.get('MAX_RETRIES', 0)
        if max_retries <= 0:
            errors.append("AI_ANALYSIS.MAX_RETRIES must be positive")
        
        return len(errors) == 0, errors
        
    except Exception as e:
        return False, [f"Error validating settings: {str(e)}"]


def get_timeout_config():
    """Get all timeout-related configuration."""
    return {
        'request_timeout': REQUEST_TIMEOUT,
        'selenium_timeout': SELENIUM_TIMEOUT,
        'selenium_short_timeout': SELENIUM_SHORT_TIMEOUT,
        'chunk_polling_timeout': CHUNK_POLLING_TIMEOUT,
        'chunk_polling_interval': CHUNK_POLLING_INTERVAL,
        'single_request_timeout': SINGLE_REQUEST_TIMEOUT,  # NEW
        'auto_cleanup_threshold': SESSION_MANAGEMENT.get('AUTO_CLEANUP_THRESHOLD', 3600)
    }


def get_ai_config():
    """Get AI-related configuration."""
    return {
        'assistant_id': ANALYZER_ASSISTANT_ID,
        'single_request_timeout': SINGLE_REQUEST_TIMEOUT,
        'max_content_size': MAX_CONTENT_SIZE_FOR_AI,
        'max_retries': AI_ANALYSIS.get('MAX_RETRIES', 3),
        'retry_backoff': AI_ANALYSIS.get('RETRY_BACKOFF_MULTIPLIER', 2)
    }


# REMOVED SETTINGS (no longer needed):
# - MAX_PARALLEL_REQUESTS (no parallel processing)
# - Semaphore/concurrency settings
# - Per-chunk processing configurations


__all__ = [
    'ANALYZER_ASSISTANT_ID', 'SINGLE_REQUEST_TIMEOUT', 'MAX_CONTENT_SIZE_FOR_AI',
    'SELENIUM_TIMEOUT', 'CHUNK_API_URL', 'CHROME_OPTIONS',
    'REQUEST_TIMEOUT', 'USER_AGENT', 'DEFAULT_EXPORT_FORMAT', 'SUPPORTED_EXPORT_FORMATS',
    'MAX_CONTENT_LENGTH', 'CHUNK_POLLING_INTERVAL', 'CHUNK_POLLING_TIMEOUT',
    'DEFAULT_TIMEZONE', 'DEBUG_MODE_DEFAULT', 'LOG_FORMAT', 'LOG_LEVEL',
    'SESSION_MANAGEMENT', 'CONTENT_VALIDATION', 'AI_ANALYSIS', 'UI_SETTINGS',
    'ERROR_HANDLING', 'PERFORMANCE', 'FEATURE_FLAGS', 'SECURITY', 'EXPORT_CONFIG',
    'get_setting', 'validate_settings', 'get_timeout_config', 'get_ai_config'
]