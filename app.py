#!/usr/bin/env python3
"""
Pure Logic Test Script - No UI

Tests the core content extraction and chunk processing logic
without Streamlit interface. Run with: python test_logic.py
"""

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
import sys

class ContentExtractor:
    """Extract content using the same logic as the main app"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
    
    def extract_content(self, url):
        """Extract structured content from a webpage"""
        try:
            print(f"🔍 Fetching content from: {url}")
            time.sleep(1)  # Rate limiting
            
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            content_parts = []
            
            # Find main content container
            main_container = self._find_main_container(soup)
            print(f"📦 Found main container: {main_container.name if main_container else 'None'}")
            
            # Extract H1 elements
            h1_elements = soup.find_all('h1')
            print(f"🎯 Found {len(h1_elements)} H1 elements")
            for h1 in h1_elements:
                text = self._get_clean_text(h1)
                if text:
                    content_parts.append(f'H1: {text}')
                    print(f"  - H1: {text[:100]}...")
            
            # Extract subtitles
            subtitle_selectors = ['.sub-title', '.subtitle', '[class*="sub-title"]', '[class*="subtitle"]']
            subtitle_count = 0
            for selector in subtitle_selectors:
                subtitles = soup.select(selector)
                for subtitle in subtitles:
                    if ('d-block' in subtitle.get('class', []) or subtitle.find_parent(class_='d-block')):
                        text = self._get_clean_text(subtitle)
                        if text:
                            content_parts.append(f'SUBTITLE: {text}')
                            subtitle_count += 1
            print(f"📝 Found {subtitle_count} subtitles")
            
            # Extract lead paragraphs
            lead_selectors = ['.lead', '[class*="lead"]']
            lead_count = 0
            for selector in lead_selectors:
                leads = soup.select(selector)
                for lead in leads:
                    text = self._get_clean_text(lead)
                    if text:
                        content_parts.append(f'LEAD: {text}')
                        lead_count += 1
            print(f"📄 Found {lead_count} lead paragraphs")
            
            # Extract main content
            if main_container:
                main_text = self._get_clean_text(main_container)
                if main_text:
                    content_parts.append(f'CONTENT: {main_text}')
                    print(f"📚 Main content: {len(main_text)} characters")
            
            final_content = '\n\n'.join(content_parts) if content_parts else 'No content found'
            
            print(f"✅ Total extracted content: {len(final_content)} characters")
            return True, final_content, None
            
        except Exception as e:
            print(f"❌ Content extraction failed: {e}")
            return False, None, str(e)
    
    def _find_main_container(self, soup):
        """Find main content container with fallback logic"""
        primary_selectors = ['article', 'main', '.content', '#content', '[role="main"]']
        
        for selector in primary_selectors:
            container = soup.select_one(selector)
            if container:
                return container
        
        # Fallback: paragraph clusters
        paragraphs = soup.find_all('p')
        if len(paragraphs) > 3:
            return paragraphs[0].parent
        
        return soup.find('body')
    
    def _get_clean_text(self, element):
        """Extract and clean text from element"""
        if not element:
            return ''
        text = element.get_text(separator=' ', strip=True)
        return ' '.join(text.split())

class ChunkProcessor:
    """Process content through chunk.dejan.ai"""
    
    def __init__(self):
        self.driver = None
    
    def setup_driver(self):
        """Initialize Chrome WebDriver with Colab-optimized settings"""
        try:
            print("🤖 Setting up Chrome WebDriver...")
            chrome_options = Options()
            chrome_options.add_argument('--headless')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--disable-extensions')
            chrome_options.add_argument('--disable-plugins')
            chrome_options.add_argument('--disable-images')  # Faster loading
            chrome_options.add_argument('--disable-javascript')  # May help with Streamlit sites
            chrome_options.add_argument('--window-size=1920,1080')
            chrome_options.add_argument('--remote-debugging-port=9222')
            chrome_options.add_argument('--disable-background-timer-throttling')
            chrome_options.add_argument('--disable-backgrounding-occluded-windows')
            chrome_options.add_argument('--disable-renderer-backgrounding')
            
            # Set timeouts
            chrome_options.add_argument('--timeout=60000')
            chrome_options.add_argument('--page-load-strategy=eager')
            
            self.driver = webdriver.Chrome(options=chrome_options)
            
            # Set longer timeouts for Colab
            self.driver.set_page_load_timeout(60)
            self.driver.implicitly_wait(15)
            
            print("✅ Chrome WebDriver initialized with Colab optimizations")
            return True
            
        except Exception as e:
            print(f"❌ Failed to initialize Chrome driver: {e}")
            return False
    
    def process_content(self, content):
        """Submit content to chunk.dejan.ai and get JSON with better error handling"""
        if not self.driver and not self.setup_driver():
            return False, None, "Failed to initialize browser"
        
        try:
            print("🔗 Navigating to chunk.dejan.ai...")
            self.driver.get("https://chunk.dejan.ai/")
            
            # Wait longer for Streamlit app to load
            print("⏳ Waiting for Streamlit app to fully load...")
            time.sleep(10)  # Give Streamlit time to initialize
            
            wait = WebDriverWait(self.driver, 60)  # Increased timeout
            
            print("📝 Finding input field...")
            try:
                input_element = wait.until(
                    EC.presence_of_element_located((By.ID, "text_area_1"))
                )
                print("✅ Input field found!")
            except TimeoutException:
                print("❌ Could not find input field. Page might not have loaded properly.")
                # Debug: Get page source
                print("🔍 Page title:", self.driver.title)
                return False, None, "Input field not found - Streamlit app may not have loaded"
            
            print("🧹 Clearing and inputting content...")
            input_element.clear()
            time.sleep(2)  # Give time for clearing
            input_element.send_keys(content[:1000])  # Limit content size for testing
            time.sleep(2)  # Give time for input
            
            print("🚀 Finding and clicking submit button...")
            try:
                submit_button = wait.until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, '[data-testid="stBaseButton-secondary"]'))
                )
                submit_button.click()
                print("✅ Submit button clicked!")
            except TimeoutException:
                print("❌ Could not find or click submit button")
                return False, None, "Submit button not found or not clickable"
            
            print("⏳ Waiting for processing to complete...")
            print("   (This may take 30-60 seconds for Streamlit to process)")
            
            try:
                copy_button = wait.until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, '[data-testid="stCodeCopyButton"]'))
                )
                print("✅ Copy button appeared - processing complete!")
            except TimeoutException:
                print("❌ Timeout waiting for results. Processing may have failed.")
                # Try to get any error messages from the page
                try:
                    error_elements = self.driver.find_elements(By.CSS_SELECTOR, '[data-testid="stAlert"]')
                    if error_elements:
                        print(f"🔍 Found error on page: {error_elements[0].text}")
                except:
                    pass
                return False, None, "Timeout waiting for chunk processing to complete"
            
            print("📊 Extracting JSON output...")
            json_output = copy_button.get_attribute('data-clipboard-text')
            
            if json_output:
                # Validate JSON
                try:
                    json.loads(json_output)
                    print("✅ Valid JSON received!")
                    return True, json_output, None
                except json.JSONDecodeError as e:
                    print(f"❌ Invalid JSON format: {e}")
                    return False, None, f"Invalid JSON received: {e}"
            else:
                print("❌ No JSON data found in copy button")
                return False, None, "No JSON output found in copy button"
                
        except TimeoutException as e:
            return False, None, f"Timeout error: {e}"
        except Exception as e:
            return False, None, f"Processing error: {e}"
    
    def cleanup(self):
        """Clean up browser"""
        if self.driver:
            try:
                self.driver.quit()
                print("🧹 Browser cleaned up")
            except:
                pass

def test_full_workflow(url):
    """Test the complete workflow"""
    print(f"{'='*60}")
    print(f"🧪 TESTING FULL WORKFLOW")
    print(f"{'='*60}")
    
    extractor = ContentExtractor()
    processor = ChunkProcessor()
    
    try:
        # Step 1: Extract content
        print(f"\n📥 STEP 1: CONTENT EXTRACTION")
        print(f"-" * 40)
        success, content, error = extractor.extract_content(url)
        
        if not success:
            print(f"❌ FAILED: {error}")
            return False
        
        if len(content) < 50:
            print(f"⚠️  WARNING: Very short content ({len(content)} chars)")
        
        print(f"\n📝 EXTRACTED CONTENT PREVIEW:")
        print(f"-" * 40)
        print(content[:500] + "..." if len(content) > 500 else content)
        
        # Step 2: Process through chunk.dejan.ai
        print(f"\n🔄 STEP 2: CHUNK PROCESSING")
        print(f"-" * 40)
        success, json_output, error = processor.process_content(content)
        
        if not success:
            print(f"❌ FAILED: {error}")
            return False
        
        # Step 3: Analyze results
        print(f"\n📊 STEP 3: RESULTS ANALYSIS")
        print(f"-" * 40)
        
        try:
            parsed_json = json.loads(json_output)
            
            if 'big_chunks' in parsed_json:
                big_chunks = parsed_json['big_chunks']
                total_small_chunks = sum(len(chunk.get('small_chunks', [])) for chunk in big_chunks)
                
                print(f"✅ SUCCESS!")
                print(f"📈 Big chunks: {len(big_chunks)}")
                print(f"📈 Small chunks: {total_small_chunks}")
                print(f"📈 Input length: {len(content)} chars")
                print(f"📈 Output length: {len(json_output)} chars")
                
                print(f"\n🎯 SAMPLE OUTPUT:")
                print(f"-" * 40)
                print(json.dumps(parsed_json, indent=2)[:800] + "...")
                
                return True
            else:
                print(f"⚠️  Unexpected JSON structure: {list(parsed_json.keys())}")
                return False
                
        except json.JSONDecodeError as e:
            print(f"❌ Invalid JSON received: {e}")
            return False
        
    except Exception as e:
        print(f"❌ UNEXPECTED ERROR: {e}")
        return False
    
    finally:
        processor.cleanup()

def main():
    """Main test function"""
    print("🧪 CONTENT PROCESSOR LOGIC TEST")
    print("=" * 60)
    
    # Get URL from command line or use default
    if len(sys.argv) > 1:
        test_url = sys.argv[1]
    else:
        test_url = input("Enter URL to test (or press Enter for example): ").strip()
        if not test_url:
            test_url = "https://example.com"  # Replace with a real article URL for testing
    
    print(f"🎯 Testing URL: {test_url}")
    
    # Validate URL format
    if not test_url.startswith(('http://', 'https://')):
        print("❌ Invalid URL format. Must start with http:// or https://")
        return
    
    # Run the test
    success = test_full_workflow(test_url)
    
    print(f"\n{'='*60}")
    if success:
        print("🎉 ALL TESTS PASSED! Logic is working correctly.")
        print("✅ Ready for Streamlit deployment.")
    else:
        print("❌ TESTS FAILED! Check errors above.")
        print("🔧 Fix issues before deploying.")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()
