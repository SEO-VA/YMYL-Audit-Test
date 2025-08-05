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
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium.common.exceptions import TimeoutException, WebDriverException
import json
import time
import logging
from urllib.parse import urlparse
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
        try:
            time.sleep(1)
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            content_parts = []
            main_container = self._find_main_container_exact(soup)

            # H1 elements
            for h1 in soup.find_all('h1'):
                text = self._get_inner_text(h1)
                if text.strip():
                    content_parts.append(f'H1: {text.strip()}')

            # Subtitles
            subtitle_selectors = '.sub-title,.subtitle,[class*="sub-title"],[class*="subtitle"]'
            for subtitle in soup.select(subtitle_selectors):
                cls = ' '.join(subtitle.get('class', []))
                if 'd-block' in cls or subtitle.find_parent(class_='d-block'):
                    text = self._get_inner_text(subtitle)
                    if text.strip():
                        content_parts.append(f'SUBTITLE: {text.strip()}')

            # Lead paragraphs
            for lead in soup.select('.lead,[class*="lead"]'):
                text = self._get_inner_text(lead)
                if text.strip():
                    content_parts.append(f'LEAD: {text.strip()}')

            # Main content
            if main_container:
                main_text = self._get_inner_text(main_container) or ''
                if main_text.strip():
                    content_parts.append(f'CONTENT: {main_text.strip()}')

            final_content = '\n\n'.join(content_parts) if content_parts else 'No content found'
            return True, final_content, None
        except Exception as e:
            return False, None, f"Error processing content: {e}"

    def _find_main_container_exact(self, soup):
        selectors = ['article', 'main', '.content', '#content', '[role="main"]']
        for sel in selectors:
            el = soup.select_one(sel)
            if el:
                return el
        ps = soup.find_all('p')
        if len(ps) > 3:
            return ps[0].parent
        return soup.find('body')

    def _get_inner_text(self, el):
        if not el:
            return ''
        try:
            txt = el.get_text(separator='\n', strip=True)
            lines = [l.strip() for l in txt.split('\n') if l.strip()]
            return '\n'.join(lines)
        except:
            return el.get_text(strip=True)

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

    def cleanup(self):
        """
        Clean up browser resources.
        """
        if self.driver:
            try:
                self.driver.quit()
            except Exception:
                pass

# URL validation
def validate_url(url):
    try:
        parsed = urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            return False, "Invalid URL format. Please include http:// or https://"
        if parsed.scheme not in ['http', 'https']:
            return False, "URL must use http:// or https://"
        return True, None
    except Exception as e:
        return False, f"Invalid URL: {e}"

# Workflow logic def process_url_workflow_with_logging(url, log_callback=None):
    def log(message):
        if log_callback:
            log_callback(message)
        logger.info(message)

    result = {'success': False,'url': url,'extracted_content': None,'json_output': None,'error': None,'step': 'Starting...'}
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
            result['error'] = "Insufficient content extracted."
            return result
        result['extracted_content'] = content
        log("📝 Content validation passed")

        log("🔄 Processing through chunk.dejan.ai...")
        result['step'] = 'Processing content...'
        success, js, err = processor.process_content(content)
        if not success:
            log(f"❌ Chunk processing failed: {err}")
            result['error'] = f"Chunk processing failed: {err}"
            return result

        result['json_output'] = js
        result['success'] = True
        result['step'] = 'Completed successfully!'
        log("✅ JSON chunks generated!")
    except Exception as e:
        log(f"💥 Unexpected error: {e}")
        result['error'] = f"Unexpected error: {e}"
    finally:
        log("🧹 Cleaning up...")
        processor.cleanup()
        log("✅ Cleanup done")

    return result

# Backward compatibility
def process_url_workflow(url):
    return process_url_workflow_with_logging(url)

# Streamlit UI
def main():
    st.title("🔄 Content Processor")
    st.markdown("**Automatically extract content and generate JSON chunks**")
    debug_mode = st.sidebar.checkbox("🐛 Debug Mode")
    col1, col2 = st.columns([2,1])
    with col1:
        st.subheader("📝 Input URL")
        url = st.text_input("Enter URL:", placeholder="https://example.com/article")
        if st.button("🚀 Process URL"):
            if not url:
                st.error("Enter a URL")
            else:
                valid, err = validate_url(url)
                if not valid:
                    st.error(err)
                else:
                    with st.spinner("Processing..."):
                        logs=[]
                        def cb(m):
                            logs.append(m)
                            if debug_mode:
                                st.text(m)
                        result = process_url_workflow_with_logging(url, cb if debug_mode else None)
                    if result['success']:
                        st.success("Completed!")
                        st.session_state['latest'] = result
                    else:
                        st.error(result['error'])
    with col2:
        st.subheader("ℹ️ How it works")
        st.markdown("1. Extract • 2. Process • 3. Generate • 4. Display")
    if 'latest' in st.session_state and st.session_state['latest']['success']:
        res = st.session_state['latest']
        st.markdown("---")
        tabs = st.tabs(["JSON","Content","Summary"])
        with tabs[0]:
            st.code(res['json_output'], language='json')
            st.download_button("💾 Download JSON", res['json_output'], file_name="chunks.json")
        with tabs[1]:
            st.text_area("Extracted Content", res['extracted_content'], height=300)
        with tabs[2]:
            data = json.loads(res['json_output'])
            if 'big_chunks' in data:
                big=len(data['big_chunks'])
                small=sum(len(c.get('small_chunks',[])) for c in data['big_chunks'])
                st.metric("Big Chunks", big)
                st.metric("Small Chunks", small)
                st.metric("Content Length", f"{len(res['extracted_content'])} chars")

if __name__ == "__main__":
    main()
