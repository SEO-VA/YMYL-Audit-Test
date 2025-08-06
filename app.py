#!/usr/bin/env python3
"""
Content Processing Web Application with AI Integration

This script combines content extraction with AI processing via Make.com integration.
Users can extract content and then send it for AI analysis with a single button click.
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

# --- Component 1: Content Extractor ---
class ContentExtractor:
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

# --- Component 2: Chunk Processor ---
class ChunkProcessor:
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
            wait = WebDriverWait(self.driver, 180)
            h3_xpath = "//h3[text()='Raw JSON Output']"
            self.log("🔄 Waiting for results section to appear...")
            wait.until(EC.presence_of_element_located((By.XPATH, h3_xpath)))
            self.log("✅ Results section is visible.")
            button_selector = "button[data-testid='stCodeCopyButton']"
            self.log("...Waiting for the copy button...")
            copy_button = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, button_selector)))
            self.log("✅ Found the copy button element.")
            self.log("...Polling button's attribute for completeness...")
            timeout = time.time() + 10
            final_content = ""
            while time.time() < timeout:
                raw_content = copy_button.get_attribute('data-clipboard-text')
                if raw_content and raw_content.strip().startswith('{') and raw_content.strip().endswith('}'):
                    final_content = raw_content; break
                time.sleep(0.2)
            if not final_content: self.log("❌ Timed out polling the attribute."); return None
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
            self.log("Using JavaScript to copy full text to browser's clipboard...")
            self.driver.execute_script("navigator.clipboard.writeText(arguments[0]);", content)
            self.log("Locating text area and clearing it...")
            textarea_selector = (By.CSS_SELECTOR, 'textarea[aria-label="Text to chunk:"]')
            input_field = wait.until(EC.element_to_be_clickable(textarea_selector))
            input_field.clear()
            self.log("Simulating a 'Paste' (Ctrl+V) command...")
            modifier_key = Keys.COMMAND if platform.system() == "Darwin" else Keys.CONTROL
            input_field.send_keys(modifier_key, "v")
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

# --- AI Processing Integration ---
def send_to_ai_processing(url, extracted_content):
    """Send extracted content to Make.com for AI processing"""
    # Get webhook URL from session state
    webhook_url = st.session_state.get('makecom_webhook_url', '')
    
    if not webhook_url or webhook_url == 'https://hook.make.com/YOUR_WEBHOOK_ID_HERE':
        return False, "Please configure your Make.com webhook URL in the sidebar first."
    
    try:
        payload = {
            "url": url,
            "extracted_content": extracted_content,
            "content_length": len(extracted_content),
            "timestamp": datetime.now().isoformat(),
            "analysis_depth": st.session_state.get('analysis_depth', 'Standard'),
            "output_format": st.session_state.get('output_format', 'Google Doc')
        }
        
        response = requests.post(webhook_url, json=payload, timeout=30)
        
        if response.status_code == 200:
            return True, "Content sent for AI processing successfully!"
        else:
            return False, f"Error: HTTP {response.status_code} - {response.text}"
            
    except requests.RequestException as e:
        return False, f"Error sending to AI processor: {str(e)}"

# --- Main Workflow Function ---
def process_url_workflow_with_logging(url, log_callback=None):
    result = {'success': False, 'url': url, 'extracted_content': None, 'json_output': None, 'error': None}
    
    def log(message):
        if log_callback: log_callback(message)
        logger.info(message)
        
    try:
        log("🚀 Initializing content extractor...")
        extractor = ContentExtractor()
        log(f"🔍 Fetching and extracting content from: {url}")
        success, content, error = extractor.extract_content(url)
        if not success:
            result['error'] = f"Content extraction failed: {error}"; return result
        result['extracted_content'] = content
        log(f"✅ Content extracted: {len(content):,} characters")

        log("🤖 Initializing chunk processor...")
        processor = ChunkProcessor(log_callback=log)
        success, json_output, error = processor.process_content(content)
        if not success:
            result['error'] = f"Chunk processing failed: {error}"; return result
        
        result['json_output'] = json_output
        result['success'] = True
        log("🎉 Workflow Complete!")
        return result
    except Exception as e:
        log(f"💥 An unexpected error occurred in the workflow: {str(e)}")
        result['error'] = f"An unexpected workflow error occurred: {str(e)}"
        return result

# --- API Handler Function ---
def handle_api_request():
    """Handle API-style requests using query parameters"""
    try:
        query_params = st.query_params
        
        if "api" in query_params and "url" in query_params:
            url = query_params["url"]
            extractor = ContentExtractor()
            success, content, error = extractor.extract_content(url)
            
            if success:
                st.json({
                    "success": True,
                    "extracted_content": content,
                    "content_length": len(content)
                })
                st.stop()
            else:
                st.json({
                    "success": False,
                    "error": error
                })
                st.stop()
                
    except Exception as e:
        pass

# --- AI Configuration Sidebar ---
def add_ai_configuration_sidebar():
    """Add AI configuration options to sidebar"""
    with st.sidebar:
        st.markdown("---")
        st.subheader("🤖 AI Processing Settings")
        
        # Make.com webhook URL configuration
        webhook_url = st.text_input(
            "Make.com Webhook URL:",
            value=st.session_state.get('makecom_webhook_url', ''),
            placeholder="https://hook.make.com/...",
            help="Enter your Make.com webhook URL for AI processing"
        )
        
        if webhook_url:
            st.session_state['makecom_webhook_url'] = webhook_url
            st.success("✅ Webhook URL configured")
        else:
            st.warning("⚠️ Configure webhook URL to enable AI processing")
        
        # AI Processing Options
        analysis_depth = st.selectbox(
            "Analysis Depth:",
            ["Standard", "Deep Analysis", "Quick Overview"],
            index=0,
            help="Choose the depth of AI analysis"
        )
        st.session_state['analysis_depth'] = analysis_depth
        
        output_format = st.selectbox(
            "Output Format:",
            ["Google Doc", "PDF Report", "JSON Summary"],
            index=0,
            help="Choose how you want to receive results"
        )
        st.session_state['output_format'] = output_format
        
        # AI Processing Info
        with st.expander("ℹ️ AI Processing Info"):
            st.markdown("""
            **What happens when you click 'Process with AI':**
            
            1. **Coordinator**: Analyzes content structure
            2. **Analyzer**: Processes section by section
            3. **Output Formatter**: Creates final formatted output
            4. **Delivery**: Results sent via your chosen format
            
            **Processing time:** 2-5 minutes depending on content length
            """)

# --- Streamlit UI ---
def main():
    # Check for API requests first
    handle_api_request()
    
    # Page configuration
    st.set_page_config(
        page_title="Content Processor with AI",
        page_icon="🚀",
        layout="wide",
    )
    
    st.title("🔄 Content Processor with AI Integration")
    st.markdown("**Extract content from websites and process with AI analysis**")
    
    # Sidebar configuration
    debug_mode = st.sidebar.checkbox("🐛 Debug Mode", help="Show detailed processing logs")
    add_ai_configuration_sidebar()
    
    st.markdown("---")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        url = st.text_input(
            "Enter the URL to process:",
            placeholder="https://www.example.com/article",
            help="Enter a complete URL including http:// or https://"
        )
        
        col_process, col_ai_only = st.columns([3, 1])
        
        with col_process:
            process_button = st.button("🚀 Extract Content", type="primary", use_container_width=True)
        
        with col_ai_only:
            # Quick AI processing button for already extracted content
            if 'latest_result' in st.session_state and st.session_state['latest_result']['success']:
                ai_only_button = st.button("🤖 AI Process", use_container_width=True)
                if ai_only_button:
                    result = st.session_state['latest_result']
                    with st.spinner("Sending content for AI processing..."):
                        success, message = send_to_ai_processing(
                            result['url'], 
                            result['extracted_content']
                        )
                        
                        if success:
                            st.success(message)
                            st.info("🔄 AI processing started! Check your configured output method.")
                            st.session_state['ai_processing_sent'] = True
                        else:
                            st.error(f"❌ {message}")
        
        if process_button:
            if not url:
                st.error("Please enter a URL to process")
                return
            
            with st.spinner("Processing your request... Please wait."):
                log_placeholder = st.empty()
                log_messages = []

                def log_callback(message):
                    utc_now = datetime.now(pytz.utc)
                    cest_tz = pytz.timezone('Europe/Malta')
                    cest_now = utc_now.astimezone(cest_tz)
                    log_messages.append(f"`{cest_now.strftime('%H:%M:%S')} (CEST)`: {message}")
                    with log_placeholder.container():
                        st.info("\n\n".join(log_messages))
                
                result = process_url_workflow_with_logging(url, log_callback if debug_mode else None)
                st.session_state['latest_result'] = result
                st.session_state['ai_processing_sent'] = False  # Reset AI processing status

                if result['success']:
                    st.success("Content extraction completed successfully!")
                else:
                    st.error(f"An error occurred: {result['error']}")

    with col2:
        st.subheader("ℹ️ How it works")
        st.markdown("""
        **Content Extraction:**
        1. **Extract**: Scrapes and formats content from your URL
        2. **Process**: Generates JSON chunks via chunk.dejan.ai
        3. **Display**: Shows structured results
        
        **AI Processing:**
        4. **Analyze**: AI processes content section by section
        5. **Coordinate**: AI creates processing plan
        6. **Format**: AI generates final formatted output
        7. **Deliver**: Results sent via your chosen method
        """)
        st.info("💡 **Tip**: Configure your Make.com webhook URL in the sidebar to enable AI processing.")

    # Results Display
    if 'latest_result' in st.session_state and st.session_state['latest_result']['success']:
        result = st.session_state['latest_result']
        st.markdown("---")
        
        # Header with AI Processing Button
        col_header, col_ai_button = st.columns([3, 1])
        
        with col_header:
            st.subheader("📊 Results")
        
        with col_ai_button:
            if st.button("🤖 Process with AI", type="primary", use_container_width=True):
                with st.spinner("Sending content for AI processing..."):
                    success, message = send_to_ai_processing(
                        result['url'], 
                        result['extracted_content']
                    )
                    
                    if success:
                        st.success(message)
                        st.info("🔄 AI processing started! You'll receive results via your configured method.")
                        st.session_state['ai_processing_sent'] = True
                    else:
                        st.error(f"❌ {message}")
        
        # Show AI processing status
        if st.session_state.get('ai_processing_sent', False):
            st.success("🤖 **AI Processing Status:** Content has been sent for analysis. Processing time: 2-5 minutes.")
        
        # Results tabs
        tab1, tab2, tab3, tab4 = st.tabs(["🎯 JSON Output", "📄 Extracted Content", "🤖 AI Preview", "📈 Summary"])
        
        with tab1:
            st.code(result['json_output'], language='json')
            st.download_button(
                label="💾 Download JSON",
                data=result['json_output'],
                file_name=f"chunks_{int(time.time())}.json",
                mime="application/json"
            )
        
        with tab2:
            st.text_area("Raw extracted content:", value=result['extracted_content'], height=400)
        
        with tab3:
            st.subheader("🤖 Content Prepared for AI Analysis")
            st.markdown("**This formatted content will be sent to your AI processing pipeline:**")
            
            # Show formatted preview
            content_preview = result['extracted_content'][:800] + "..." if len(result['extracted_content']) > 800 else result['extracted_content']
            st.code(content_preview, language='text')
            
            if len(result['extracted_content']) > 800:
                with st.expander("Show complete content"):
                    st.code(result['extracted_content'], language='text')
            
            # AI Processing Pipeline Info
            st.markdown("---")
            st.subheader("🔄 AI Processing Pipeline")
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.markdown("""
                **1. Coordinator**
                - Analyzes content structure
                - Creates processing plan
                - Identifies key sections
                """)
            
            with col2:
                st.markdown("""
                **2. Analyzer** 
                - Section-by-section analysis
                - Detailed content review
                - Structured insights
                """)
            
            with col3:
                st.markdown("""
                **3. Output Formatter**
                - Combines all analyses
                - Formats final output
                - Delivers via chosen method
                """)
        
        with tab4:
            st.subheader("Processing Summary")
            try:
                json_data = json.loads(result['json_output'])
                big_chunks = json_data.get('big_chunks', [])
                total_small_chunks = sum(len(chunk.get('small_chunks', [])) for chunk in big_chunks)
                
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("Big Chunks", len(big_chunks))
                col2.metric("Total Small Chunks", total_small_chunks)
                col3.metric("Content Length", f"{len(result['extracted_content']):,} chars")
                col4.metric("Processing Time", "2-5 min")
                
                # AI Processing Readiness
                st.markdown("---")
                st.subheader("🤖 AI Processing Readiness")
                
                col_left, col_right = st.columns(2)
                with col_left:
                    st.metric("Sections for AI Analysis", len(big_chunks) if big_chunks else 1)
                    st.metric("Content Format", "✅ H1/CONTENT structured")
                
                with col_right:
                    webhook_configured = bool(st.session_state.get('makecom_webhook_url'))
                    st.metric("Webhook Status", "✅ Configured" if webhook_configured else "⚠️ Not configured")
                    st.metric("Analysis Depth", st.session_state.get('analysis_depth', 'Standard'))
                
            except (json.JSONDecodeError, TypeError):
                st.warning("Could not parse JSON for detailed statistics.")
            
            st.info(f"**Source URL**: {result['url']}")

if __name__ == "__main__":
    main()
