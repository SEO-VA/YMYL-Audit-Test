#!/usr/bin/env python3
"""
Logging utilities for YMYL Audit Tool

Centralized logging setup and helper functions.

FIXED: Improved import structure and error handling
"""

import logging
from datetime import datetime
from typing import Dict, Any, Union
import pytz

# Import settings with error handling
try:
    from config.settings import LOG_FORMAT, LOG_LEVEL, DEFAULT_TIMEZONE
except ImportError:
    # Fallback values if config is not available
    LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    LOG_LEVEL = 'INFO'
    DEFAULT_TIMEZONE = "Europe/Malta"


def setup_logger(name: str, level: Union[str, int] = None) -> logging.Logger:
    """
    Set up a logger with consistent formatting.
    
    Args:
        name (str): Name of the logger (usually __name__)
        level (str|int): Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    
    Returns:
        logging.Logger: Configured logger instance
    """
    if level is None:
        if isinstance(LOG_LEVEL, str):
            level = getattr(logging, LOG_LEVEL.upper(), logging.INFO)
        else:
            level = LOG_LEVEL
    elif isinstance(level, str):
        level = getattr(logging, level.upper(), logging.INFO)
    
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Avoid duplicate handlers
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(LOG_FORMAT)
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    
    return logger


def log_with_timestamp(message: str, timezone: str = DEFAULT_TIMEZONE) -> str:
    """
    Add timestamp to log message for UI display.
    
    Args:
        message (str): Log message
        timezone (str): Timezone for timestamp
        
    Returns:
        str: Formatted message with timestamp
    """
    try:
        tz = pytz.timezone(timezone)
        timestamp = datetime.now(tz).strftime('%H:%M:%S')
        return f"`{timestamp}`: {message}"
    except Exception as e:
        # Fallback to simple timestamp if timezone fails
        timestamp = datetime.now().strftime('%H:%M:%S')
        return f"`{timestamp}`: {message}"


def format_processing_step(step_name: str, status: str = "in_progress", details: str = None) -> str:
    """
    Format processing step for consistent UI display.
    
    Args:
        step_name (str): Name of the processing step
        status (str): Status ('in_progress', 'success', 'error', 'info')
        details (str): Additional details
        
    Returns:
        str: Formatted step message
    """
    icons = {
        'in_progress': '🔄',
        'success': '✅',
        'error': '❌',
        'info': 'ℹ️',
        'warning': '⚠️'
    }
    
    icon = icons.get(status, '•')
    message = f"{icon} {step_name}"
    
    if details:
        message += f": {details}"
    
    return message

def format_user_message(technical_message: str, context: str = "") -> str:
    """
    Convert technical messages to user-friendly ones.
    
    Args:
        technical_message (str): Original technical message
        context (str): Additional context about what's happening
        
    Returns:
        str: User-friendly version of the message
    """
    # Common technical terms and their user-friendly replacements
    replacements = {
        'chunk processor': 'content processor',
        'chunk processing': 'content processing',
        'unicode escapes': 'special characters',
        'selenium timeout': 'website loading timeout',
        'webdriver': 'browser automation',
        'json parsing': 'data format reading',
        'http error': 'website connection issue',
        'api key': 'access credentials',
        'processing workflow': 'analysis process',
        'extraction failed': 'could not get content',
        'validation error': 'format check failed'
    }
    
    # Convert to lowercase for matching
    user_message = technical_message.lower()
    
    # Apply replacements
    for technical_term, friendly_term in replacements.items():
        user_message = user_message.replace(technical_term, friendly_term)
    
    # Add context if provided
    if context:
        user_message = f"{context}: {user_message}"
    
    # Capitalize first letter
    user_message = user_message[0].upper() + user_message[1:] if user_message else ""
    
    return user_message

def create_simple_progress_message(step_name: str, current: int = None, total: int = None) -> str:
    """
    Create simple progress messages for normal users.
    
    Args:
        step_name (str): Name of the current step
        current (int): Current item number (optional)
        total (int): Total items (optional)
        
    Returns:
        str: Simple progress message
    """
    # Simplify step names
    simple_steps = {
        'content_extraction': 'Getting content from website',
        'chunk_processing': 'Processing content',
        'ai_analysis': 'Running AI analysis',
        'json_parsing': 'Reading data format',
        'unicode_decoding': 'Processing text',
        'validation': 'Checking format',
        'export_generation': 'Creating reports'
    }
    
    # Get simplified name or use original
    simple_name = simple_steps.get(step_name.lower(), step_name)
    
    # Add progress if provided
    if current is not None and total is not None and total > 0:
        percentage = (current / total) * 100
        return f"{simple_name} ({current}/{total} - {percentage:.0f}%)"
    else:
        return simple_name

def categorize_error_for_user(error_message: str, error_type: str = "") -> dict:
    """
    Categorize errors and provide user-friendly information.
    
    Args:
        error_message (str): Original error message
        error_type (str): Type of error if known
        
    Returns:
        dict: Error information with user-friendly details
    """
    error_info = {
        'category': 'general',
        'user_message': 'Something went wrong',
        'suggestion': 'Please try again',
        'technical_details': error_message
    }
    
    # Analyze the error message to categorize it
    error_lower = error_message.lower()
    
    if any(term in error_lower for term in ['timeout', 'timed out', 'time out']):
        error_info.update({
            'category': 'timeout',
            'user_message': 'The website took too long to respond',
            'suggestion': 'Try again, or check if the website is working in your browser'
        })
    
    elif any(term in error_lower for term in ['connection', 'network', 'dns', 'resolve']):
        error_info.update({
            'category': 'connection',
            'user_message': 'Could not connect to the website',
            'suggestion': 'Check your internet connection and verify the URL is correct'
        })
    
    elif any(term in error_lower for term in ['json', 'parse', 'format', 'invalid']):
        error_info.update({
            'category': 'format',
            'user_message': 'There is an issue with the data format',
            'suggestion': 'Check that your JSON follows the correct format'
        })
    
    elif any(term in error_lower for term in ['api', 'key', 'authentication', 'unauthorized']):
        error_info.update({
            'category': 'api',
            'user_message': 'Issue with AI analysis service access',
            'suggestion': 'Check your API key or try again in a moment'
        })
    
    elif any(term in error_lower for term in ['memory', 'large', 'size', 'limit']):
        error_info.update({
            'category': 'size',
            'user_message': 'The content is too large to process',
            'suggestion': 'Try with a smaller webpage or reduce your JSON content'
        })
    
    return error_info        

def format_metrics(metrics_dict: Dict[str, Any]) -> str:
    """
    Format metrics for display.
    
    Args:
        metrics_dict (dict): Dictionary of metric names and values
        
    Returns:
        str: Formatted metrics string
    """
    if not metrics_dict:
        return "No metrics available"
    
    formatted_metrics = []
    for key, value in metrics_dict.items():
        # Skip None values and internal fields
        if value is None or key.startswith('_'):
            continue
            
        try:
            if isinstance(value, (int, float)):
                if isinstance(value, float):
                    # Round to 2 decimal places for floats
                    if value >= 1000:
                        formatted_value = f"{value:,.2f}"
                    else:
                        formatted_value = f"{value:.2f}"
                else:
                    # Add thousands separator for large integers
                    formatted_value = f"{value:,}"
            elif isinstance(value, bool):
                formatted_value = "Yes" if value else "No"
            else:
                formatted_value = str(value)
            
            # Format key name (convert snake_case to Title Case)
            formatted_key = key.replace('_', ' ').title()
            formatted_metrics.append(f"{formatted_key}: {formatted_value}")
            
        except Exception as e:
            # If formatting fails, use string representation
            formatted_metrics.append(f"{key}: {str(value)}")
    
    return " | ".join(formatted_metrics)


def create_progress_message(completed: int, total: int, operation: str = "items") -> str:
    """
    Create a standardized progress message.
    
    Args:
        completed (int): Number of completed items
        total (int): Total number of items
        operation (str): Description of what's being processed
        
    Returns:
        str: Formatted progress message
    """
    if total <= 0:
        return f"Processing {operation}..."
    
    percentage = (completed / total) * 100
    return f"Processed {completed}/{total} {operation} ({percentage:.1f}%)"


def log_performance_metrics(logger: logging.Logger, operation: str, duration: float, 
                          items_processed: int = None, **kwargs) -> None:
    """
    Log performance metrics in a standardized format.
    
    Args:
        logger: Logger instance
        operation (str): Description of the operation
        duration (float): Duration in seconds
        items_processed (int): Number of items processed (optional)
        **kwargs: Additional metrics to log
    """
    try:
        metrics = {
            'operation': operation,
            'duration_seconds': round(duration, 3),
        }
        
        if items_processed is not None:
            metrics['items_processed'] = items_processed
            if duration > 0:
                metrics['items_per_second'] = round(items_processed / duration, 2)
        
        # Add any additional metrics
        metrics.update(kwargs)
        
        # Format for logging
        formatted_metrics = format_metrics(metrics)
        logger.info(f"Performance Metrics: {formatted_metrics}")
        
    except Exception as e:
        logger.warning(f"Error logging performance metrics: {e}")


def safe_log_exception(logger: logging.Logger, exception: Exception, 
                      context: str = None, level: str = "ERROR") -> str:
    """
    Safely log an exception with context.
    
    Args:
        logger: Logger instance
        exception: Exception to log
        context (str): Additional context information
        level (str): Log level to use
        
    Returns:
        str: Formatted error message for user display
    """
    try:
        error_msg = str(exception)
        exception_type = type(exception).__name__
        
        # Create detailed log message
        log_parts = [f"{exception_type}: {error_msg}"]
        if context:
            log_parts.insert(0, f"Context: {context}")
        
        detailed_message = " | ".join(log_parts)
        
        # Log at appropriate level
        log_level = getattr(logging, level.upper(), logging.ERROR)
        logger.log(log_level, detailed_message)
        
        # Return user-friendly message
        user_message = error_msg if error_msg else f"An {exception_type} occurred"
        if context:
            user_message = f"{context}: {user_message}"
            
        return user_message
        
    except Exception as logging_error:
        # Fallback if logging itself fails
        fallback_msg = f"Logging error: {logging_error}, Original error: {exception}"
        print(fallback_msg)  # Print to console as last resort
        return str(exception)


# Create a default logger for this module
logger = setup_logger(__name__)


# Backward compatibility - create module-level functions that were expected
def get_logger(name: str) -> logging.Logger:
    """Get or create a logger with the given name."""
    return setup_logger(name)


def format_timestamp(timezone: str = DEFAULT_TIMEZONE) -> str:
    """Get current timestamp formatted for the given timezone."""
    try:
        tz = pytz.timezone(timezone)
        return datetime.now(tz).strftime('%Y-%m-%d %H:%M:%S %Z')
    except Exception:
        return datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')


# Export commonly used functions
__all__ = [
    'setup_logger',
    'log_with_timestamp', 
    'format_processing_step',
    'format_metrics',
    'create_progress_message',
    'log_performance_metrics',
    'safe_log_exception',
    'get_logger',
    'format_timestamp',
    'format_user_message',              # NEW
    'create_simple_progress_message',   # NEW  
    'categorize_error_for_user',        # NEW
    'logger'
]