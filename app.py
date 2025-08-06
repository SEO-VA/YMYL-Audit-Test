#!/usr/bin/env python3
"""
Content Processing Web Application (Final Version)

A Streamlit web app that scrapes full-length content from URLs and
reliably processes them through chunk.dejan.ai to generate complete JSON chunks.
This version incorporates all bug fixes and robust automation logic discovered
during extensive testing.
"""

import streamlit as st
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, WebDriverException
import json
import time
import html
from datetime import datetime
import pytz
import platform
import logging

# --- Logging Configuration ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Streamlit Page Configuration ---
st.set_page_config(
    page_title="Content Processor",
    page_icon="🚀",
    layout="wide",
)

# --- Component 1: Content Extractor (Unchanged from Original) ---
class ContentExtractor:
    """
    Handles content extraction from websites using the exact logic from the JavaScript bookmarklet.
    """
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })

    def extract_content(self, url):
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            content_parts = []
            main_container_selectors = ['article', 'main', '.content', '#content', '[role="main"]']
            main_container = None
            for selector in main_container_selectors:
                main_container = soup.select_one(selector)
                if main_container: break
            if not main_container:
                if len(soup.find_all('p')) > 3: main_container = soup.find_all('p')[0].parent
                else: main_container = soup.body
            for h1 in soup.find_all('h1'):
                text = h1.get_text(separator='\n', strip=True)
                if text: content_parts.append(f'H1: {text}')
            for st_element in soup.select('.sub-title,.subtitle,[class*="sub-title"],[class*="subtitle"]'):
                text = st_element.get_text(separator='\n', strip=True)
                if text: content_parts.append(f'SUBTITLE: {text}')
            for lead in soup.select('.lead,[class*="lead"]'):
                text = lead.get_text(separator='\n', strip=True)
                if text: content_parts.append(f'LEAD: {text}')
            if main_container:
                main_text = main_container.get_text(separator='\n', strip=True)
                if main_text: content_parts.append(f'CONTENT: {main_text}')
            return True, '\n\n'.join(content_parts) or "No content found", None
        except requests.RequestException as e:
            return False, None, f"Error fetching URL: {e}"

# --- Component 2: The Upgraded Chunk Processor ---
class ChunkProcessor:
    """
    Handles interaction with chunk.dejan.ai using the final, robust automation logic.
    """
    def __init__(self, log_callback=None):
        self.driver = None
        self.log = log_callback if log_callback else logger.info

    def _setup_driver(self):
        self.log("Initializing browser with enhanced stability & permissions...")
        chrome_options = Options()
        chrome_options.add_argument('--headless=new')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        # Grant clipboard permissions for headless mode, essential for the copy-paste method
        chrome_options.add_experimental_option("prefs", {"profile.default_content_setting_values.clipboard": 1})
        try:
            self.driver = webdriver.Chrome(options=chrome_options)
            self.log("✅ Browser initialized successfully.")
            return True
        except WebDriverException as e:
            self.log(f"❌ WebDriver Initialization Failed: {e}")
            return False

    def _extract_json_from_button(self):
        try:
            wait = WebDriverWait(self.driver, 180) # Generous 3-minute wait for the whole process
            # Step 1: Wait for the H3 heading as the primary signal of completion.
            h3_xpath = "//h3[text()='Raw JSON Output']"
            self.log("🔄 Waiting for results section to appear (by finding H3 heading)...")
            wait.until(EC.presence_of_element_located((By.XPATH, h3_xpath)))
            self.log("✅ Results section is visible.")
            
            # Step 2: Wait for the copy button to exist.
            button_selector = "button[data-testid='stCodeCopyButton']"
            self.log("...Waiting for the copy button to be added to the page...")
            copy_button = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, button_selector)))
            self.log("✅ Found the copy button element.")
            
            # Step 3: Poll the button's attribute to ensure it's fully populated.
            self.log("...Polling button's 'data-clipboard-text' attribute for completeness...")
            timeout = time.time() + 10 # Poll for up to 10 seconds
            final_content = ""
            while time.time() < timeout:
                raw_content = copy_button.get_attribute('data-clipboard-text')
                if raw_content and raw_content.strip().startswith('{') and raw_content.strip().endswith('}'):
                    final_content = raw_content; break
                time.sleep(0.2)
            if not final_content: self.log("❌ Timed out polling the attribute."); return None
            self.log("✅ Attribute is fully populated.")
            
            # Step 4: Decode the HTML entities from the string.
            self.log("...Decoding HTML entities...")
            decoded_content = html.unescape(final_content)
            self.log(f"✅ Extraction complete. Retrieved {len(decoded_content):,} characters.")
            return decoded_content
        except Exception as e:
            self.log(f"❌ An error occurred during the final JSON extraction phase: {e}")
            return None

    def process_content(self, content):
        if not self._setup_driver():
            return False, None, "Failed to initialize browser."
        try:
            self.log(f"Navigating to `chunk.dejan.ai`...")
            self.driver.get("https://chunk.dejan.ai/")
            wait = WebDriverWait(self.driver, 30)
            
            # --- FINAL INPUT METHOD: COPY-PASTE ---
            self.log("Using JavaScript to copy full text to browser's clipboard...")
            self.driver.execute_script("navigator.clipboard.writeText(arguments[0]);", content)
            self.log("✅ Content copied to clipboard.")
            
            self.log("Locating text area...")
            textarea_selector = (By.CSS_SELECTOR, 'textarea[aria-label="Text to chunk:"]')
            input_field = wait.until(EC.element_to_be_clickable(textarea_selector))
            input_field.clear()
            
            self.log("Simulating a 'Paste' (Ctrl+V) command into the text area...")
            modifier_key = Keys.COMMAND if platform.system() == "Darwin" else Keys.CONTROL
            input_field.send_keys(modifier_key, "v")
            self.log("✅ Paste command sent successfully.")

            self.log("Clicking submit button...")
            submit_button = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, '[data-testid="stBaseButton-secondary"]')))
            submit_button.click()
            
            json_output = self._extract_json_from_button()
            
            if json_output:
                return True, json_output, None
            else:
                return False, None, "Failed to extract JSON from the results page."

        except Exception as e:
            return False, None, f"An unexpected error occurred during processing: {e}"
        finally:
            self.cleanup()
            
    def cleanup(self):
        if self.driver:
            self.log("Cleaning up and closing browser instance.")
            self.driver.quit()
            self.log("✅ Browser closed.")

# --- Main Application UI and Workflow ---
def main():
    st.title("🚀 Content Processing Automation")
    st.markdown("Enter a URL to scrape its content, process it through `chunk.dejan.ai`, and extract the resulting JSON.")
    st.info("This application now uses a robust copy-paste method to handle large content and a resilient polling mechanism to extract the complete JSON result.", icon="💡")

    url_to_process = st.text_input(
        "Enter the URL to process:",
        "https://www.casinohawks.com/bonuses/bonus-code",
        help="Enter a full URL of an article to scrape and process."
    )

    if st.button("🚀 Process URL", type="primary", use_container_width=True):
        if not url_to_process:
            st.error("Please enter a URL to process.")
            return

        st.subheader("📋 Real-time Processing Log")
        log_messages = []
        log_container = st.empty()
        
        def log_callback(message):
            utc_now = datetime.now(pytz.utc)
            cest_tz = pytz.timezone('Europe/Malta')
            cest_now = utc_now.astimezone(cest_tz)
            log_messages.append(f"`{cest_now.strftime('%H:%M:%S')} (CEST) / {utc_now.strftime('%H:%M:%S')} (UTC)`: {message}")
            log_container.info("\n\n".join(log_messages))

        with st.spinner("Processing in progress... This may take several minutes for large content."):
            # Step 1: Extract content
            log_callback("Initializing ContentExtractor...")
            extractor = ContentExtractor()
            log_callback(f"Extracting content from: {url_to_process}")
            success, content_to_submit, error = extractor.extract_content(url_to_process)
            
            if not success:
                st.error(f"Failed to extract content: {error}")
                return
            
            st.session_state['extracted_content'] = content_to_submit
            log_callback(f"✅ Content extracted successfully ({len(content_to_submit):,} chars).")

            # Step 2: Process content
            processor = ChunkProcessor(log_callback=log_callback)
            success, json_output, error = processor.process_content(content_to_submit)
            
            if not success:
                st.error(f"Failed to process content: {error}")
                return

            st.session_state['json_output'] = json_output
            log_callback("🎉 Workflow Complete!")
            st.success("Processing complete! View the results below.")
            
    if 'json_output' in st.session_state:
        st.markdown("---")
        st.subheader("📊 Results")
        tab1, tab2 = st.tabs(["🎯 JSON Output", "📄 Extracted Content"])

        with tab1:
            st.code(st.session_state['json_output'], language='json')
            st.download_button(
                "💾 Download Full Extracted JSON",
                data=st.session_state['json_output'],
                file_name=f"chunks_{int(time.time())}.json",
                mime="application/json"
            )
        with tab2:
            st.text_area("Scraped Content Sent for Processing:", st.session_state.get('extracted_content', ''), height=300)

if __name__ == "__main__":
    main()
