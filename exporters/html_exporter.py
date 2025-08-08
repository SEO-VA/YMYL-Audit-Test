#!/usr/bin/env python3
"""
HTML Exporter for YMYL Audit Tool

Converts markdown reports to styled HTML documents with professional formatting.
"""

import markdown
import re
from typing import Optional
from utils.logging_utils import setup_logger

logger = setup_logger(__name__)


class HTMLExporter:
    """
    Converts markdown reports to professionally styled HTML documents.
    
    Features:
    - Responsive design
    - Professional color scheme
    - Enhanced severity indicators
    - Print-friendly styling
    - Accessibility considerations
    """
    
    def __init__(self):
        """Initialize the HTML exporter."""
        self.css_style = self._get_css_styles()
        logger.info("HTMLExporter initialized")

    def convert(self, markdown_content: str, title: str = "YMYL Compliance Audit Report") -> bytes:
        """
        Convert markdown content to styled HTML.
        
        Args:
            markdown_content (str): Markdown content to convert
            title (str): Document title
            
        Returns:
            bytes: UTF-8 encoded HTML document
        """
        try:
            logger.info(f"Converting markdown to HTML ({len(markdown_content):,} characters)")
            
            # Convert markdown to HTML
            html_content = markdown.markdown(
                markdown_content, 
                extensions=['tables', 'toc', 'codehilite', 'fenced_code']
            )
            
            # Enhance the HTML with styling and structure
            enhanced_html = self._enhance_html_content(html_content)
            
            # Create complete HTML document
            full_html = self._create_complete_document(enhanced_html, title)
            
            logger.info(f"HTML conversion successful ({len(full_html):,} characters)")
            return full_html.encode('utf-8')
            
        except Exception as e:
            logger.error(f"HTML conversion error: {e}")
            return self._create_error_document(str(e)).encode('utf-8')

    def _enhance_html_content(self, html_content: str) -> str:
        """
        Enhance HTML content with styling and structure.
        
        Args:
            html_content (str): Base HTML content
            
        Returns:
            str: Enhanced HTML content
        """
        # Enhance severity indicators with CSS classes
        html_content = html_content.replace('🔴', '<span class="severity-critical">🔴 Critical</span>')
        html_content = html_content.replace('🟠', '<span class="severity-high">🟠 High</span>')
        html_content = html_content.replace('🟡', '<span class="severity-medium">🟡 Medium</span>')
        html_content = html_content.replace('🔵', '<span class="severity-low">🔵 Low</span>')
        
        # Enhance other indicators
        html_content = html_content.replace('✅', '<span class="success-indicator">✅</span>')
        html_content = html_content.replace('❌', '<span class="error-indicator">❌</span>')
        html_content = html_content.replace('⚠️', '<span class="warning-indicator">⚠️</span>')
        
        # Wrap processing summary in special container
        html_content = re.sub(
            r'<h2>Processing Summary</h2>(.*?)(?=<h2>|$)', 
            r'<div class="processing-summary"><h2>Processing Summary</h2>\1</div>', 
            html_content, 
            flags=re.DOTALL
        )
        
        # Add anchor links to headers
        html_content = self._add_anchor_links(html_content)
        
        return html_content

    def _add_anchor_links(self, html_content: str) -> str:
        """
        Add anchor links to headers for navigation.
        
        Args:
            html_content (str): HTML content
            
        Returns:
            str: HTML with anchor links
        """
        def replace_header(match):
            tag = match.group(1)
            content = match.group(2)
            # Create anchor ID from content
            anchor_id = re.sub(r'[^\w\s-]', '', content).strip()
            anchor_id = re.sub(r'[-\s]+', '-', anchor_id).lower()
            return f'<{tag} id="{anchor_id}">{content}</{tag}>'
        
        # Add IDs to h1-h6 tags
        html_content = re.sub(r'<(h[1-6])>([^<]+)</h[1-6]>', replace_header, html_content)
        
        return html_content

    def _get_css_styles(self) -> str:
        """
        Get CSS styles for the HTML document.
        
        Returns:
            str: CSS styles
        """
        return """
        <style>
        /* Base Styles */
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            color: #333;
            background-color: #ffffff;
        }
        
        /* Typography */
        h1 {
            color: #2c3e50;
            border-bottom: 3px solid #3498db;
            padding-bottom: 10px;
            margin-bottom: 30px;
            font-size: 2.5em;
            font-weight: 700;
        }
        
        h2 {
            color: #34495e;
            border-left: 4px solid #3498db;
            padding-left: 15px;
            margin-top: 30px;
            margin-bottom: 15px;
            font-size: 1.8em;
            font-weight: 600;
        }
        
        h3 {
            color: #34495e;
            margin-top: 25px;
            margin-bottom: 10px;
            font-size: 1.4em;
            font-weight: 500;
        }
        
        h4, h5, h6 {
            color: #34495e;
            margin-top: 20px;
            margin-bottom: 8px;
            font-weight: 500;
        }
        
        p {
            margin-bottom: 15px;
            text-align: justify;
        }
        
        /* Severity Indicators */
        .severity-critical { 
            color: #e74c3c; 
            font-weight: bold; 
            background-color: #fadbd8;
            padding: 3px 8px;
            border-radius: 4px;
            border-left: 4px solid #e74c3c;
        }
        
        .severity-high { 
            color: #e67e22; 
            font-weight: bold;
            background-color: #fdeaa7;
            padding: 3px 8px;
            border-radius: 4px;
            border-left: 4px solid #e67e22;
        }
        
        .severity-medium { 
            color: #f39c12; 
            font-weight: bold;
            background-color: #fcf3cf;
            padding: 3px 8px;
            border-radius: 4px;
            border-left: 4px solid #f39c12;
        }
        
        .severity-low { 
            color: #3498db; 
            font-weight: bold;
            background-color: #d6eaf8;
            padding: 3px 8px;
            border-radius: 4px;
            border-left: 4px solid #3498db;
        }
        
        /* Status Indicators */
        .success-indicator {
            color: #27ae60;
            font-weight: bold;
        }
        
        .error-indicator {
            color: #e74c3c;
            font-weight: bold;
        }
        
        .warning-indicator {
            color: #f39c12;
            font-weight: bold;
        }
        
        /* Tables */
        table {
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
            background-color: #ffffff;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        
        th, td {
            padding: 12px 15px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }
        
        th {
            background-color: #f8f9fa;
            font-weight: bold;
            color: #2c3e50;
            border-bottom: 2px solid #3498db;
        }
        
        tr:nth-child(even) {
            background-color: #f9f9f9;
        }
        
        tr:hover {
            background-color: #f1f1f1;
        }
        
        /* Processing Summary */
        .processing-summary {
            background-color: #f8f9fa;
            padding: 20px;
            border-radius: 8px;
            margin: 30px 0;
            border: 1px solid #e9ecef;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        }
        
        .processing-summary h2 {
            color: #2c3e50;
            margin-top: 0;
            border-left: 4px solid #27ae60;
        }
        
        /* Code Blocks */
        code {
            background-color: #f1f2f6;
            padding: 2px 6px;
            border-radius: 3px;
            font-family: 'Courier New', monospace;
            font-size: 0.9em;
            color: #2c3e50;
        }
        
        pre {
            background-color: #2c3e50;
            color: #ecf0f1;
            padding: 15px;
            border-radius: 5px;
            overflow-x: auto;
            margin: 15px 0;
        }
        
        pre code {
            background-color: transparent;
            color: #ecf0f1;
            padding: 0;
        }
        
        /* Blockquotes */
        blockquote {
            border-left: 4px solid #bdc3c7;
            margin: 15px 0;
            padding-left: 15px;
            color: #7f8c8d;
            font-style: italic;
        }
        
        /* Lists */
        ul, ol {
            margin-bottom: 15px;
            padding-left: 30px;
        }
        
        li {
            margin-bottom: 5px;
        }
        
        /* Links */
        a {
            color: #3498db;
            text-decoration: none;
            border-bottom: 1px dotted #3498db;
        }
        
        a:hover {
            color: #2980b9;
            border-bottom: 1px solid #2980b9;
        }
        
        /* Horizontal Rules */
        hr {
            border: none;
            height: 2px;
            background: linear-gradient(to right, #3498db, transparent);
            margin: 30px 0;
        }
        
        /* Print Styles */
        @media print {
            body {
                max-width: none;
                margin: 0;
                padding: 15px;
                font-size: 12pt;
                line-height: 1.4;
            }
            
            h1 {
                font-size: 18pt;
                page-break-after: avoid;
            }
            
            h2 {
                font-size: 16pt;
                page-break-after: avoid;
            }
            
            h3 {
                font-size: 14pt;
                page-break-after: avoid;
            }
            
            .processing-summary {
                page-break-inside: avoid;
            }
            
            table {
                page-break-inside: auto;
            }
            
            tr {
                page-break-inside: avoid;
                page-break-after: auto;
            }
        }
        
        /* Responsive Design */
        @media (max-width: 768px) {
            body {
                padding: 10px;
            }
            
            h1 {
                font-size: 2em;
            }
            
            h2 {
                font-size: 1.5em;
            }
            
            table {
                font-size: 0.9em;
            }
            
            th, td {
                padding: 8px 10px;
            }
        }
        
        /* Accessibility */
        @media (prefers-reduced-motion: reduce) {
            * {
                animation-duration: 0.01ms !important;
                animation-iteration-count: 1 !important;
                transition-duration: 0.01ms !important;
            }
        }
        
        /* Focus styles for accessibility */
        *:focus {
            outline: 2px solid #3498db;
            outline-offset: 2px;
        }
        </style>
        """

    def _create_complete_document(self, html_content: str, title: str) -> str:
        """
        Create complete HTML document with metadata.
        
        Args:
            html_content (str): Body content
            title (str): Document title
            
        Returns:
            str: Complete HTML document
        """
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="description" content="YMYL Compliance Audit Report generated by AI-powered analysis system">
    <meta name="author" content="YMYL Audit Tool">
    <meta name="robots" content="noindex, nofollow">
    <title>{title}</title>
    {self.css_style}
</head>
<body>
    <main>
        {html_content}
    </main>
    
    <footer style="margin-top: 50px; padding: 20px 0; border-top: 1px solid #ddd; text-align: center; color: #7f8c8d; font-size: 0.9em;">
        <p>Generated by YMYL Audit Tool - AI-powered compliance analysis system</p>
        <p>Report generated on {self._get_current_timestamp()}</p>
    </footer>
</body>
</html>"""

    def _create_error_document(self, error_message: str) -> str:
        """
        Create error HTML document.
        
        Args:
            error_message (str): Error description
            
        Returns:
            str: Error HTML document
        """
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Export Error - YMYL Audit Tool</title>
    <style>
        body {{ font-family: Arial, sans-serif; max-width: 800px; margin: 50px auto; padding: 20px; }}
        .error {{ background-color: #fadbd8; border: 1px solid #e74c3c; border-radius: 5px; padding: 20px; }}
        .error h1 {{ color: #e74c3c; margin-top: 0; }}
    </style>
</head>
<body>
    <div class="error">
        <h1>Export Error</h1>
        <p><strong>Failed to convert report:</strong> {error_message}</p>
        <p>Please try again or contact support if the problem persists.</p>
    </div>
</body>
</html>"""

    def _get_current_timestamp(self) -> str:
        """Get current timestamp for footer."""
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")

    def validate_markdown(self, markdown_content: str) -> bool:
        """
        Validate markdown content before conversion.
        
        Args:
            markdown_content (str): Markdown to validate
            
        Returns:
            bool: True if valid, False otherwise
        """
        try:
            if not markdown_content or not markdown_content.strip():
                return False
            
            # Check for basic markdown structure
            if not any(line.startswith('#') for line in markdown_content.split('\n')):
                logger.warning("No headers found in markdown content")
            
            return True
            
        except Exception as e:
            logger.error(f"Markdown validation error: {e}")
            return False
