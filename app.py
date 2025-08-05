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
            time.sleep(1)
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            content_parts = []
            main_container = self._find_main_container_exact(soup)
            h1_elements = soup.find_all('h1')
            for h1 in h1_elements:
                text = self._get_inner_text(h1)
                if text.strip():
                    content_parts.append(f'H1: {text.strip()}')
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
            lead_selectors = '.lead,[class*="lead"]'
            leads = soup.select(lead_selectors)
            for lead in leads:
                text = self._get_inner_text(lead)
                if text.strip():
                    content_parts.append(f'LEAD: {text.strip()}')
            if main_container:
                main_text = self._get_inner_text(main_container) or ''
                if main_text.strip():
                    content_parts.append(f'CONTENT: {main_text.strip()}')
            final_content = '\n\n'.join(content_parts) if content_parts else 'No content found'
            return True, final_content, None
        except requests.RequestException as e:
            return False, None, f"Error fetching URL: {str(e)}"
        except Exception as e:
            return False, None, f"Error processing content: {str(e)}"
    
    def _find_main_container_exact(self, soup):
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
        if not element:
            return ''
        try:
            text = element.get_text(separator='\n', strip=True)
            lines = [line.strip() for line in text.split('\n') if line.strip()]
            return '\n'.join(lines)
        except:
            return element.get_text(strip=True)

class ChunkProcessor:
    """
    Handles interaction with chunk.dejan.ai using Selenium automation with spinner detection
    """
    
    def __init__(self):
        self.driver = None
        self.setup_driver()
    
    def setup_driver(self):
        chrome_options = Options()
        chrome_options.add_argument('--headless=new')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        try:
            self.driver = webdriver.Chrome(options=chrome_options)
        except Exception:
            basic_options = Options()
            basic_options.add_argument('--headless')
            basic_options.add_argument('--no-sandbox')
            basic_options.add_argument('--disable-dev-shm-usage')
            self.driver = webdriver.Chrome(options=basic_options)
        self.driver.set_page_load_timeout(60)
        self.driver.implicitly_wait(15)
        return True
    
    def process_content(self, content):
        max_retries = 2
        for attempt in range(max_retries):
            if not self.driver:
                self.setup_driver()
            try:
                self.driver.get("https://chunk.dejan.ai/")
                time.sleep(8)
                wait = WebDriverWait(self.driver, 45)
                selectors_to_try = [
                    (By.ID, "text_area_1"),
                    (By.CSS_SELECTOR, 'textarea[aria-label="Text to chunk:"]'),
                    (By.CSS_SELECTOR, 'textarea'),
                ]
                input_element = None
                for stype, sel in selectors_to_try:
                    try:
                        input_element = wait.until(EC.presence_of_element_located((stype, sel)))
                        break
                    except TimeoutException:
                        continue
                if not input_element:
                    raise TimeoutException("Input field not found")
                input_element.clear()
                time.sleep(2)
                input_element.send_keys(content[:3000])
                time.sleep(3)
                button_selectors = [
                    (By.CSS_SELECTOR, '[data-testid="stBaseButton-secondary"]'),
                    (By.XPATH, "//button[contains(text(), 'Generate') ]"),
                    (By.CSS_SELECTOR, 'button[kind="secondary"]'),
                ]
                submit_btn = None
                for stype, sel in button_selectors:
                    try:
                        submit_btn = wait.until(EC.element_to_be_clickable((stype, sel)))
                        break
                    except TimeoutException:
                        continue
                if not submit_btn:
                    raise TimeoutException("Submit button not found")
                submit_btn.click()
                # --- FIXED PART START ---
                # Wait for spinner to disappear
                try:
                    # Wait for spinner element to finish (using data-testid)
                    WebDriverWait(self.driver, 180).until(
                        EC.invisibility_of_element_located((By.CSS_SELECTOR, '[data-testid="stSpinner"]'))
                    )
                except TimeoutException:
                    logger.warning("Spinner did not disappear in time")
                # Poll for stable, valid JSON
                def get_json_text():
                    btn = self.driver.find_element(By.CSS_SELECTOR, 'button[data-testid="stCodeCopyButton"]')
                    return btn.get_attribute('data-clipboard-text') or ''
                prev = ''
                for _ in range(60):
                    curr = get_json_text()
                    if curr and curr == prev:
                        try:
                            return True, curr, None
                        except Exception:
                            pass
                    prev = curr
                    time.sleep(1)
                raise TimeoutException("JSON never stabilized after spinner")
                # --- FIXED PART END ---
            except TimeoutException as e:
                if attempt == max_retries - 1:
                    return False, None, f"Timeout: {e}"
                self.cleanup()
                time.sleep(5)
                continue
            except WebDriverException as e:
                if attempt == max_retries - 1:
                    return False, None, f"Browser error: {e}"
                self.cleanup()
                time.sleep(5)
                continue
        return False, None, "Failed after retries"
    
    def cleanup(self):
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass

# ... rest of the script remains unchanged ...
