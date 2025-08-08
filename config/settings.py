#!/usr/bin/env python3
"""
Configuration settings for YMYL Audit Tool

Centralized configuration management for all application settings.
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
CHUNK_POLLING_TIMEOUT = 10  # seconds

# UI Configuration
DEFAULT_TIMEZONE = "Europe/Malta"
DEBUG_MODE_DEFAULT = True

# Logging Configuration
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
LOG_LEVEL = 'INFO'

# Add this to your config/settings.py
DEFAULT_EXPORT_FORMATS = ["html", "pdf", "docx", "markdown"]
