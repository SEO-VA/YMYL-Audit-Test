#!/usr/bin/env python3
"""
Chunk Processor for YMYL Audit Tool

Handles automated interaction with chunk.dejan.ai to process content into chunks.
Uses Selenium WebDriver for browser automation.

ENHANCED: Improved Unicode handling to prevent surrogate pair errors
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
from utils.json_utils import decode_unicode_escapes, clean_surrogate_pairs  # ENHANCED: Import new functions

logger = setup_logger(__name__)


class ChunkProcessor:
    """
    Processes content through chunk.dejan.ai using browser automation.
    
    Handles:
    - Browser setup and configuration
    - Content submission to chunking service
    - Result extraction and JSON parsing
    - Error handling and cleanup
    - Unicode surrogate pair handling
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
        
        ENHANCED: Improved Unicode handling to prevent surrogate errors
        
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
            
            # ENHANCED: Clean Unicode before processing
            self._log("Cleaning Unicode characters in content", "in_progress")
            cleaned_content = clean_surrogate_pairs(content)
            
            if cleaned_content != content:
                char_diff = len(content) - len(cleaned_content)
                self._log(f"Unicode cleaning applied: {char_diff} problematic characters handled", "info")
            
            wait = WebDriverWait(self.driver, SELENIUM_SHORT_TIMEOUT)
            
            # Step 1: Copy content to clipboard with safe encoding
            self._log("Using JavaScript to copy content to clipboard", "in_progress")
            
            # ENHANCED: Use safe JavaScript string escaping
            try:
                # Escape the content for JavaScript (handle quotes, newlines, etc.)
                js_escaped_content = (
                    cleaned_content
                    .replace('\\', '\\\\')  # Escape backslashes
                    .replace('`', '\\`')    # Escape backticks
                    .replace('$', '\\$')    # Escape dollar signs
                    .replace('\n', '\\n')   # Escape newlines
                    .replace('\r', '\\r')   # Escape carriage returns
                    .replace('\t', '\\t')   # Escape tabs
                )
                
                # Use template literal for better Unicode support
                js_code = f"navigator.clipboard.writeText(`{js_escaped_content}`);"
                self.driver.execute_script(js_code)
                
                self._log("Content copied to clipboard successfully", "success")
                
            except Exception as clipboard_error:
                self._log(f"Clipboard copy failed: {clipboard_error}", "warning")
                
                # Fallback: Try with JSON.stringify for safe escaping
                try:
                    import json
                    json_escaped = json.dumps(cleaned_content)
                    js_code = f"navigator.clipboard.writeText({json_escaped});"
                    self.driver.execute_script(js_code)
                    self._log("Content copied using JSON fallback method", "success")
                except Exception as json_error:
                    self._log(f"JSON fallback also failed: {json_error}", "error")
                    return False
            
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
            
            # ENHANCED: Verify paste worked by checking field content
            try:
                pasted_text = input_field.get_attribute('value')
                if not pasted_text or len(pasted_text) < len(cleaned_content) * 0.9:
                    self._log("Paste verification failed - trying direct input", "warning")
                    
                    # Fallback: Direct text input (slower but more reliable)
                    input_field.clear()
                    # Send in smaller chunks to avoid issues
                    chunk_size = 1000
                    for i in range(0, len(cleaned_content), chunk_size):
                        chunk = cleaned_content[i:i + chunk_size]
                        input_field.send_keys(chunk)
                        time.sleep(0.1)  # Small delay between chunks
                    
                    self._log("Content entered using direct input method", "success")
                else:
                    self._log("Paste verification successful", "success")
                    
            except Exception as verify_error:
                self._log(f"Paste verification failed: {verify_error}", "warning")
                # Continue anyway, the paste might have worked
            
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
        Extract JSON output from the copy button and decode Unicode escapes.
        
        ENHANCED: Better Unicode handling with surrogate pair safety
        
        Returns:
            str or None: Extracted and decoded JSON content or None if failed
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
            
            # ENHANCED: Safe HTML entity decoding
            self._log("Decoding HTML entities", "in_progress")
            try:
                decoded_content = html.unescape(final_content)
            except Exception as html_error:
                self._log(f"HTML decoding failed: {html_error}", "warning")
                decoded_content = final_content
            
            # ENHANCED: Safe Unicode decoding with surrogate handling
            self._log("Decoding Unicode escapes safely", "in_progress")
            try:
                decoded_content = decode_unicode_escapes(decoded_content)
                
                # Additional safety: clean any remaining surrogates
                final_decoded = clean_surrogate_pairs(decoded_content)
                
                if final_decoded != decoded_content:
                    self._log("Additional Unicode cleaning applied", "info")
                
                decoded_content = final_decoded
                
            except Exception as unicode_error:
                self._log(f"Unicode decoding failed: {unicode_error}", "warning")
                # Use the HTML-decoded version as fallback
                decoded_content = clean_surrogate_pairs(decoded_content)
            
            # Log decoding results for debugging
            if '\\u' in final_content:
                unicode_count = final_content.count('\\u')
                remaining_count = decoded_content.count('\\u')
                self._log(f"Unicode decoding: {unicode_count} sequences found, {remaining_count} remaining", "info")
                
                if remaining_count == 0:
                    logger.info("Unicode decoding successful - all sequences converted")
                else:
                    logger.warning(f"Unicode decoding incomplete - {remaining_count} sequences remain")
            
            # ENHANCED: Validate the final content can be safely encoded
            try:
                decoded_content.encode('utf-8')
                self._log("UTF-8 encoding validation passed", "success")
            except UnicodeEncodeError as encoding_error:
                self._log(f"UTF-8 encoding validation failed: {encoding_error}", "error")
                # Apply final cleaning
                decoded_content = decoded_content.encode('utf-8', errors='replace').decode('utf-8')
                self._log("Applied replacement encoding for safety", "warning")
            
            self._log(f"Extraction complete. Retrieved {len(decoded_content):,} characters", "success")
            logger.info(f"Successfully extracted and decoded JSON: {len(decoded_content):,} characters")
            
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
        
        ENHANCED: Better Unicode error handling throughout
        
        Args:
            content (str): Content to be processed
            
        Returns:
            tuple: (success: bool, json_output: str or None, error: str or None)
        """
        logger.info(f"Starting chunk processing for content ({len(content):,} characters)")
        
        # ENHANCED: Validate and clean input content
        if not content or not content.strip():
            error_msg = "Cannot process empty content"
            self._log(error_msg, "error")
            return False, None, error_msg
        
        # Pre-clean the content for Unicode issues
        try:
            cleaned_input = clean_surrogate_pairs(content)
            if cleaned_input != content:
                char_diff = len(content) - len(cleaned_input)
                logger.info(f"Pre-cleaned {char_diff} problematic Unicode characters from input")
            content = cleaned_input
        except Exception as clean_error:
            logger.warning(f"Input cleaning failed: {clean_error}")
            # Continue with original content
        
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
            
            # Step 4: Extract and decode JSON
            json_output = self._extract_json_from_button()
            if not json_output:
                return False, None, "Failed to extract JSON from results page"
            
            # ENHANCED: Final validation of output
            try:
                # Test that the output can be safely used
                json_output.encode('utf-8')
                import json
                json.loads(json_output)  # Validate it's proper JSON
                
                self._log("Final validation passed - output is safe and valid", "success")
                
            except UnicodeEncodeError as encoding_error:
                self._log(f"Final encoding validation failed: {encoding_error}", "error")
                return False, None, "Output contains unsafe Unicode characters"
            except json.JSONDecodeError as json_error:
                self._log(f"Final JSON validation failed: {json_error}", "error")
                return False, None, "Output is not valid JSON"
            except Exception as validation_error:
                self._log(f"Final validation failed: {validation_error}", "error")
                return False, None, f"Output validation failed: {validation_error}"
            
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

    def validate_unicode_safety(self, text: str) -> dict:
        """
        Validate that text is safe for processing (no surrogate pairs).
        
        Args:
            text (str): Text to validate
            
        Returns:
            dict: Validation results
        """
        try:
            results = {
                'is_safe': True,
                'can_encode_utf8': True,
                'has_surrogates': False,
                'unicode_escape_count': text.count('\\u'),
                'original_length': len(text),
                'errors': []
            }
            
            # Test UTF-8 encoding
            try:
                text.encode('utf-8')
            except UnicodeEncodeError as e:
                results['is_safe'] = False
                results['can_encode_utf8'] = False
                results['errors'].append(f"UTF-8 encoding error: {e}")
            
            # Check for surrogates in Unicode escapes
            import re
            unicode_matches = re.findall(r'\\u([0-9a-fA-F]{4})', text)
            surrogate_count = 0
            
            for match in unicode_matches:
                code_point = int(match, 16)
                if 0xD800 <= code_point <= 0xDFFF:
                    surrogate_count += 1
            
            if surrogate_count > 0:
                results['is_safe'] = False
                results['has_surrogates'] = True
                results['errors'].append(f"Found {surrogate_count} surrogate Unicode escapes")
            
            return results
            
        except Exception as e:
            return {
                'is_safe': False,
                'can_encode_utf8': False,
                'has_surrogates': False,
                'unicode_escape_count': 0,
                'original_length': len(text) if text else 0,
                'errors': [f"Validation error: {e}"]
            }

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit with cleanup."""
        self.cleanup()
        if exc_type is not None:
            logger.error(f"ChunkProcessor context manager exit due to exception: {exc_type.__name__}: {exc_val}")