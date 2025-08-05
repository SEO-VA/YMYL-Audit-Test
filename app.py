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
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities

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
        """
        Extract structured content using EXACT logic from the JavaScript bookmarklet

        Args:
            url (str): Source URL to scrape

        Returns:
            tuple: (success: bool, content: str, error: str)
        """
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
                class_names = ' '.join(subtitle.get('class', []))
                has_d_block = 'd-block' in class_names
                closest_d = subtitle.find_parent(class_='d-block') is not None
                if has_d_block or closest_d:
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

        except requests.RequestException as e:
            return False, None, f"Error fetching URL: {e}"
        except Exception as e:
            return False, None, f"Error processing content: {e}"

    def _find_main_container_exact(self, soup):
        selectors = ['article', 'main', '.content', '#content', '[role="main"]']
        for sel in selectors:
            c = soup.select_one(sel)
            if c:
                return c
        ps = soup.find_all('p')
        if len(ps) > 3:
            return ps[0].parent
        return soup.find('body')

    def _get_inner_text(self, element):
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
    Handles interaction with chunk.dejan.ai using Selenium automation
    and explicit wait for JSON readiness.
    """

    def __init__(self):
        self.driver = None
        self.setup_driver()

    def setup_driver(self):
        """
        Initialize Chrome WebDriver with ultra-stable settings for Streamlit Cloud.
        """
        try:
            # Enable performance logging for network debugging if needed
            caps = DesiredCapabilities.CHROME.copy()
            caps['goog:loggingPrefs'] = {'performance': 'ALL'}

            chrome_options = Options()
            chrome_options.add_argument('--headless=new')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--disable-web-security')
            chrome_options.add_argument('--disable-features=VizDisplayCompositor')
            chrome_options.add_argument('--disable-extensions')
            chrome_options.add_argument('--disable-plugins')
            chrome_options.add_argument('--disable-images')
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
            chrome_options.add_argument('--single-process')
            chrome_options.add_argument('--disable-default-apps')
            chrome_options.add_argument('--window-size=1280,720')
            chrome_options.add_argument('--start-maximized')
            chrome_options.add_argument('--max_old_space_size=2048')
            chrome_options.add_argument('--memory-pressure-off')
            chrome_options.add_argument('--disable-logging')
            chrome_options.add_argument('--log-level=3')
            chrome_options.add_argument('--silent')
            chrome_options.add_argument(
                '--user-agent=Mozilla/5.0 (X11; Linux x86_64) '
                'AppleWebKit/537.36 (KHTML, like Gecko) '
                'Chrome/120.0.0.0 Safari/537.36'
            )

            try:
                self.driver = webdriver.Chrome(desired_capabilities=caps, options=chrome_options)
            except Exception:
                basic_opts = Options()
                basic_opts.add_argument('--headless')
                basic_opts.add_argument('--no-sandbox')
                basic_opts.add_argument('--disable-dev-shm-usage')
                self.driver = webdriver.Chrome(options=basic_opts)

            self.driver.set_page_load_timeout(60)
            self.driver.implicitly_wait(15)
            logger.info("Chrome WebDriver initialized")
            return True
        except WebDriverException as e:
            logger.error(f"Chrome init failed: {e}")
            return False

    def process_content(self, content):
        """
        Submit content to chunk.dejan.ai and wait for valid JSON in the copy-button.
        """
        max_retries = 2
        for attempt in range(max_retries):
            if not self.driver and not self.setup_driver():
                return False, None, "Browser init failed"
            try:
                logger.info(f"Attempt {attempt+1}/{max_retries}: navigating to chunk.dejan.ai")
                self.driver.get("https://chunk.dejan.ai/")
                time.sleep(8)
                wait = WebDriverWait(self.driver, 45)

                # 1) locate and fill text area
                textarea = None
                for by, sel in [
                    (By.ID, "text_area_1"),
                    (By.CSS_SELECTOR, 'textarea[aria-label="Text to chunk:"]'),
                    (By.CSS_SELECTOR, 'textarea'),
                ]:
                    try:
                        textarea = wait.until(EC.presence_of_element_located((by, sel)))
                        break
                    except TimeoutException:
                        pass
                if not textarea:
                    raise TimeoutException("Input textarea not found")
                textarea.clear()
                time.sleep(1)
                textarea.send_keys(content[:3000])
                time.sleep(2)

                # 2) click generate button
                submit_btn = None
                for by, sel in [
                    (By.CSS_SELECTOR, '[data-testid="stBaseButton-secondary"]'),
                    (By.XPATH, "//button[contains(text(), 'Generate')]")
                ]:
                    try:
                        submit_btn = wait.until(EC.element_to_be_clickable((by, sel)))
                        break
                    except TimeoutException:
                        pass
                if not submit_btn:
                    raise TimeoutException("Submit button not found")
                submit_btn.click()

                # 3) wait for JSON readiness
                locator = (By.CSS_SELECTOR, '[data-testid="stCodeCopyButton"]')
                def json_ready(driver):
                    try:
                        btn = driver.find_element(*locator)
                        txt = btn.get_attribute('data-clipboard-text') or ''
                        txt = txt.strip()
                        if txt.startswith('{') and txt.endswith('}'):
                            json.loads(txt)
                            return True
                    except Exception:
                        pass
                    return False

                logger.info("Waiting for valid JSON on copy-button…")
                WebDriverWait(self.driver, 180, poll_frequency=1).until(json_ready)
                logger.info("Valid JSON detected!")

                # 4) extract JSON
                btn = self.driver.find_element(*locator)
                json_output = btn.get_attribute('data-clipboard-text')
                try:
                    json.loads(json_output)
                    return True, json_output, None
                except json.JSONDecodeError:
                    return False, None, "Invalid JSON after wait"

            except Exception as e:
                logger.warning(f"Attempt {attempt+1} failed: {e}")
                if attempt == max_retries - 1:
                    return False, None, str(e)
                self.cleanup()
                time.sleep(5)

        return False, None, "All retry attempts failed"

    def cleanup(self):
        """
        Clean up browser resources.
        """
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass

# URL validation
def validate_url(url):
    try:
        parsed = urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            return False, "Invalid URL format. Include http:// or https://"
        if parsed.scheme not in ['http', 'https']:
            return False, "URL must use http:// or https://"
        return True, None
    except Exception as e:
        return False, f"Invalid URL: {e}"
