#!/usr/bin/env python3
"""
Content Extractor for YMYL Audit Tool

Handles web scraping and content extraction from URLs.
Extracts structured content including headings, paragraphs, and special sections.
"""

import requests
from bs4 import BeautifulSoup
from typing import Tuple, Optional
from config.settings import REQUEST_TIMEOUT, USER_AGENT, MAX_CONTENT_LENGTH
from utils.logging_utils import setup_logger

logger = setup_logger(__name__)


class ContentExtractor:
    """
    Extracts and structures content from web pages.
    
    Handles various content types including:
    - Headings (H1-H6)
    - Paragraphs and lead text
    - Subtitles and special sections
    - FAQ sections
    - Author information
    """
    
    def __init__(self, timeout: int = REQUEST_TIMEOUT, user_agent: str = USER_AGENT):
        """
        Initialize the ContentExtractor.
        
        Args:
            timeout (int): Request timeout in seconds
            user_agent (str): User agent string for requests
        """
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': user_agent
        })
        logger.info("ContentExtractor initialized")

    def extract_content(self, url: str) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Extract structured content from a URL.
        
        Args:
            url (str): URL to extract content from
            
        Returns:
            tuple: (success: bool, content: str or None, error: str or None)
        """
        logger.info(f"Starting content extraction from: {url}")
        
        try:
            # Fetch the page
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            
            # Check content length
            content_length = len(response.content)
            if content_length > MAX_CONTENT_LENGTH:
                logger.warning(f"Content length ({content_length:,} bytes) exceeds maximum ({MAX_CONTENT_LENGTH:,} bytes)")
                return False, None, f"Content too large: {content_length:,} bytes (max: {MAX_CONTENT_LENGTH:,})"
            
            # Parse HTML
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extract structured content
            content_parts = self._extract_structured_content(soup)
            
            # Join with double newlines to preserve spacing
            final_content = '\n\n'.join(content_parts)
            
            logger.info(f"Content extraction successful: {len(final_content):,} characters extracted")
            return True, final_content, None
            
        except requests.exceptions.Timeout:
            error_msg = f"Request timeout after {self.timeout} seconds"
            logger.error(error_msg)
            return False, None, error_msg
            
        except requests.exceptions.ConnectionError:
            error_msg = "Connection error - unable to reach the website"
            logger.error(error_msg)
            return False, None, error_msg
            
        except requests.exceptions.HTTPError as e:
            error_msg = f"HTTP error: {e.response.status_code}"
            logger.error(error_msg)
            return False, None, error_msg
            
        except requests.RequestException as e:
            error_msg = f"Request error: {str(e)}"
            logger.error(error_msg)
            return False, None, error_msg
            
        except Exception as e:
            error_msg = f"Unexpected error during content extraction: {str(e)}"
            logger.error(error_msg)
            return False, None, error_msg

    def _extract_structured_content(self, soup: BeautifulSoup) -> list:
        """
        Extract structured content from BeautifulSoup object.
        
        Args:
            soup (BeautifulSoup): Parsed HTML content
            
        Returns:
            list: List of structured content parts
        """
        content_parts = []
        
        # 1. Extract H1 (anywhere on page)
        h1_content = self._extract_h1(soup)
        if h1_content:
            content_parts.append(h1_content)
        
        # 2. Extract Subtitle (anywhere on page)
        subtitle_content = self._extract_subtitle(soup)
        if subtitle_content:
            content_parts.append(subtitle_content)
        
        # 3. Extract Lead paragraph (anywhere on page)
        lead_content = self._extract_lead(soup)
        if lead_content:
            content_parts.append(lead_content)
        
        # 4. Extract Article content
        article_content = self._extract_article_content(soup)
        content_parts.extend(article_content)
        
        # 5. Extract FAQ section
        faq_content = self._extract_faq(soup)
        if faq_content:
            content_parts.append(faq_content)
        
        # 6. Extract Author section
        author_content = self._extract_author(soup)
        if author_content:
            content_parts.append(author_content)
        
        # Filter out empty parts
        content_parts = [part for part in content_parts if part and part.strip()]
        
        logger.info(f"Extracted {len(content_parts)} content sections")
        return content_parts

    def _extract_h1(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract H1 content."""
        h1 = soup.find('h1')
        if h1:
            text = h1.get_text(separator='\n', strip=True)
            if text:
                return f"H1: {text}"
        return None

    def _extract_subtitle(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract subtitle content."""
        subtitle = soup.find('span', class_=['sub-title', 'd-block'])
        if subtitle:
            text = subtitle.get_text(separator='\n', strip=True)
            if text:
                return f"SUBTITLE: {text}"
        return None

    def _extract_lead(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract lead paragraph content."""
        lead = soup.find('p', class_='lead')
        if lead:
            text = lead.get_text(separator='\n', strip=True)
            if text:
                return f"LEAD: {text}"
        return None

    def _extract_article_content(self, soup: BeautifulSoup) -> list:
        """Extract article content with proper structure."""
        content_parts = []
        article = soup.find('article')
        
        if not article:
            logger.info("No article tag found, skipping article content extraction")
            return content_parts
        
        # Remove tab-content sections before processing
        for tab_content in article.find_all('div', class_='tab-content'):
            tab_content.decompose()
        
        # Process all elements in document order within article
        for element in article.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'span', 'p']):
            text = element.get_text(separator='\n', strip=True)
            if not text:
                continue
            
            # Check element type and add appropriate prefix
            formatted_content = self._format_element_content(element, text)
            if formatted_content:
                content_parts.append(formatted_content)
        
        logger.info(f"Extracted {len(content_parts)} article elements")
        return content_parts

    def _format_element_content(self, element, text: str) -> Optional[str]:
        """Format element content with appropriate prefix."""
        tag_name = element.name.lower()
        element_classes = element.get('class', [])
        
        # Handle headings
        if tag_name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
            return f"{tag_name.upper()}: {text}"
        
        # Handle special span elements
        elif tag_name == 'span':
            if 'sub-title' in element_classes and 'd-block' in element_classes:
                return f"SUBTITLE: {text}"
            # Skip other spans that don't have special formatting
            return None
        
        # Handle special paragraph elements
        elif tag_name == 'p':
            if 'lead' in element_classes:
                return f"LEAD: {text}"
            else:
                return f"CONTENT: {text}"
        
        return None

    def _extract_faq(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract FAQ section content."""
        faq_section = soup.find('section', attrs={'data-qa': 'templateFAQ'})
        if faq_section:
            text = faq_section.get_text(separator='\n', strip=True)
            if text:
                return f"FAQ: {text}"
        return None

    def _extract_author(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract author section content."""
        author_section = soup.find('section', attrs={'data-qa': 'templateAuthorCard'})
        if author_section:
            text = author_section.get_text(separator='\n', strip=True)
            if text:
                return f"AUTHOR: {text}"
        return None

    def get_page_info(self, url: str) -> dict:
        """
        Get basic information about a webpage without full content extraction.
        
        Args:
            url (str): URL to analyze
            
        Returns:
            dict: Basic page information
        """
        try:
            response = self.session.head(url, timeout=self.timeout)
            response.raise_for_status()
            
            info = {
                'url': url,
                'status_code': response.status_code,
                'content_type': response.headers.get('content-type', 'unknown'),
                'content_length': response.headers.get('content-length'),
                'accessible': True,
                'error': None
            }
            
            # Convert content-length to int if present
            if info['content_length']:
                try:
                    info['content_length'] = int(info['content_length'])
                except ValueError:
                    info['content_length'] = None
            
            return info
            
        except Exception as e:
            return {
                'url': url,
                'status_code': None,
                'content_type': None,
                'content_length': None,
                'accessible': False,
                'error': str(e)
            }

    def cleanup(self):
        """Clean up resources."""
        if hasattr(self, 'session'):
            self.session.close()
        logger.info("ContentExtractor cleanup completed")

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit with cleanup."""
        self.cleanup()
