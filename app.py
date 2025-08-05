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
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                          'AppleWebKit/537.36 (KHTML, like Gecko) '
                          'Chrome/91.0.4472.124 Safari/537.36',
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
                text = self._get_inner_text(h1)
                if text.strip():
                    content_parts.append(f'H1: {text.strip()}')
            
            # Extract subtitles with EXACT bookmarklet logic
            subtitle_selectors = '.sub-title,.subtitle,[class*="sub-title"],[class*="subtitle"]'
            subtitles = soup.select(subtitle_selectors)
            for subtitle in subtitles:
                class_names = ' '.join(subtitle.get('class', []))
                has_d_block = 'd-block' in class_names
                closest_d_block = subtitle.find_parent(class_='d-block') is not None
                if has_d_block or closest_d_block:
                    text = self._get_inner_text(subtitle)
                    if text.strip():
                        content_parts.append(f'SUBTITLE: {text.strip()}')
            
            # Extract lead paragraphs - EXACT bookmarklet logic
            lead_selectors = '.lead,[class*="lead"]'
            leads = soup.select(lead_selectors)
            for lead in leads:
                text = self._get_inner_text(lead)
                if text.strip():
                    content_parts.append(f'LEAD: {text.strip()}')
            
            # Extract main content - EXACT bookmarklet logic
            if main_container:
                main_text = self._get_inner_text(main_container) or ''
                if main_text.strip():
                    content_parts.append(f'CONTENT: {main_text.strip()}')
            
            # Join all content parts
            final_content = '\n\n'.join(content_parts) if content_parts else 'No content found'
            
            return True, final_content, None
            
        except requests.RequestException as e:
            return False, None, f"Error fetching URL: {str(e)}"
        except Exception as e:
            return False, None, f"Error processing content: {str(e)}"
    
    def _find_main_container_exact(self, soup):
        """
        Find main content container using EXACT bookmarklet logic
        """
        selectors = ['article', 'main', '.content', '#content', '[role="main"]']
        for selector in selectors:
            container = soup.select_one(selector)
            if container:
                return container
        
        paragraphs = soup.find_all('p')
        if len(paragraphs) > 3:
            return paragraphs[0].parent
        
        return soup.find('body')
    
    def _get_inner_text(self, element):
        """
        Get text equivalent to JavaScript innerText || textContent with proper formatting
        """
        if not element:
            return ''
        try:
            text = element.get_text(separator='\n', strip=True)
            lines = [ln.strip() for ln in text.split('\n') if ln.strip()]
            return '\n'.join(lines)
        except:
            return element.get_text(strip=True)

class ChunkProcessor:
    """
    Handles interaction with chunk.dejan.ai using Selenium and network-based JSON detection
    in a background thread to avoid blocking Streamlit's UI.
    """
    def __init__(self):
        self.driver = None
        self.setup_driver()

    def setup_driver(self):
        """
        Initialize Chrome WebDriver with both performance logging and
        the existing stability flags.
        """
        try:
            # Merge performance logging with stability options
            caps = DesiredCapabilities.CHROME.copy()
            caps['goog:loggingPrefs'] = {'performance': 'ALL'}

            chrome_options = Options()
            chrome_options.add_argument('--headless=new')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--disable-web-security')
            chrome_options.add_argument('--disable-extensions')
            chrome_options.add_argument('--disable-plugins')
            chrome_options.add_argument('--disable-images')
            chrome_options.add_argument('--disable-background-timer-throttling')
            chrome_options.add_argument('--window-size=1280,720')
            chrome_options.add_argument('--start-maximized')
            chrome_options.add_argument('--user-agent=Mozilla/5.0 (X11; Linux x86_64)')

            self.driver = webdriver.Chrome(desired_capabilities=caps, options=chrome_options)
            self.driver.set_page_load_timeout(60)
            self.driver.implicitly_wait(15)
            logger.info('WebDriver initialized with performance logging and stability flags')
            return True
        except Exception as e:
            logger.error(f'Driver init failed: {e}')
            return False

    def process_content(self, content):
        """
        Submit content to chunk.dejan.ai, then offload network-log polling to a
        background thread to detect the fetch response without blocking.
        """
        max_retries = 2
        for attempt in range(max_retries):
            if not self.driver and not self.setup_driver():
                return False, None, 'Browser init failed'

            try:
                logger.info(f'Attempt {attempt+1}/{max_retries}: navigating to chunk.dejan.ai')
                self.driver.get('https://chunk.dejan.ai/')
                time.sleep(8)

                # fill input
                wait = WebDriverWait(self.driver, 45)
                textbox = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'textarea')))
                textbox.clear()
                textbox.send_keys(content[:3000])
                time.sleep(1)

                # click generate
                gen_btn = wait.until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, '[data-testid="stBaseButton-secondary"]'))
                )
                gen_btn.click()

                # background thread to wait for network response
                def network_ready():
                    start = time.time()
                    while time.time() - start < 180:
                        logs = self.driver.get_log('performance')
                        for entry in logs:
                            msg = json.loads(entry['message'])['message']
                            if msg.get('method') == 'Network.responseReceived':
                                r = msg['params']['response']
                                if 'chunk.dejan.ai' in r.get('url', '') and r.get('status') == 200:
                                    return True
                        time.sleep(0.5)
                    return False

                from concurrent.futures import ThreadPoolExecutor
                with ThreadPoolExecutor(max_workers=1) as executor:
                    future = executor.submit(network_ready)
                    if not future.result():
                        raise TimeoutException('Network JSON response not received')
                logger.info('Network JSON response received')

                # extract JSON
                copy_btn = self.driver.find_element(By.CSS_SELECTOR, '[data-testid="stCodeCopyButton"]')
                json_text = copy_btn.get_attribute('data-clipboard-text')
                json.loads(json_text)
                return True, json_text, None

            except Exception as e:
                logger.warning(f'Attempt {attempt+1} failed: {e}')
                if attempt == max_retries - 1:
                    return False, None, str(e)
                self.cleanup()
                time.sleep(5)
        return False, None, 'All attempts failed'
        
def validate_url(url):
    """
    Validate that the provided URL is properly formatted and accessible
    """
    try:
        parsed = urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            return False, "Invalid URL format. Please include http:// or https://"
        if parsed.scheme not in ['http', 'https']:
            return False, "URL must use http:// or https://"
        return True, None
    except Exception as e:
        return False, f"Invalid URL: {str(e)}"

def process_url_workflow_with_logging(url, log_callback=None):
    """
    Complete workflow function with live logging updates
    """
    def log(message):
        if log_callback:
            log_callback(message)
        logger.info(message)
    
    result = {
        'success': False,
        'url': url,
        'extracted_content': None,
        'json_output': None,
        'error': None,
        'step': 'Starting...'
    }
    
    log("🚀 Initializing content extractor...")
    extractor = ContentExtractor()
    log("🤖 Initializing chunk processor...")
    processor = ChunkProcessor()
    
    try:
        log(f"🔍 Fetching content from: {url}")
        result['step'] = 'Extracting content from URL...'
        success, content, error = extractor.extract_content(url)
        if not success:
            log(f"❌ Content extraction failed: {error}")
            result['error'] = f"Content extraction failed: {error}"
            return result
        
        log(f"✅ Content extracted: {len(content)} characters")
        if not content or content.strip() == 'No content found' or len(content.strip()) < 50:
            log("⚠️ Insufficient content extracted")
            result['error'] = "Insufficient content extracted from URL. Please check if the URL contains readable content."
            return result
        
        result['extracted_content'] = content
        log("📝 Content validation passed")
        
        log("🔄 Starting chunk.dejan.ai processing...")
        result['step'] = 'Processing content through chunk.dejan.ai...'
        success, json_output, error = processor.process_content(content)
        if not success:
            log(f"❌ Chunk processing failed: {error}")
            result['error'] = f"Chunk processing failed: {error}"
            return result
        
        log("✅ JSON chunks generated successfully!")
        result['json_output'] = json_output
        result['success'] = True
        result['step'] = 'Completed successfully!'
        
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
        log("🧹 Cleaning up browser resources...")
        processor.cleanup()
        log("✅ Cleanup completed")

def process_url_workflow(url):
    return process_url_workflow_with_logging(url)

def main():
    """
    Main Streamlit application interface
    """
    st.title("🔄 Content Processor")
    st.markdown("**Automatically extract content from websites and generate JSON chunks**")
    
    debug_mode = st.sidebar.checkbox("🐛 Debug Mode", help="Show detailed processing logs")
    st.markdown("---")
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("📝 Input URL")
        url = st.text_input(
            "Enter the URL to process:",
            placeholder="https://example.com/article",
            help="Enter a complete URL including http:// or https://"
        )
        
        if st.button("🚀 Process URL", type="primary", use_container_width=True):
            if not url:
                st.error("Please enter a URL to process")
                return
            is_valid, error_msg = validate_url(url)
            if not is_valid:
                st.error(error_msg)
                return
            
            with st.spinner("Processing your request..."):
                progress_placeholder = st.empty()
                status_placeholder = st.empty()
                log_placeholder = st.empty()
                
                log_container = st.container()
                with log_container:
                    st.subheader("📋 Processing Log")
                    log_messages = []
                
                def log_callback(message):
                    log_messages.append(f"• {message}")
                    if debug_mode:
                        with log_placeholder.container():
                            for msg in log_messages[-10:]:
                                st.text(msg)
                
                progress_placeholder.progress(0.1)
                status_placeholder.info("🔍 Validating URL and starting extraction...")
                result = process_url_workflow_with_logging(url, log_callback if debug_mode else None)
                
                if result['success']:
                    progress_placeholder.progress(1.0)
                    status_placeholder.success("✅ Processing completed successfully!")
                    st.session_state['latest_result'] = result
                else:
                    progress_placeholder.progress(0.5)
                    status_placeholder.error(f"❌ Error: {result['error']}")
    
    with col2:
        st.subheader("ℹ️ How it works")
        st.markdown("""
        1. **Extract**: Scrapes content from your URL  
        2. **Process**: Sends content to chunk.dejan.ai  
        3. **Generate**: Returns structured JSON chunks  
        4. **Display**: Shows results below
        """)
        st.info("💡 **Tip**: Works best with articles, blog posts, and structured content")
    
    if ('latest_result' in st.session_state and 
        st.session_state['latest_result'] and 
        st.session_state['latest_result'].get('success', False)):
        result = st.session_state['latest_result']
        st.markdown("---")
        st.subheader("📊 Results")
        tab1, tab2, tab3 = st.tabs(["🎯 JSON Output", "📄 Extracted Content", "📈 Summary"])
        
        with tab1:
            st.subheader("Generated JSON Chunks")
            st.code(result['json_output'], language='json')
            st.download_button(
                label="💾 Download JSON",
                data=result['json_output'],
                file_name=f"chunks_{int(time.time())}.json",
                mime="application/json"
            )
        with tab2:
            st.subheader("Extracted Content")
            st.markdown("**Formatted content as extracted by the bookmarklet logic:**")
            extracted_content_display = st.text_area(
                "Raw extracted content (copyable):",
                value=result['extracted_content'],
                height=400,
                disabled=False,
                help="This content is formatted exactly like the original bookmarklet."
            )
            if st.button("📋 Copy Extracted Content", key="copy_extracted"):
                st.success("✅ Content copied to clipboard!")
            
            content_lines = result['extracted_content'].split('\n\n')
            h1_count = len([l for l in content_lines if l.startswith('H1:')])
            subtitle_count = len([l for l in content_lines if l.startswith('SUBTITLE:')])
            lead_count = len([l for l in content_lines if l.startswith('LEAD:')])
            has_main = any(l.startswith('CONTENT:') for l in content_lines)
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("H1 Headers", h1_count)
            c2.metric("Subtitles", subtitle_count)
            c3.metric("Lead Paragraphs", lead_count)
            c4.metric("Main Content", "✅ Yes" if has_main else "❌ No")
        
        with tab3:
            st.subheader("Processing Summary")
            try:
                json_data = json.loads(result['json_output'])
                if 'big_chunks' in json_data:
                    big = len(json_data['big_chunks'])
                    small = sum(len(ch.get('small_chunks', [])) for ch in json_data['big_chunks'])
                    colA, colB, colC = st.columns(3)
                    colA.metric("Big Chunks", big)
                    colB.metric("Small Chunks", small)
                    colC.metric("Content Length", f"{len(result['extracted_content'])} chars")
            except json.JSONDecodeError:
                st.warning("Could not parse JSON for statistics")
            st.info(f"**Source URL**: {result['url']}")
    
    st.markdown("---")
    st.markdown(
        "<div style='text-align: center; color: #666;'>"
        "Built with Streamlit • Powered by chunk.dejan.ai"
        "</div>", 
        unsafe_allow_html=True
    )

if 'latest_result' not in st.session_state:
    st.session_state['latest_result'] = None

if __name__ == "__main__":
    main()
