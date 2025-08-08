#!/usr/bin/env python3
"""
Chunk Processor for YMYL Audit Tool

Handles automated interaction with chunk.dejan.ai to process content into chunks.
Uses Selenium WebDriver for browser automation.
"""

import time
import html
import platform
from typing import Tuple, Optional, Callable
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, WebDriverException
from config.settings import (
    CHUNK_API_URL, SELENIUM_TIMEOUT, SELENIUM_SHORT_TIMEOUT,
    CHROME_OPTIONS, CHUNK_POLLING_INTERVAL, CHUNK_POLLING_TIMEOUT,
    MAX_CONTENT_LENGTH
)
from utils.logging_utils import setup_logger, format_processing_step

logger = setup_logger(__name__)


class ChunkProcessor:
    """
    Processes content through chunk.dejan.ai using browser automation.
    
    Handles:
    - Browser setup and configuration
    - Content submission to chunking service
    - Result extraction and JSON parsing
    - Error handling and cleanup
    """
    
    def __init__(self, log_callback: Optional[Callable[[str], None]] = None):
        """
        Initialize the ChunkProcessor.
        
        Args:
            log_callback: Optional callback function for logging to UI
        """
        self.driver = None
        self.log_callback = log_callback
        logger.info("ChunkProcessor initialized")

    def _log(self, message: str, status: str = "info"):
        """
        Log message to both logger and UI callback.
        
        Args:
            message (str): Message to log
            status (str): Status type for formatting
        """
        formatted_message = format_processing_step(message, status)
        logger.info(message)
        
        if self.log_callback:
            self.log_callback(formatted_message)

    def _setup_driver(self) -> bool:
        """
        Set up Chrome WebDriver with optimal configuration.
        
        Returns:
            bool: True if setup successful, False otherwise
        """
        self._log("Initializing browser with enhanced stability & permissions", "in_progress")
        
        try:
            chrome_options = Options()
            
            # Add all Chrome options from config
            for option in CHROME_OPTIONS:
                chrome_options.add_argument(option)
            
            # Enable clipboard access
            chrome_options.add_experimental_option(
                "prefs", 
                {"profile.default_content_setting_values.clipboard": 1}
            )
            
            # Additional stability options
            chrome_options.add_argument('--disable-blink-features=AutomationControlled')
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            
            # Initialize driver
            self.driver = webdriver.Chrome(options=chrome_options)
            
            # Remove webdriver property to avoid detection
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            self._log("Browser initialized successfully", "success")
            return True
            
        except WebDriverException as e:
            error_msg = f"WebDriver initialization failed: {str(e)}"
            self._log(error_msg, "error")
            logger.error(error_msg)
            return False
        except Exception as e:
            error_msg = f"Unexpected error during browser setup: {str(e)}"
            self._log(error_msg, "error")
            logger.error(error_msg)
            return False

    def _navigate_to_chunker(self) -> bool:
        """
        Navigate to the chunking website.
        
        Returns:
            bool: True if navigation successful, False otherwise
        """
        try:
            self._log(f"Navigating to {CHUNK_API_URL}", "in_progress")
            self.driver.get(CHUNK_API_URL)
            
            # Wait for page to load
            wait = WebDriverWait(self.driver, SELENIUM_SHORT_TIMEOUT)
            wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            
            self._log("Successfully navigated to chunking service", "success")
            return True
            
        except TimeoutException:
            error_msg = "Timeout waiting for chunking website to load"
            self._log(error_msg, "error")
            logger.error(error_msg)
            return False
        except Exception as e:
            error_msg = f"Navigation error: {str(e)}"
            self._log(error_msg, "error")
            logger.error(error_msg)
            return False

    def _submit_content(self, content: str) -> bool:
        """
        Submit content to the chunking service.
        
        Args:
            content (str): Content to be chunked
            
        Returns:
            bool: True if submission successful, False otherwise
        """
        try:
            # Validate content length
            if len(content) > MAX_CONTENT_LENGTH:
                error_msg = f"Content too large: {len(content):,} characters (max: {MAX_CONTENT_LENGTH:,})"
                self._log(error_msg, "error")
                return False
            
            wait = WebDriverWait(self.driver, SELENIUM_SHORT_TIMEOUT)
            
            # Step 1: Copy content to clipboard
            self._log("Using JavaScript to copy content to clipboard", "in_progress")
            self.driver.execute_script("navigator.clipboard.writeText(arguments[0]);", content)
            
            # Step 2: Locate and clear textarea
            self._log("Locating text area and clearing it", "in_progress")
            textarea_selector = (By.CSS_SELECTOR, 'textarea[aria-label="Text to chunk:"]')
            input_field = wait.until(EC.element_to_be_clickable(textarea_selector))
            input_field.clear()
            
            # Step 3: Paste content
            self._log("Simulating paste command (Ctrl+V)", "in_progress")
            modifier_key = Keys.COMMAND if platform.system() == "Darwin" else Keys.CONTROL
            input_field.send_keys(modifier_key, "v")
            
            # Brief wait to ensure paste completes
            time.sleep(1)
            
            # Step 4: Submit
            self._log("Clicking submit button", "in_progress")
            submit_button = wait.until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, '[data-testid="stBaseButton-secondary"]'))
            )
            submit_button.click()
            
            self._log("Content submitted successfully", "success")
            return True
            
        except TimeoutException as e:
            error_msg = f"Timeout during content submission: element not found or not clickable"
            self._log(error_msg, "error")
            logger.error(f"{error_msg}: {str(e)}")
            return False
        except Exception as e:
            error_msg = f"Error during content submission: {str(e)}"
            self._log(error_msg, "error")
            logger.error(error_msg)
            return False

    def _wait_for_results(self) -> bool:
        """
        Wait for processing results to appear.
        
        Returns:
            bool: True if results appeared, False if timeout
        """
        try:
            wait = WebDriverWait(self.driver, SELENIUM_TIMEOUT)
            h3_xpath = "//h3[text()='Raw JSON Output']"
            
            self._log("Waiting for results section to appear", "in_progress")
            wait.until(EC.presence_of_element_located((By.XPATH, h3_xpath)))
            
            self._log("Results section is visible", "success")
            return True
            
        except TimeoutException:
            error_msg = f"Timeout waiting for results after {SELENIUM_TIMEOUT} seconds"
            self._log(error_msg, "error")
            logger.error(error_msg)
            return False
        except Exception as e:
            error_msg = f"Error waiting for results: {str(e)}"
            self._log(error_msg, "error")
            logger.error(error_msg)
            return False

    def _extract_json_from_button(self) -> Optional[str]:
        """
        Extract JSON output from the copy button.
        
        Returns:
            str or None: Extracted JSON content or None if failed
        """
        try:
            wait = WebDriverWait(self.driver, SELENIUM_SHORT_TIMEOUT)
            button_selector = "button[data-testid='stCodeCopyButton']"
            
            self._log("Locating copy button", "in_progress")
            copy_button = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, button_selector)))
            
            self._log("Polling button attribute for completeness", "in_progress")
            
            # Poll for complete content
            timeout = time.time() + CHUNK_POLLING_TIMEOUT
            final_content = ""
            
            while time.time() < timeout:
                raw_content = copy_button.get_attribute('data-clipboard-text')
                
                if raw_content and raw_content.strip():
                    # Check if content looks like complete JSON
                    if raw_content.strip().startswith('{') and raw_content.strip().endswith('}'):
                        final_content = raw_content
                        break
                
                time.sleep(CHUNK_POLLING_INTERVAL)
            
            if not final_content:
                error_msg = "Timed out polling the button attribute"
                self._log(error_msg, "error")
                logger.error(error_msg)
                return None
            
            # Decode HTML entities
            self._log("Decoding HTML entities", "in_progress")
            decoded_content = html.unescape(final_content)
            
            self._log(f"Extraction complete. Retrieved {len(decoded_content):,} characters", "success")
            logger.info(f"Successfully extracted JSON: {len(decoded_content):,} characters")
            
            return decoded_content
            
        except TimeoutException:
            error_msg = "Timeout locating copy button"
            self._log(error_msg, "error")
            logger.error(error_msg)
            return None
        except Exception as e:
            error_msg = f"Error during JSON extraction: {str(e)}"
            self._log(error_msg, "error")
            logger.error(error_msg)
            return None

    def process_content(self, content: str) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Process content through the complete chunking workflow.
        
        Args:
            content (str): Content to be processed
            
        Returns:
            tuple: (success: bool, json_output: str or None, error: str or None)
        """
        logger.info(f"Starting chunk processing for content ({len(content):,} characters)")
        
        # Validate input
        if not content or not content.strip():
            error_msg = "Cannot process empty content"
            self._log(error_msg, "error")
            return False, None, error_msg
        
        # Setup browser
        if not self._setup_driver():
            return False, None, "Failed to initialize browser"
        
        try:
            # Step 1: Navigate to chunker
            if not self._navigate_to_chunker():
                return False, None, "Failed to navigate to chunking service"
            
            # Step 2: Submit content
            if not self._submit_content(content):
                return False, None, "Failed to submit content to chunking service"
            
            # Step 3: Wait for results
            if not self._wait_for_results():
                return False, None, "Chunking process timed out or failed"
            
            # Step 4: Extract JSON
            json_output = self._extract_json_from_button()
            if not json_output:
                return False, None, "Failed to extract JSON from results page"
            
            self._log("Chunk processing completed successfully", "success")
            logger.info("Chunk processing workflow completed successfully")
            
            return True, json_output, None
            
        except Exception as e:
            error_msg = f"Unexpected error during chunk processing: {str(e)}"
            self._log(error_msg, "error")
            logger.error(error_msg)
            return False, None, error_msg
            
        finally:
            # Always cleanup
            self.cleanup()

    def cleanup(self):
        """
        Clean up browser resources.
        """
        if self.driver:
            try:
                self._log("Cleaning up and closing browser instance", "info")
                self.driver.quit()
                self.driver = None
                self._log("Browser closed successfully", "success")
                logger.info("Browser cleanup completed")
            except Exception as e:
                logger.warning(f"Error during browser cleanup: {str(e)}")
        else:
            logger.info("No browser instance to cleanup")

    def get_processing_status(self) -> dict:
        """
        Get current processing status information.
        
        Returns:
            dict: Status information
        """
        return {
            'browser_initialized': self.driver is not None,
            'browser_active': self.driver is not None and self.driver.session_id is not None,
            'current_url': self.driver.current_url if self.driver else None,
            'page_title': self.driver.title if self.driver else None
        }

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit with cleanup."""
        self.cleanup()
        if exc_type is not None:
            logger.error(f"ChunkProcessor context manager exit due to exception: {exc_type.__name__}: {exc_val}")
