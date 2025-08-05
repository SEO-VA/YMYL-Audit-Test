import streamlit as st
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
import requests
from bs4 import BeautifulSoup
import time, json

# --- Content Extraction ---
def extract_content(url: str) -> str:
    response = requests.get(url, timeout=45)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, 'html.parser')
    # selector priority
    container = None
    for sel in ['article', 'main', '.content', '#content', '[role=\"main\"]']:
        el = soup.select_one(sel)
        if el:
            container = el
            break
    # fallback: paragraph clustering
    if container is None:
        paragraphs = soup.find_all('p')
        if len(paragraphs) > 3:
            container = paragraphs[0].parent
    if container is None:
        container = soup.body

    sections = []
    # H1s
    for h in container.find_all('h1'):
        text = h.get_text(strip=True)
        if text:
            sections.append(f"H1: {text}")
    # Subtitles with d-block
    for st_el in container.select('.sub-title, .subtitle, [class*=\"sub-title\"], [class*=\"subtitle\"]'):
        if 'd-block' in st_el.get('class', []) or st_el.find_parent(class_='d-block'):
            text = st_el.get_text(strip=True)
            if text:
                sections.append(f"SUBTITLE: {text}")
    # Leads
    for ld in container.select('.lead, [class*=\"lead\"]'):
        text = ld.get_text(strip=True)
        if text:
            sections.append(f"LEAD: {text}")
    # Content
    content_text = container.get_text(separator='\n', strip=True)
    if content_text:
        sections.append(f"CONTENT: {content_text}")

    return '\n\n'.join(sections) or 'No content found'

# --- Chunk Processing via Selenium ---
def process_chunks(text: str, debug: bool = False) -> dict:
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')

    driver = webdriver.Chrome(options=chrome_options)
    try:
        driver.get('https://chunk.dejan.ai/')
        textarea = WebDriverWait(driver, 45).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'textarea#text_area_1'))
        )
        textarea.clear()
        textarea.send_keys(text)
        btn = driver.find_element(By.CSS_SELECTOR, 'button[data-testid="stBaseButton-secondary"]')
        btn.click()

        # Wait for processing to truly finish
        # 1) Ensure spinner(s) have appeared and then disappeared
        if debug:
            spinners = driver.find_elements(By.CSS_SELECTOR, 'div.stSpinner')
            print(f"Found {len(spinners)} spinner(s)")
            for s in spinners:
                print(s.get_attribute('outerHTML')[:200])
        WebDriverWait(driver, 180).until(
            EC.invisibility_of_element_located((By.CSS_SELECTOR, 'div.stSpinner'))
        )

        # 2) Poll until JSON output stabilizes and parses
        def get_json_text():
            copy_btn = driver.find_element(By.CSS_SELECTOR, 'button[data-testid="stCodeCopyButton"]')
            return copy_btn.get_attribute('data-clipboard-text') or ''

        prev = ''
        for _ in range(60):
            current = get_json_text()
            if current and current == prev:
                try:
                    return json.loads(current)
                except json.JSONDecodeError:
                    pass
            prev = current
            time.sleep(1)
        raise TimeoutException("JSON never stabilized or stayed invalid after spinner disappeared.")

    finally:
        driver.quit()

# --- Streamlit App ---
def main():
    st.title("Content-to-JSON Automator")
    url = st.text_input("Enter URL to process:")
    debug = st.checkbox("Debug mode", value=False)
    if st.button("Process") and url:
        with st.spinner("Extracting content…"):
            try:
                content = extract_content(url)
            except Exception as e:
                st.error(f"Content extraction failed: {e}")
                return
        st.subheader("Extracted Content")
        st.text_area("", content, height=300)

        with st.spinner("Processing chunks…"):
            try:
                result = process_chunks(content, debug=debug)
            except Exception as e:
                st.error(f"Chunk processing failed: {e}")
                return

        st.subheader("JSON Output")
        st.code(json.dumps(result, indent=2), language='json')

if __name__ == "__main__":
    main()
