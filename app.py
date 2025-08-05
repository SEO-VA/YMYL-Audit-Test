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
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
import json
import time
import logging
from urllib.parse import urlparse

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
            parts = []
            main = self._find_main_container_exact(soup)
            for h1 in soup.find_all('h1'):
                t = self._get_inner_text(h1)
                if t.strip(): parts.append(f'H1: {t.strip()}')
            for sub in soup.select('.sub-title,.subtitle,[class*="sub-title"],[class*="subtitle"]'):
                cls = ' '.join(sub.get('class', []))
                if 'd-block' in cls or sub.find_parent(class_='d-block'):
                    t = self._get_inner_text(sub)
                    if t.strip(): parts.append(f'SUBTITLE: {t.strip()}')
            for lead in soup.select('.lead,[class*="lead"]'):
                t = self._get_inner_text(lead)
                if t.strip(): parts.append(f'LEAD: {t.strip()}')
            if main:
                mt = self._get_inner_text(main)
                if mt.strip(): parts.append(f'CONTENT: {mt.strip()}')
            content = '\n\n'.join(parts) if parts else 'No content found'
            return True, content, None
        except Exception as e:
            return False, None, str(e)
    def _find_main_container_exact(self, soup):
        for sel in ['article','main','.content','#content','[role="main"]']:
            el = soup.select_one(sel)
            if el: return el
        ps = soup.find_all('p')
        if len(ps)>3: return ps[0].parent
        return soup.find('body')
    def _get_inner_text(self, el):
        if not el: return ''
        try:
            txt = el.get_text(separator='\n',strip=True)
            lines = [l.strip() for l in txt.split('\n') if l.strip()]
            return '\n'.join(lines)
        except:
            return el.get_text(strip=True)

class ChunkProcessor:
    """
    Handles interaction with chunk.dejan.ai using Selenium and network-based JSON detection.
    """
    def __init__(self):
        self.driver = None
        self.setup_driver()

    def setup_driver(self):
        try:
            caps = DesiredCapabilities.CHROME.copy()
            caps['goog:loggingPrefs'] = {'performance':'ALL'}
            options = Options()
            options.add_argument('--headless=new')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-gpu')
            options.add_argument('--window-size=1280,720')
            self.driver = webdriver.Chrome(desired_capabilities=caps, options=options)
            self.driver.set_page_load_timeout(60)
            self.driver.implicitly_wait(15)
            logger.info('WebDriver initialized with performance logging')
            return True
        except Exception as e:
            logger.error(f'Driver init failed: {e}')
            return False

    def process_content(self, content):
        max_retries = 2
        for attempt in range(max_retries):
            if not self.driver and not self.setup_driver():
                return False, None, 'Browser init failed'
            try:
                logger.info(f'Attempt {attempt+1}/{max_retries}: navigating to chunk.dejan.ai')
                self.driver.get('https://chunk.dejan.ai/')
                time.sleep(8)
                wait = WebDriverWait(self.driver, 45)

                # fill input
                inp = None
                for by,sel in [(By.ID,'text_area_1'),(By.CSS_SELECTOR,'textarea')]:
                    try: inp = wait.until(EC.presence_of_element_located((by,sel))); break
                    except: pass
                if not inp: raise TimeoutException('Input not found')
                inp.clear(); time.sleep(1); inp.send_keys(content[:3000]); time.sleep(2)

                # click generate
                btn = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR,'[data-testid="stBaseButton-secondary"]')))
                btn.click()

                # wait for network response
                logger.info('Waiting for network response...')
                def network_ready(driver):
                    for entry in driver.get_log('performance'):
                        msg = json.loads(entry['message'])['message']
                        if msg.get('method')=='Network.responseReceived':
                            r = msg['params']['response']
                            if 'chunk.dejan.ai' in r.get('url','') and r.get('status')==200:
                                return True
                    return False
                WebDriverWait(self.driver,180,1).until(network_ready)
                logger.info('Network response received')

                # extract JSON
                copy_btn = self.driver.find_element(By.CSS_SELECTOR,'[data-testid="stCodeCopyButton"]')
                json_text = copy_btn.get_attribute('data-clipboard-text')
                try: json.loads(json_text); return True,json_text,None
                except: return False,None,'Invalid JSON'

            except Exception as e:
                logger.warning(f'Attempt {attempt+1} failed: {e}')
                if attempt==max_retries-1: return False,None,str(e)
                self.cleanup(); time.sleep(5)
        return False,None,'All attempts failed'

    def cleanup(self):
        if self.driver:
            try: self.driver.quit()
            except: pass

# URL validation
def validate_url(url):
    try:
        p=urlparse(url)
        if not p.scheme or not p.netloc: return False,'Invalid URL'
        return True,None
    except: return False,'Parse error'

# The rest of the Streamlit UI remains unchanged
# ...
