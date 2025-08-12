#!/usr/bin/env python3
"""
Configuration settings for YMYL Audit Tool

Centralized configuration management for all application settings.

FIXED: Enhanced with settings for stale results prevention and session management
"""

# AI Processing Configuration
ANALYZER_ASSISTANT_ID = "asst_WzODK9EapCaZoYkshT6x9xEH"

# Selenium/Browser Configuration
SELENIUM_TIMEOUT = 180
SELENIUM_SHORT_TIMEOUT = 30
CHUNK_API_URL = "https://chunk.dejan.ai/"

# Browser Options
CHROME_OPTIONS = [
    '--headless=new',
    '--no-sandbox',
    '--disable-dev-shm-usage',
    '--disable-gpu'
]

# HTTP Configuration
REQUEST_TIMEOUT = 30
USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'

# Export Configuration
DEFAULT_EXPORT_FORMATS = ['html', 'docx', 'pdf', 'markdown']
MAX_PARALLEL_REQUESTS = 10

# Content Processing Configuration
MAX_CONTENT_LENGTH = 1000000  # 1MB limit for content processing
CHUNK_POLLING_INTERVAL = 0.2  # seconds
CHUNK_POLLING_TIMEOUT = 30    # FIXED: Increased from 10 to 30 seconds for more reliable processing

# UI Configuration
DEFAULT_TIMEZONE = "Europe/Malta"
DEBUG_MODE_DEFAULT = True

# Logging Configuration
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
LOG_LEVEL = 'INFO'

# FIXED: New settings for stale results prevention and session management
SESSION_MANAGEMENT = {
    # Session state keys that should be cleared when starting new URL analysis
    'ANALYSIS_KEYS': [
        "latest_result",
        "ai_analysis_result", 
        "ai_report",
        "ai_stats",
        "analysis_statistics",
        "current_url_analysis",
        "processing_start_time",
        "chunk_analysis_results"
    ],
    
    # Maximum number of results to keep in session history
    'MAX_HISTORY_ITEMS': 5,
    
    # Automatic cleanup threshold (seconds) - auto-clear results older than this
    'AUTO_CLEANUP_THRESHOLD': 3600,  # 1 hour
    
    # Enable/disable automatic stale detection
    'ENABLE_STALE_DETECTION': True,
    
    # Show debug info for session management
    'DEBUG_SESSION_STATE': False
}

# Content validation settings
CONTENT_VALIDATION = {
    # Minimum content length for valid chunks
    'MIN_CHUNK_LENGTH': 10,
    
    # Maximum content length before warning
    'MAX_SAFE_CONTENT_LENGTH': 500000,  # 500KB
    
    # Minimum number of chunks required for AI analysis
    'MIN_CHUNKS_FOR_ANALYSIS': 1,
    
    # Content quality threshold (0.0 to 1.0)
    'MIN_QUALITY_SCORE': 0.5,
    
    # Enable content hash validation
    'ENABLE_CONTENT_HASHING': True
}

# AI Analysis Configuration
AI_ANALYSIS = {
    # Timeout for individual chunk analysis (seconds)
    'CHUNK_ANALYSIS_TIMEOUT': 300,
    
    # Maximum retries for failed chunks
    'MAX_CHUNK_RETRIES': 3,
    
    # Backoff multiplier for retries
    'RETRY_BACKOFF_MULTIPLIER': 2,
    
    # Enable progress tracking enhancements
    'ENABLE_PROGRESS_TRACKING': True,
    
    # Progress update interval (for UI responsiveness)
    'PROGRESS_UPDATE_INTERVAL': 0.1,
    
    # Parallel processing limits
    'MAX_CONCURRENT_ANALYSES': 10,
    'MIN_CONCURRENT_ANALYSES': 1
}

# UI Enhancement Settings
UI_SETTINGS = {
    # Show detailed analysis context
    'SHOW_ANALYSIS_CONTEXT': True,
    
    # Enable freshness indicators
    'SHOW_FRESHNESS_INDICATORS': True,
    
    # Auto-scroll to results after processing
    'AUTO_SCROLL_TO_RESULTS': True,
    
    # Show processing statistics
    'SHOW_PROCESSING_STATS': True,
    
    # Maximum number of log lines to display
    'MAX_LOG_LINES': 50,
    
    # Maximum number of milestones in simple progress
    'MAX_PROGRESS_MILESTONES': 10,
    
    # Enable advanced debug options
    'ENABLE_DEBUG_OPTIONS': True,
    
    # Enable advanced debug options
    'ENABLE_DEBUG_OPTIONS': True,

    # NEW: User-friendly logging settings
    'SIMPLE_PROGRESS_MODE': True,
    'SHOW_TECHNICAL_LOGS': False,
    'MAX_USER_FRIENDLY_MESSAGES': 5,
    'CONSOLIDATE_STATUS_MESSAGES': True
}

# Error Handling Configuration
ERROR_HANDLING = {
    # Show detailed error messages to users
    'SHOW_DETAILED_ERRORS': False,
    
    # Enable error reporting/logging
    'ENABLE_ERROR_REPORTING': True,
    
    # Maximum error message length for UI
    'MAX_ERROR_MESSAGE_LENGTH': 200,
    
    # Retry configuration for various operations
    'RETRY_CONFIG': {
        'content_extraction': {'max_retries': 3, 'backoff': 1.5},
        'chunk_processing': {'max_retries': 2, 'backoff': 2.0},
        'ai_analysis': {'max_retries': 3, 'backoff': 2.0}
    }
}

# Performance Monitoring
PERFORMANCE = {
    # Enable performance monitoring
    'ENABLE_MONITORING': True,
    
    # Log performance metrics
    'LOG_PERFORMANCE_METRICS': True,
    
    # Performance thresholds for warnings
    'THRESHOLDS': {
        'content_extraction': 30,     # seconds
        'chunk_processing': 120,      # seconds  
        'ai_analysis_per_chunk': 60   # seconds
    },
    
    # Memory usage monitoring
    'MONITOR_MEMORY_USAGE': True,
    
    # Clear large objects after processing
    'AUTO_CLEANUP_LARGE_OBJECTS': True
}

# Feature Flags
FEATURE_FLAGS = {
    # Enable experimental features
    'EXPERIMENTAL_FEATURES': False,
    
    # Enable enhanced progress tracking
    'ENHANCED_PROGRESS_TRACKING': True,
    
    # Enable content validation
    'CONTENT_VALIDATION': True,
    
    # Enable stale results detection
    'STALE_RESULTS_DETECTION': True,
    
    # Enable session state debugging
    'SESSION_STATE_DEBUG': False,
    
    # Enable advanced analytics
    'ADVANCED_ANALYTICS': True
}

# Security Configuration
SECURITY = {
    # Sanitize user inputs
    'SANITIZE_INPUTS': True,
    
    # Maximum URL length
    'MAX_URL_LENGTH': 2048,
    
    # Allowed URL schemes
    'ALLOWED_URL_SCHEMES': ['http', 'https'],
    
    # Enable content type validation
    'VALIDATE_CONTENT_TYPES': True,
    
    # Maximum file sizes for various operations
    'MAX_FILE_SIZES': {
        'content': MAX_CONTENT_LENGTH,
        'json_output': 5 * 1024 * 1024,  # 5MB
        'exported_reports': 10 * 1024 * 1024  # 10MB
    }
}

# Export and Download Configuration
EXPORT_CONFIG = {
    # Default filename pattern
    'FILENAME_PATTERN': 'ymyl_compliance_report_{timestamp}',
    
    # Include metadata in exports
    'INCLUDE_METADATA': True,
    
    # Compression for large exports
    'ENABLE_COMPRESSION': False,
    
    # Watermark for exported documents
    'ADD_WATERMARK': True,
    
    # Maximum export file size before warning
    'MAX_EXPORT_SIZE': 50 * 1024 * 1024  # 50MB
}

# Development and Testing
DEVELOPMENT = {
    # Enable development mode features
    'DEV_MODE': False,
    
    # Show internal timestamps and IDs
    'SHOW_INTERNAL_DATA': False,
    
    # Enable test data generation
    'ENABLE_TEST_DATA': False,
    
    # Mock external services (for testing)
    'MOCK_EXTERNAL_SERVICES': False,
    
    # Additional logging for development
    'VERBOSE_LOGGING': False
}

# Backward Compatibility
COMPATIBILITY = {
    # Support legacy session state keys
    'SUPPORT_LEGACY_KEYS': True,
    
    # Migrate old session data format
    'AUTO_MIGRATE_SESSION_DATA': True,
    
    # Legacy timeout values
    'LEGACY_TIMEOUTS': {
        'chunk_polling': 10  # Original timeout for reference
    }
}


def get_setting(key_path: str, default=None):
    """
    Get a setting value using dot notation.
    
    FIXED: New utility function for accessing nested settings
    
    Args:
        key_path (str): Dot-separated path to setting (e.g., 'SESSION_MANAGEMENT.ENABLE_STALE_DETECTION')
        default: Default value if setting not found
        
    Returns:
        Setting value or default
    """
    try:
        # Import current module to access settings
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
    """
    Validate configuration settings for consistency.
    
    FIXED: New function to ensure settings are valid
    
    Returns:
        tuple: (is_valid, errors_list)
    """
    errors = []
    
    try:
        # Validate timeout settings
        if CHUNK_POLLING_TIMEOUT <= CHUNK_POLLING_INTERVAL:
            errors.append("CHUNK_POLLING_TIMEOUT must be greater than CHUNK_POLLING_INTERVAL")
        
        # Validate content limits
        if MAX_CONTENT_LENGTH <= 0:
            errors.append("MAX_CONTENT_LENGTH must be positive")
        
        # Validate AI settings
        if MAX_PARALLEL_REQUESTS <= 0:
            errors.append("MAX_PARALLEL_REQUESTS must be positive")
        
        # Validate session management settings
        max_history = SESSION_MANAGEMENT.get('MAX_HISTORY_ITEMS', 0)
        if max_history <= 0:
            errors.append("SESSION_MANAGEMENT.MAX_HISTORY_ITEMS must be positive")
        
        # Validate content validation settings
        min_quality = CONTENT_VALIDATION.get('MIN_QUALITY_SCORE', 0)
        if not (0 <= min_quality <= 1):
            errors.append("CONTENT_VALIDATION.MIN_QUALITY_SCORE must be between 0 and 1")
        
        return len(errors) == 0, errors
        
    except Exception as e:
        return False, [f"Error validating settings: {str(e)}"]


def get_timeout_config():
    """
    Get all timeout-related configuration in one place.
    
    FIXED: Utility function for timeout management
    
    Returns:
        dict: All timeout settings
    """
    return {
        'request_timeout': REQUEST_TIMEOUT,
        'selenium_timeout': SELENIUM_TIMEOUT,
        'selenium_short_timeout': SELENIUM_SHORT_TIMEOUT,
        'chunk_polling_timeout': CHUNK_POLLING_TIMEOUT,
        'chunk_polling_interval': CHUNK_POLLING_INTERVAL,
        'ai_analysis_timeout': AI_ANALYSIS.get('CHUNK_ANALYSIS_TIMEOUT', 300),
        'auto_cleanup_threshold': SESSION_MANAGEMENT.get('AUTO_CLEANUP_THRESHOLD', 3600)
    }


# FIXED: Export important configuration groups for easy access
__all__ = [
    # Original exports
    'ANALYZER_ASSISTANT_ID', 'SELENIUM_TIMEOUT', 'CHUNK_API_URL', 'CHROME_OPTIONS',
    'REQUEST_TIMEOUT', 'USER_AGENT', 'DEFAULT_EXPORT_FORMATS', 'MAX_PARALLEL_REQUESTS',
    'MAX_CONTENT_LENGTH', 'CHUNK_POLLING_INTERVAL', 'CHUNK_POLLING_TIMEOUT',
    'DEFAULT_TIMEZONE', 'DEBUG_MODE_DEFAULT', 'LOG_FORMAT', 'LOG_LEVEL',
    
    # New configuration groups
    'SESSION_MANAGEMENT', 'CONTENT_VALIDATION', 'AI_ANALYSIS', 'UI_SETTINGS',
    'ERROR_HANDLING', 'PERFORMANCE', 'FEATURE_FLAGS', 'SECURITY', 'EXPORT_CONFIG',
    'DEVELOPMENT', 'COMPATIBILITY',
    
    # Utility functions
    'get_setting', 'validate_settings', 'get_timeout_config'
]