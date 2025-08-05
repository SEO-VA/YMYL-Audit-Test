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
    Handles content extraction from websites using the same logic as the JavaScript bookmarklet
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
        Extract structured content from a webpage using the same logic as the JS bookmarklet
        
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
            
            # Find the main content container using fallback strategy
            main_container = self._find_main_container(soup)
            
            # Extract H1 elements (main headings)
            h1_elements = soup.find_all('h1')
            for h1 in h1_elements:
                text = self._get_clean_text(h1)
                if text:
                    content_parts.append(f'H1: {text}')
            
            # Extract subtitles with specific class patterns (matching JS logic)
            subtitle_selectors = [
                '.sub-title', '.subtitle', 
                '[class*="sub-title"]', '[class*="subtitle"]'
            ]
            
            for selector in subtitle_selectors:
                subtitles = soup.select(selector)
                for subtitle in subtitles:
                    # Check if it has d-block class or is within d-block (matching JS logic)
                    if ('d-block' in subtitle.get('class', []) or 
                        subtitle.find_parent(class_='d-block')):
                        text = self._get_clean_text(subtitle)
                        if text:
                            content_parts.append(f'SUBTITLE: {text}')
            
            # Extract lead paragraphs (intro/summary paragraphs)
            lead_selectors = ['.lead', '[class*="lead"]']
            for selector in lead_selectors:
                leads = soup.select(selector)
                for lead in leads:
                    text = self._get_clean_text(lead)
                    if text:
                        content_parts.append(f'LEAD: {text}')
            
            # Extract main content from the identified container
            if main_container:
                main_text = self._get_clean_text(main_container)
                if main_text:
                    content_parts.append(f'CONTENT: {main_text}')
            
            # Join all content parts with double newlines for readability
            final_content = '\n\n'.join(content_parts) if content_parts else 'No content found'
            
            return True, final_content, None
            
        except requests.RequestException as e:
            return False, None, f"Error fetching URL: {str(e)}"
        except Exception as e:
            return False, None, f"Error processing content: {str(e)}"
    
    def _find_main_container(self, soup):
        """
        Find the main content container using the same fallback logic as the JS bookmarklet
        
        Args:
            soup: BeautifulSoup object
            
        Returns:
            BeautifulSoup element or None
        """
        # Primary selectors in order of preference (semantic HTML elements first)
        primary_selectors = [
            'article',      # Semantic article element
            'main',         # Main content area
            '.content',     # Common content class
            '#content',     # Common content ID
            '[role="main"]' # ARIA main role
        ]
        
        # Try each selector in order
        for selector in primary_selectors:
            container = soup.select_one(selector)
            if container:
                return container
        
        # Fallback: find parent element of paragraph clusters
        # This handles sites without semantic markup
        paragraphs = soup.find_all('p')
        if len(paragraphs) > 3:
            return paragraphs[0].parent
        
        # Last resort: use the entire body element
        return soup.find('body')
    
    def _get_clean_text(self, element):
        """
        Extract and clean text from an HTML element
        
        Args:
            element: BeautifulSoup element
            
        Returns:
            str: Cleaned text content
        """
        if not element:
            return ''
        
        # Extract text with spaces between elements and strip whitespace
        text = element.get_text(separator=' ', strip=True)
        
        # Normalize whitespace (remove extra spaces, tabs, newlines)
        text = ' '.join(text.split())
        
        return text

class ChunkProcessor:
    """
    Handles interaction with chunk.dejan.ai using Selenium automation
    """
    
    def __init__(self):
        self.driver = None
        self.setup_driver()
    
    def setup_driver(self):
        """
        Initialize Chrome WebDriver with optimized settings for Streamlit Cloud
        """
        try:
            # Configure Chrome options for headless operation and Streamlit Cloud compatibility
            chrome_options = Options()
            chrome_options.add_argument('--headless')  # Run without GUI for server deployment
            chrome_options.add_argument('--no-sandbox')  # Required for containerized environments
            chrome_options.add_argument('--disable-dev-shm-usage')  # Overcome limited resource problems
            chrome_options.add_argument('--disable-gpu')  # Disable GPU acceleration
            chrome_options.add_argument('--window-size=1920,1080')  # Set consistent window size
            chrome_options.add_argument('--disable-web-security')  # Disable web security for testing
            chrome_options.add_argument('--disable-features=VizDisplayCompositor')  # Additional stability
            chrome_options.add_argument('--disable-extensions')  # Disable extensions
            chrome_options.add_argument('--disable-plugins')  # Disable plugins
            chrome_options.add_argument('--remote-debugging-port=9222')  # Enable remote debugging
            
            # Initialize the WebDriver (Streamlit Cloud will use chromium-driver from packages.txt)
            self.driver = webdriver.Chrome(options=chrome_options)
            self.driver.implicitly_wait(10)  # Set default wait time for element finding
            
            return True
            
        except WebDriverException as e:
            logger.error(f"Failed to initialize Chrome driver: {e}")
            return False
    
    def process_content(self, content):
        """
        Submit content to chunk.dejan.ai and retrieve the generated JSON
        
        Args:
            content (str): Text content to be processed
            
        Returns:
            tuple: (success: bool, json_output: str, error: str)
        """
        if not self.driver:
            if not self.setup_driver():
                return False, None, "Failed to initialize browser"
        
        try:
            # Navigate to the chunk.dejan.ai website
            self.driver.get("https://chunk.dejan.ai/")
            
            # Wait for the page to fully load (Streamlit apps take time to initialize)
            wait = WebDriverWait(self.driver, 30)
            
            # Find and clear the input textarea using the ID we identified
            input_element = wait.until(
                EC.presence_of_element_located((By.ID, "text_area_1"))
            )
            
            # Clear any existing content and input our scraped content
            input_element.clear()
            input_element.send_keys(content)
            
            # Find and click the "Generate Chunks and Visualize" button
            submit_button = wait.until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, '[data-testid="stBaseButton-secondary"]'))
            )
            submit_button.click()
            
            # Wait for processing to complete by waiting for the copy button to appear
            # This button only appears when the JSON output is ready
            copy_button = wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, '[data-testid="stCodeCopyButton"]'))
            )
            
            # Extract the JSON from the copy button's data-clipboard-text attribute
            json_output = copy_button.get_attribute('data-clipboard-text')
            
            if json_output:
                # Validate that we got valid JSON
                try:
                    json.loads(json_output)  # Test if it's valid JSON
                    return True, json_output, None
                except json.JSONDecodeError:
                    return False, None, "Invalid JSON received from chunk.dejan.ai"
            else:
                return False, None, "No JSON output found"
                
        except TimeoutException:
            return False, None, "Timeout waiting for chunk.dejan.ai to process content"
        except WebDriverException as e:
            return False, None, f"Browser error: {str(e)}"
        except Exception as e:
            return False, None, f"Unexpected error: {str(e)}"
    
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

def process_url_workflow(url):
    """
    Complete workflow function that handles the entire process
    This runs in a separate thread to avoid blocking the UI
    
    Args:
        url (str): Source URL to process
        
    Returns:
        dict: Result containing success status and data/error information
    """
    result = {
        'success': False,
        'url': url,
        'extracted_content': None,
        'json_output': None,
        'error': None,
        'step': 'Starting...'
    }
    
    # Initialize processors
    extractor = ContentExtractor()
    processor = ChunkProcessor()
    
    try:
        # Step 1: Extract content from the source URL
        result['step'] = 'Extracting content from URL...'
        success, content, error = extractor.extract_content(url)
        
        if not success:
            result['error'] = f"Content extraction failed: {error}"
            return result
        
        # Validate that we got meaningful content
        if not content or content.strip() == 'No content found' or len(content.strip()) < 50:
            result['error'] = "Insufficient content extracted from URL. Please check if the URL contains readable content."
            return result
        
        result['extracted_content'] = content
        
        # Step 2: Process content through chunk.dejan.ai
        result['step'] = 'Processing content through chunk.dejan.ai...'
        success, json_output, error = processor.process_content(content)
        
        if not success:
            result['error'] = f"Chunk processing failed: {error}"
            return result
        
        result['json_output'] = json_output
        result['success'] = True
        result['step'] = 'Completed successfully!'
        
        return result
        
    except Exception as e:
        result['error'] = f"Unexpected error in workflow: {str(e)}"
        return result
    
    finally:
        # Always cleanup browser resources
        processor.cleanup()

def main():
    """
    Main Streamlit application interface
    """
    # App header with styling
    st.title("🔄 Content Processor")
    st.markdown("**Automatically extract content from websites and generate JSON chunks**")
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
            
            # Show processing status
            with st.spinner("Processing your request..."):
                # Create progress placeholder
                progress_placeholder = st.empty()
                status_placeholder = st.empty()
                
                # Process the URL (this runs synchronously but shows progress)
                progress_placeholder.progress(0.1)
                status_placeholder.info("🔍 Validating URL and starting extraction...")
                
                # Run the workflow
                result = process_url_workflow(url)
                
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
        3. **Generate**: Returns structured JSON chunks
        4. **Display**: Shows results below
        """)
        
        # Stats or additional info could go here
        st.info("💡 **Tip**: Works best with articles, blog posts, and structured content")
    
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
            st.text_area(
                "Raw extracted content:",
                value=result['extracted_content'],
                height=300,
                disabled=True
            )
        
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
        "Built with Streamlit • Powered by chunk.dejan.ai"
        "</div>", 
        unsafe_allow_html=True
    )

# Session state initialization - ensure proper initialization
if 'latest_result' not in st.session_state:
    st.session_state['latest_result'] = None

# Run the app
if __name__ == "__main__":
    main()
