#!/usr/bin/env python3
"""
Content Processing Web Application

A Streamlit web app that scrapes content from URLs and automatically 
processes them through chunk.dejan.ai to generate JSON chunks.

Deployed on Streamlit Cloud for easy access by colleagues.
"""

import streamlit as st
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, WebDriverException
import json
import time
import logging
from urllib.parse import urlparse
import threading
from concurrent.futures import ThreadPoolExecutor

# Configure logging for debugging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Streamlit page configuration
st.set_page_config(
    page_title="Content Processor",
    page_icon="🔄",
    layout="wide",
    initial_sidebar_state="collapsed"
)

class ContentExtractor:
    """
    Handles content extraction from websites using EXACT logic from the JavaScript bookmarklet
    """
    
    def __init__(self):
        # Configure requests session with proper headers to avoid blocking
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        })
    
    def extract_content(self, url):
        """
        Extract structured content using EXACT logic from the JavaScript bookmarklet
        
        Args:
            url (str): Source URL to scrape
            
        Returns:
            tuple: (success: bool, content: str, error: str)
        """
        try:
            # Add delay to respect rate limits and avoid being blocked
            time.sleep(1)
            
            # Fetch the webpage content
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            # Parse HTML content with BeautifulSoup
            soup = BeautifulSoup(response.content, 'html.parser')
            content_parts = []
            
            # Find the main content container using EXACT bookmarklet logic
            main_container = self._find_main_container_exact(soup)
            
            # Extract H1 elements - EXACT bookmarklet logic
            h1_elements = soup.find_all('h1')
            for h1 in h1_elements:
                # Use innerText equivalent (get_text with strip) || textContent equivalent  
                text = self._get_inner_text(h1)
                if text.strip():
                    content_parts.append(f'H1: {text.strip()}')
            
            # Extract subtitles with EXACT bookmarklet logic
            # '.sub-title,.subtitle,[class*="sub-title"],[class*="subtitle"]'
            subtitle_selectors = '.sub-title,.subtitle,[class*="sub-title"],[class*="subtitle"]'
            subtitles = soup.select(subtitle_selectors)
            
            for subtitle in subtitles:
                # Check EXACT condition: className.includes('d-block') || closest('.d-block')
                class_names = ' '.join(subtitle.get('class', []))
                has_d_block = 'd-block' in class_names
                closest_d_block = subtitle.find_parent(class_='d-block') is not None
                
                if has_d_block or closest_d_block:
                    text = self._get_inner_text(subtitle)
                    if text.strip():
                        content_parts.append(f'SUBTITLE: {text.strip()}')
            
            # Extract lead paragraphs - EXACT bookmarklet logic
            # '.lead,[class*="lead"]'
            lead_selectors = '.lead,[class*="lead"]'
            leads = soup.select(lead_selectors)
            
            for lead in leads:
                text = self._get_inner_text(lead)
                if text.strip():
                    content_parts.append(f'LEAD: {text.strip()}')
            
            # Extract main content - EXACT bookmarklet logic
            if main_container:
                # Use innerText || textContent || '' equivalent
                main_text = self._get_inner_text(main_container) or ''
                if main_text.strip():
                    content_parts.append(f'CONTENT: {main_text.strip()}')
            
            # Join all content parts - EXACT bookmarklet logic
            final_content = '\n\n'.join(content_parts) if content_parts else 'No content found'
            
            return True, final_content, None
            
        except requests.RequestException as e:
            return False, None, f"Error fetching URL: {str(e)}"
        except Exception as e:
            return False, None, f"Error processing content: {str(e)}"
    
    def _find_main_container_exact(self, soup):
        """
        Find main content container using EXACT bookmarklet logic
        
        var a=document.querySelector('article')||document.querySelector('main')||document.querySelector('.content')||document.querySelector('#content')||document.querySelector('[role="main"]');
        if(!a){var p=document.querySelectorAll('p');if(p.length>3)a=p[0].parentElement;}
        if(!a)a=document.body;
        """
        # Try selectors in exact order from bookmarklet
        selectors = ['article', 'main', '.content', '#content', '[role="main"]']
        
        for selector in selectors:
            container = soup.select_one(selector)
            if container:
                return container
        
        # Fallback: if no container found, check paragraph logic
        paragraphs = soup.find_all('p')
        if len(paragraphs) > 3:
            return paragraphs[0].parent
        
        # Final fallback: document.body equivalent
        return soup.find('body')
    
    def _get_inner_text(self, element):
        """
        Get text equivalent to JavaScript innerText || textContent with proper formatting
        
        This preserves paragraph breaks and block structure like the original bookmarklet
        """
        if not element:
            return ''
        
        try:
            # Get text with line breaks preserved (closest to innerText behavior)
            text = element.get_text(separator='\n', strip=True)
            
            # Clean up excessive line breaks but preserve paragraph structure
            lines = text.split('\n')
            cleaned_lines = []
            
            for line in lines:
                line = line.strip()
                if line:  # Only add non-empty lines
                    cleaned_lines.append(line)
            
            # Join with single newlines to preserve paragraph breaks within sections
            return '\n'.join(cleaned_lines)
            
        except:
            # Fallback to simple text extraction
            return element.get_text(strip=True)

class ChunkProcessor:
    """
    Handles interaction with chunk.dejan.ai using Selenium automation with 4-fetch completion detection
    """
    
    def __init__(self):
        self.driver = None
        self.setup_driver()
    
    def setup_driver(self):
        """
        Initialize Chrome WebDriver with ultra-stable settings and performance logging enabled
        """
        try:
            # Configure Chrome options with maximum stability for containerized environments
            chrome_options = Options()
            
            # Core headless settings
            chrome_options.add_argument('--headless=new')  # Use new headless mode
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            
            # Memory and stability optimizations
            chrome_options.add_argument('--disable-web-security')
            chrome_options.add_argument('--disable-features=VizDisplayCompositor')
            chrome_options.add_argument('--disable-extensions')
            chrome_options.add_argument('--disable-plugins')
            chrome_options.add_argument('--disable-images')  # Faster loading
            chrome_options.add_argument('--disable-background-timer-throttling')
            chrome_options.add_argument('--disable-backgrounding-occluded-windows')
            chrome_options.add_argument('--disable-renderer-backgrounding')
            chrome_options.add_argument('--disable-field-trial-config')
            chrome_options.add_argument('--disable-back-forward-cache')
            chrome_options.add_argument('--disable-hang-monitor')
            chrome_options.add_argument('--disable-prompt-on-repost')
            chrome_options.add_argument('--disable-sync')
            chrome_options.add_argument('--disable-translate')
            chrome_options.add_argument('--hide-scrollbars')
            chrome_options.add_argument('--metrics-recording-only')
            chrome_options.add_argument('--mute-audio')
            chrome_options.add_argument('--no-first-run')
            chrome_options.add_argument('--safebrowsing-disable-auto-update')
            chrome_options.add_argument('--single-process')  # Run in single process mode
            chrome_options.add_argument('--disable-default-apps')
            
            # Window and display settings
            chrome_options.add_argument('--window-size=1280,720')  # Smaller window
            chrome_options.add_argument('--start-maximized')
            
            # Memory limits
            chrome_options.add_argument('--max_old_space_size=2048')
            chrome_options.add_argument('--memory-pressure-off')
            
            # Disable logging that might cause issues
            chrome_options.add_argument('--disable-logging')
            chrome_options.add_argument('--log-level=3')
            chrome_options.add_argument('--silent')
            
            # Set user agent
            chrome_options.add_argument('--user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
            
            # IMPORTANT: Enable performance logging for network monitoring
            chrome_options.add_argument('--enable-logging')
            chrome_options.add_argument('--log-level=0')
            chrome_options.set_capability('goog:loggingPrefs', {'performance': 'ALL'})
            
            # Initialize the WebDriver with error handling
            try:
                self.driver = webdriver.Chrome(options=chrome_options)
            except Exception as e:
                logger.error(f"Failed with advanced options, trying basic setup: {e}")
                # Fallback to basic options with performance logging
                basic_options = Options()
                basic_options.add_argument('--headless')
                basic_options.add_argument('--no-sandbox')
                basic_options.add_argument('--disable-dev-shm-usage')
                basic_options.set_capability('goog:loggingPrefs', {'performance': 'ALL'})
                self.driver = webdriver.Chrome(options=basic_options)
            
            # Set timeouts
            self.driver.set_page_load_timeout(60)
            self.driver.implicitly_wait(15)
            
            logger.info("Chrome WebDriver initialized successfully with network monitoring")
            return True
            
        except WebDriverException as e:
            logger.error(f"Failed to initialize Chrome driver: {e}")
            return False
    
    def wait_for_fourth_fetch(self):
        """
        Count fetch requests to index.NJ4tUjPs809
        After 4th fetch = JSON ready for extraction
        """
        endpoint_pattern = "index.NJ4tUjPs809"
        fetch_count = 0
        seen_requests = set()  # Track unique requests to avoid duplicates
        max_wait_time = 180  # 3 minute timeout
        start_time = time.time()
        
        logger.info("Counting fetch requests for completion...")
        logger.info("Waiting for 4th fetch request to index.NJ4tUjPs809...")
        
        while fetch_count < 4:
            # Check timeout
            if time.time() - start_time > max_wait_time:
                logger.warning("Timeout waiting for 4th fetch request - proceeding anyway")
                return True  # Continue anyway
                
            try:
                logs = self.driver.get_log('performance')
                
                for log in logs:
                    if endpoint_pattern in str(log) and 'fetch' in str(log).lower():
                        log_id = f"{log.get('timestamp', 0)}_{hash(str(log))}"
                        if log_id not in seen_requests:
                            seen_requests.add(log_id)
                            fetch_count += 1
                            logger.info(f"Fetch request {fetch_count}/4 detected")
                            
                            if fetch_count >= 4:
                                logger.info("🎯 4th fetch request completed - JSON ready!")
                                return True
                                
            except Exception as e:
                logger.warning(f"Error checking logs: {e}")
            
            time.sleep(0.5)  # Check frequently
        
        return True
    
    def process_content(self, content):
        """
        Submit content to chunk.dejan.ai with 4-fetch completion detection
        """
        max_retries = 2
        
        for attempt in range(max_retries):
            if not self.driver:
                if not self.setup_driver():
                    return False, None, "Failed to initialize browser"
            
            try:
                logger.info(f"Attempt {attempt + 1}/{max_retries}: Navigating to chunk.dejan.ai...")
                
                # Navigate to the chunk.dejan.ai website
                self.driver.get("https://chunk.dejan.ai/")
                
                # Wait longer for Streamlit to initialize
                time.sleep(8)
                
                # Wait for the page to fully load
                wait = WebDriverWait(self.driver, 45)
                
                # Find input field with multiple strategies
                input_element = None
                selectors_to_try = [
                    (By.ID, "text_area_1"),
                    (By.CSS_SELECTOR, 'textarea[aria-label="Text to chunk:"]'),
                    (By.CSS_SELECTOR, 'textarea'),
                ]
                
                for selector_type, selector in selectors_to_try:
                    try:
                        input_element = wait.until(
                            EC.presence_of_element_located((selector_type, selector))
                        )
                        logger.info(f"Found input field with selector: {selector}")
                        break
                    except TimeoutException:
                        continue
                
                if not input_element:
                    raise TimeoutException("Could not find input field with any selector")
                
                # Clear and input content
                logger.info("Clearing and inputting content...")
                input_element.clear()
                time.sleep(2)
                
                # Send content (limit size to prevent issues)
                content_to_send = content[:5000]  # Increased limit for better processing
                input_element.send_keys(content_to_send)
                time.sleep(3)
                
                # Find and click submit button
                submit_button = None
                button_selectors = [
                    (By.CSS_SELECTOR, '[data-testid="stBaseButton-secondary"]'),
                    (By.XPATH, "//button[contains(text(), 'Generate')]"),
                    (By.CSS_SELECTOR, 'button[kind="secondary"]'),
                ]
                
                for selector_type, selector in button_selectors:
                    try:
                        submit_button = wait.until(
                            EC.element_to_be_clickable((selector_type, selector))
                        )
                        logger.info(f"Found submit button with selector: {selector}")
                        break
                    except TimeoutException:
                        continue
                
                if not submit_button:
                    raise TimeoutException("Could not find submit button")
                
                logger.info("Clicking submit button...")
                submit_button.click()
                
                # 4-FETCH COMPLETION DETECTION
                logger.info("Starting 4-fetch counting detection...")
                fourth_fetch_detected = self.wait_for_fourth_fetch()
                
                if not fourth_fetch_detected:
                    logger.warning("4-fetch detection timed out, attempting to extract JSON anyway...")
                else:
                    logger.info("4th fetch detected - processing definitely complete!")
                
                # Find the copy button (should be ready now)
                logger.info("Looking for copy button...")
                copy_button = wait.until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, '[data-testid="stCodeCopyButton"]'))
                )
                
                # Extract the JSON immediately after 4th fetch detection
                logger.info("Extracting JSON output...")
                json_output = copy_button.get_attribute('data-clipboard-text')
                
                if json_output:
                    try:
                        json.loads(json_output)  # Validate JSON
                        logger.info("Successfully retrieved and validated JSON output")
                        logger.info(f"JSON length: {len(json_output)} characters")
                        return True, json_output, None
                    except json.JSONDecodeError as e:
                        logger.error(f"Invalid JSON received: {e}")
                        return False, None, "Invalid JSON received from chunk.dejan.ai"
                else:
                    return False, None, "No JSON output found in copy button"
                    
            except TimeoutException as e:
                error_msg = f"Timeout on attempt {attempt + 1}: {str(e)}"
                logger.warning(error_msg)
                if attempt == max_retries - 1:
                    return False, None, f"Timeout after {max_retries} attempts waiting for chunk.dejan.ai"
                
                # Cleanup and retry
                self.cleanup()
                time.sleep(5)
                continue
                
            except WebDriverException as e:
                error_msg = f"Browser error on attempt {attempt + 1}: {str(e)}"
                logger.warning(error_msg)
                if attempt == max_retries - 1:
                    return False, None, f"Browser error after {max_retries} attempts: {str(e)}"
                
                # Cleanup and retry
                self.cleanup()
                time.sleep(5)
                continue
                
            except Exception as e:
                error_msg = f"Unexpected error on attempt {attempt + 1}: {str(e)}"
                logger.error(error_msg)
                if attempt == max_retries - 1:
                    return False, None, f"Unexpected error after {max_retries} attempts: {str(e)}"
                
                # Cleanup and retry
                self.cleanup()
                time.sleep(5)
                continue
        
        return False, None, "All retry attempts failed"
    
    def cleanup(self):
        """
        Clean up browser resources
        """
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass  # Ignore cleanup errors

def validate_url(url):
    """
    Validate that the provided URL is properly formatted and accessible
    
    Args:
        url (str): URL to validate
        
    Returns:
        tuple: (is_valid: bool, error_message: str)
    """
    try:
        # Parse the URL to check its structure
        parsed = urlparse(url)
        
        # Check if URL has scheme and netloc (domain)
        if not parsed.scheme or not parsed.netloc:
            return False, "Invalid URL format. Please include http:// or https://"
        
        # Check if scheme is http or https
        if parsed.scheme not in ['http', 'https']:
            return False, "URL must use http:// or https://"
        
        return True, None
        
    except Exception as e:
        return False, f"Invalid URL: {str(e)}"

def process_url_workflow_with_logging(url, log_callback=None):
    """
    Complete workflow function with live logging updates
    
    Args:
        url (str): Source URL to process
        log_callback (function): Function to call with log messages
        
    Returns:
        dict: Result containing success status and data/error information
    """
    def log(message):
        if log_callback:
            log_callback(message)
        logger.info(message)  # Also log to server logs
    
    result = {
        'success': False,
        'url': url,
        'extracted_content': None,
        'json_output': None,
        'error': None,
        'step': 'Starting...'
    }
    
    # Initialize processors
    log("🚀 Initializing content extractor...")
    extractor = ContentExtractor()
    
    log("🤖 Initializing chunk processor...")
    processor = ChunkProcessor()
    
    try:
        # Step 1: Extract content from the source URL
        log(f"🔍 Fetching content from: {url}")
        result['step'] = 'Extracting content from URL...'
        success, content, error = extractor.extract_content(url)
        
        if not success:
            log(f"❌ Content extraction failed: {error}")
            result['error'] = f"Content extraction failed: {error}"
            return result
        
        log(f"✅ Content extracted: {len(content)} characters")
        
        # Validate that we got meaningful content
        if not content or content.strip() == 'No content found' or len(content.strip()) < 50:
            log("⚠️ Insufficient content extracted")
            result['error'] = "Insufficient content extracted from URL. Please check if the URL contains readable content."
            return result
        
        result['extracted_content'] = content
        log("📝 Content validation passed")
        
        # Step 2: Process content through chunk.dejan.ai
        log("🔄 Starting chunk.dejan.ai processing...")
        result['step'] = 'Processing content through chunk.dejan.ai...'
        
        log("🌐 Navigating to chunk.dejan.ai with 4-fetch monitoring...")
        success, json_output, error = processor.process_content(content)
        
        if not success:
            log(f"❌ Chunk processing failed: {error}")
            result['error'] = f"Chunk processing failed: {error}"
            return result
        
        log("✅ JSON chunks generated successfully!")
        result['json_output'] = json_output
        result['success'] = True
        result['step'] = 'Completed successfully!'
        
        # Parse and log JSON stats
        try:
            json_data = json.loads(json_output)
            if 'big_chunks' in json_data:
                big_chunks = len(json_data['big_chunks'])
                total_small = sum(len(chunk.get('small_chunks', [])) for chunk in json_data['big_chunks'])
                log(f"📊 Generated {big_chunks} big chunks, {total_small} small chunks")
        except:
            pass
        
        return result
        
    except Exception as e:
        log(f"💥 Unexpected error: {str(e)}")
        result['error'] = f"Unexpected error in workflow: {str(e)}"
        return result
    
    finally:
        # Always cleanup browser resources
        log("🧹 Cleaning up browser resources...")
        processor.cleanup()
        log("✅ Cleanup completed")

def process_url_workflow(url):
    """
    Original workflow function for backward compatibility
    """
    return process_url_workflow_with_logging(url)

def main():
    """
    Main Streamlit application interface
    """
    # App header with styling
    st.title("🔄 Content Processor")
    st.markdown("**Automatically extract content from websites and generate JSON chunks**")
    
    # Debug mode toggle
    debug_mode = st.sidebar.checkbox("🐛 Debug Mode", help="Show detailed processing logs")
    
    st.markdown("---")
    
    # Create two columns for better layout
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # URL input section
        st.subheader("📝 Input URL")
        url = st.text_input(
            "Enter the URL to process:",
            placeholder="https://example.com/article",
            help="Enter a complete URL including http:// or https://"
        )
        
        # Process button
        if st.button("🚀 Process URL", type="primary", use_container_width=True):
            
            # Validate URL before processing
            if not url:
                st.error("Please enter a URL to process")
                return
            
            is_valid, error_msg = validate_url(url)
            if not is_valid:
                st.error(error_msg)
                return
            
            # Show processing status with detailed logging
            with st.spinner("Processing your request..."):
                # Create progress and logging placeholders
                progress_placeholder = st.empty()
                status_placeholder = st.empty()
                log_placeholder = st.empty()
                
                # Initialize logging container
                if debug_mode:
                    log_container = st.container()
                    with log_container:
                        st.subheader("📋 Processing Log")
                        log_messages = []
                
                # Process the URL with live updates
                progress_placeholder.progress(0.1)
                status_placeholder.info("🔍 Validating URL and starting extraction...")
                
                # Run the workflow with logging callback
                def log_callback(message):
                    if debug_mode:
                        log_messages.append(f"• {message}")
                        with log_placeholder.container():
                            for msg in log_messages[-15:]:  # Show last 15 messages
                                st.text(msg)
                
                result = process_url_workflow_with_logging(url, log_callback if debug_mode else None)
                
                # Update progress based on results
                if result['success']:
                    progress_placeholder.progress(1.0)
                    status_placeholder.success("✅ Processing completed successfully!")
                    
                    # Store results in session state for display
                    st.session_state['latest_result'] = result
                    
                else:
                    progress_placeholder.progress(0.5)
                    status_placeholder.error(f"❌ Error: {result['error']}")
    
    with col2:
        # Information panel
        st.subheader("ℹ️ How it works")
        st.markdown("""
        1. **Extract**: Scrapes content from your URL
        2. **Process**: Sends content to chunk.dejan.ai
        3. **Monitor**: Counts 4 fetch requests for completion
        4. **Generate**: Returns complete JSON chunks
        5. **Display**: Shows results below
        """)
        
        # Stats or additional info could go here
        st.info("💡 **Tip**: Works best with articles, blog posts, and structured content")
        
        if debug_mode:
            st.warning("🐛 **Debug Mode Active**\nDetailed processing logs will be shown during operation.")
    
    # Results display section
    if ('latest_result' in st.session_state and 
        st.session_state['latest_result'] is not None and 
        st.session_state['latest_result'].get('success', False)):
        result = st.session_state['latest_result']
        
        st.markdown("---")
        st.subheader("📊 Results")
        
        # Create tabs for different views
        tab1, tab2, tab3 = st.tabs(["🎯 JSON Output", "📄 Extracted Content", "📈 Summary"])
        
        with tab1:
            st.subheader("Generated JSON Chunks")
            
            # Display JSON in a code block with copy functionality
            st.code(result['json_output'], language='json')
            
            # Add download button for JSON
            st.download_button(
                label="💾 Download JSON",
                data=result['json_output'],
                file_name=f"chunks_{int(time.time())}.json",
                mime="application/json"
            )
        
        with tab2:
            st.subheader("Extracted Content")
            st.markdown("**Formatted content as extracted by the bookmarklet logic:**")
            
            # Display the content in a copyable text area
            extracted_content_display = st.text_area(
                "Raw extracted content (copyable):",
                value=result['extracted_content'],
                height=400,
                disabled=False,  # Make it copyable
                help="This content is formatted exactly like the original bookmarklet. You can select and copy it."
            )
            
            # Add a copy button for convenience
            if st.button("📋 Copy Extracted Content", key="copy_extracted"):
                st.success("✅ Content copied to clipboard! (Use Ctrl+A then Ctrl+C in the text area above)")
            
            # Show content statistics
            content_lines = result['extracted_content'].split('\n\n')
            h1_count = len([line for line in content_lines if line.startswith('H1:')])
            subtitle_count = len([line for line in content_lines if line.startswith('SUBTITLE:')])
            lead_count = len([line for line in content_lines if line.startswith('LEAD:')])
            has_main_content = any(line.startswith('CONTENT:') for line in content_lines)
            
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("H1 Headers", h1_count)
            with col2:
                st.metric("Subtitles", subtitle_count)
            with col3:
                st.metric("Lead Paragraphs", lead_count)
            with col4:
                st.metric("Main Content", "✅ Yes" if has_main_content else "❌ No")
        
        with tab3:
            st.subheader("Processing Summary")
            
            # Parse JSON to show statistics
            try:
                json_data = json.loads(result['json_output'])
                
                if 'big_chunks' in json_data:
                    big_chunks = json_data['big_chunks']
                    total_small_chunks = sum(len(chunk.get('small_chunks', [])) for chunk in big_chunks)
                    
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Big Chunks", len(big_chunks))
                    with col2:
                        st.metric("Small Chunks", total_small_chunks)
                    with col3:
                        st.metric("Content Length", f"{len(result['extracted_content'])} chars")
                
            except json.JSONDecodeError:
                st.warning("Could not parse JSON for statistics")
            
            # Source URL info
            st.info(f"**Source URL**: {result['url']}")
    
    # Footer
    st.markdown("---")
    st.markdown(
        "<div style='text-align: center; color: #666;'>"
        "Built with Streamlit • Powered by chunk.dejan.ai • 4-fetch completion detection"
        "</div>", 
        unsafe_allow_html=True
    )

# Session state initialization - ensure proper initialization
if 'latest_result' not in st.session_state:
    st.session_state['latest_result'] = None

# Run the app
if __name__ == "__main__":
    main()
