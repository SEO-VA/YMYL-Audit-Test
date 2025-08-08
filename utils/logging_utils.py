#!/usr/bin/env python3
"""
Logging utilities for YMYL Audit Tool

Centralized logging setup and helper functions.
"""

import logging
from datetime import datetime
import pytz
from config.settings import LOG_FORMAT, LOG_LEVEL, DEFAULT_TIMEZONE


def setup_logger(name, level=None):
    """
    Set up a logger with consistent formatting.
    
    Args:
        name (str): Name of the logger (usually __name__)
        level (str): Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    
    Returns:
        logging.Logger: Configured logger instance
    """
    if level is None:
        level = getattr(logging, LOG_LEVEL)
    
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Avoid duplicate handlers
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(LOG_FORMAT)
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    
    return logger


def log_with_timestamp(message, timezone=DEFAULT_TIMEZONE):
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


def format_processing_step(step_name, status="in_progress", details=None):
    """
    Format processing step for consistent UI display.
    
    Args:
        step_name (str): Name of the processing step
        status (str): Status ('in_progress', 'success', 'error')
        details (str): Additional details
        
    Returns:
        str: Formatted step message
    """
    icons = {
        'in_progress': '🔄',
        'success': '✅',
        'error': '❌',
        'info': 'ℹ️'
    }
    
    icon = icons.get(status, '•')
    message = f"{icon} {step_name}"
    
    if details:
        message += f": {details}"
    
    return message


def format_metrics(metrics_dict):
    """
    Format metrics for display.
    
    Args:
        metrics_dict (dict): Dictionary of metric names and values
        
    Returns:
        str: Formatted metrics string
    """
    formatted_metrics = []
    for key, value in metrics_dict.items():
        if isinstance(value, (int, float)):
            if isinstance(value, float):
                formatted_value = f"{value:.2f}"
            else:
                formatted_value = f"{value:,}"
        else:
            formatted_value = str(value)
        
        formatted_metrics.append(f"{key}: {formatted_value}")
    
    return " | ".join(formatted_metrics)


# Default logger for the module
logger = setup_logger(__name__)
