#!/usr/bin/env python3
"""
PDF Exporter for YMYL Audit Tool

Converts markdown reports to professional PDF documents using ReportLab.
"""

import io
import re
from datetime import datetime
from typing import Optional, List
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, 
    PageBreak, KeepTogether
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, mm
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from utils.logging_utils import setup_logger

logger = setup_logger(__name__)


class NumberedCanvas(canvas.Canvas):
    """Custom canvas class for adding page numbers and headers."""
    
    def __init__(self, *args, **kwargs):
        canvas.Canvas.__init__(self, *args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        """Add page numbers to all pages."""
        num_pages = len(self._saved_page_states)
        for (page_num, page_state) in enumerate(self._saved_page_states):
            self.__dict__.update(page_state)
            self.draw_page_number(page_num + 1, num_pages)
            canvas.Canvas.showPage(self)
        canvas.Canvas.save(self)

    def draw_page_number(self, page_num, total_pages):
        """Draw page number at bottom of page."""
        self.setFont("Helvetica", 9)
        self.setFillColor(colors.grey)
        self.drawCentredText(
            self._pagesize[0] / 2, 
            20, 
            f"YMYL Compliance Audit Report - Page {page_num} of {total_pages}"
        )


class PDFExporter:
    """
    Converts markdown reports to professionally formatted PDF documents.
    
    Features:
    - Professional layout and typography
    - Color-coded severity indicators
    - Page numbering and headers
    - Table of contents (basic)
    - Consistent spacing and formatting
    """
    
    def __init__(self):
        """Initialize the PDF exporter."""
        self.styles = None
        self._setup_styles()
        logger.info("PDFExporter initialized")

    def convert(self, markdown_content: str, title: str = "YMYL Compliance Audit Report") -> bytes:
        """
        Convert markdown content to PDF document.
        
        Args:
            markdown_content (str): Markdown content to convert
            title (str): Document title
            
        Returns:
            bytes: PDF document as bytes
        """
        try:
            logger.info(f"Converting markdown to PDF ({len(markdown_content):,} characters)")
            
            # Create buffer and document
            buffer = io.BytesIO()
            doc = SimpleDocTemplate(
                buffer, 
                pagesize=A4, 
                rightMargin=25*mm, 
                leftMargin=25*mm, 
                topMargin=25*mm, 
                bottomMargin=25*mm,
                canvasmaker=NumberedCanvas
            )
            
            # Build document content
            story = self._build_story(markdown_content, title)
            
            # Build PDF
            doc.build(story)
            buffer.seek(0)
            
            logger.info("PDF conversion successful")
            return buffer.getvalue()
            
        except Exception as e:
            logger.error(f"PDF conversion error: {e}")
            return self._create_error_pdf(str(e))

    def _setup_styles(self):
        """Set up paragraph styles for the PDF."""
        self.styles = getSampleStyleSheet()
        
        # Custom Title Style
        self.styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=self.styles['Title'],
            fontSize=24,
            textColor=colors.HexColor('#2c3e50'),
            spaceAfter=30,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        ))
        
        # Custom Heading 1 Style
        self.styles.add(ParagraphStyle(
            name='CustomHeading1',
            parent=self.styles['Heading1'],
            fontSize=18,
            textColor=colors.HexColor('#34495e'),
            spaceBefore=20,
            spaceAfter=12,
            fontName='Helvetica-Bold'
        ))
        
        # Custom Heading 2 Style
        self.styles.add(ParagraphStyle(
            name='CustomHeading2',
            parent=self.styles['Heading2'],
            fontSize=14,
            textColor=colors.HexColor('#34495e'),
            spaceBefore=16,
            spaceAfter=8,
            fontName='Helvetica-Bold'
        ))
        
        # Custom Heading 3 Style
        self.styles.add(ParagraphStyle(
            name='CustomHeading3',
            parent=self.styles['Heading3'],
            fontSize=12,
            textColor=colors.HexColor('#34495e'),
            spaceBefore=12,
            spaceAfter=6,
            fontName='Helvetica-Bold'
        ))
        
        # Severity Styles
        self.styles.add(ParagraphStyle(
            name='Critical',
            parent=self.styles['Normal'],
            textColor=colors.HexColor('#e74c3c'),
            fontSize=10,
            fontName='Helvetica-Bold',
            leftIndent=10,
            spaceBefore=3,
            spaceAfter=3
        ))
        
        self.styles.add(ParagraphStyle(
            name='High',
            parent=self.styles['Normal'],
            textColor=colors.HexColor('#e67e22'),
            fontSize=10,
            fontName='Helvetica-Bold',
            leftIndent=10,
            spaceBefore=3,
            spaceAfter=3
        ))
        
        self.styles.add(ParagraphStyle(
            name='Medium',
            parent=self.styles['Normal'],
            textColor=colors.HexColor('#f39c12'),
            fontSize=10,
            fontName='Helvetica-Bold',
            leftIndent=10,
            spaceBefore=3,
            spaceAfter=3
        ))
        
        self.styles.add(ParagraphStyle(
            name='Low',
            parent=self.styles['Normal'],
            textColor=colors.HexColor('#3498db'),
            fontSize=10,
            fontName='Helvetica-Bold',
            leftIndent=10,
            spaceBefore=3,
            spaceAfter=3
        ))
        
        # Processing Summary Style
        self.styles.add(ParagraphStyle(
            name='ProcessingSummary',
            parent=self.styles['Normal'],
            fontSize=9,
            textColor=colors.HexColor('#7f8c8d'),
            leftIndent=15,
            rightIndent=15,
            spaceBefore=6,
            spaceAfter=6,
            alignment=TA_LEFT
        ))
        
    if 'Code' not in self.styles.byName:
        self.styles.add(ParagraphStyle(
            name='Code',
            parent=self.styles['Normal'],
            fontName='Courier',
            fontSize=9,
            textColor=colors.HexColor('#2c3e50'),
            backColor=colors.HexColor('#f8f9fa'),
            leftIndent=20,
            rightIndent=20,
            spaceBefore=6,
            spaceAfter=6
        ))
        
    def _build_story(self, markdown_content: str, title: str) -> List:
        """
        Build the story (content) for the PDF document.
        
        Args:
            markdown_content (str): Markdown content
            title (str): Document title
            
        Returns:
            list: Story elements for ReportLab
        """
        story = []
        lines = markdown_content.split('\n')
        in_processing_summary = False
        
        # Add document title
        story.append(Paragraph(title, self.styles['CustomTitle']))
        story.append(Spacer(1, 12))
        
        # Add generation timestamp
        timestamp = datetime.now().strftime("%B %d, %Y at %H:%M UTC")
        story.append(Paragraph(f"Generated on {timestamp}", self.styles['ProcessingSummary']))
        story.append(Spacer(1, 20))
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Track processing summary section
            if line.startswith('## Processing Summary'):
                in_processing_summary = True
                story.append(Spacer(1, 12))
                # Add a subtle background box for processing summary
                story.append(Paragraph(line[3:], self.styles['CustomHeading2']))
                continue
            elif line.startswith('##') and in_processing_summary:
                in_processing_summary = False
            
            # Parse different markdown elements
            element = self._parse_line(line, in_processing_summary)
            if element:
                story.append(element)
        
        # Add final spacing
        story.append(Spacer(1, 20))
        
        return story

    def _parse_line(self, line: str, in_processing_summary: bool = False):
        """
        Parse a single line of markdown and return appropriate element.
        
        Args:
            line (str): Line to parse
            in_processing_summary (bool): Whether we're in processing summary section
            
        Returns:
            Flowable or None: ReportLab flowable element
        """
        # Handle different markdown elements
        if line.startswith('# '):
            # Main heading (skip if it's the title)
            if not line[2:].lower().startswith('ymyl compliance'):
                return Paragraph(line[2:], self.styles['CustomHeading1'])
            return None
            
        elif line.startswith('## '):
            return Paragraph(line[3:], self.styles['CustomHeading2'])
            
        elif line.startswith('### '):
            return Paragraph(line[4:], self.styles['CustomHeading3'])
            
        elif line.startswith('**') and line.endswith('**'):
            # Bold text
            text = f"<b>{line[2:-2]}</b>"
            style = self.styles['ProcessingSummary'] if in_processing_summary else self.styles['Normal']
            return Paragraph(text, style)
            
        elif line.startswith('---'):
            # Horizontal rule
            return Spacer(1, 12)
            
        elif line.startswith('- ') or line.startswith('* '):
            # Bullet points
            text = f"• {line[2:]}"
            style = self.styles['ProcessingSummary'] if in_processing_summary else self.styles['Normal']
            return Paragraph(text, style)
            
        elif self._contains_severity_indicator(line):
            # Severity indicators
            style_name = self._get_severity_style(line)
            if style_name:
                # Clean up the line for better PDF display
                clean_line = self._clean_severity_line(line)
                return Paragraph(clean_line, self.styles[style_name])
            return Paragraph(line, self.styles['Normal'])
            
        else:
            # Regular paragraph
            if line:
                style = self.styles['ProcessingSummary'] if in_processing_summary else self.styles['Normal']
                # Handle code blocks
                if line.startswith('```') or line.startswith('    '):
                    return Paragraph(line, self.styles['Code'])
                return Paragraph(line, style)
        
        return None

    def _contains_severity_indicator(self, line: str) -> bool:
        """Check if line contains severity indicators."""
        return any(indicator in line for indicator in ['🔴', '🟠', '🟡', '🔵', '✅', '❌'])

    def _get_severity_style(self, line: str) -> Optional[str]:
        """Get appropriate style for severity line."""
        if '🔴' in line:
            return 'Critical'
        elif '🟠' in line:
            return 'High'
        elif '🟡' in line:
            return 'Medium'
        elif '🔵' in line:
            return 'Low'
        return None

    def _clean_severity_line(self, line: str) -> str:
        """Clean up severity line for better PDF display."""
        # Replace emoji with text labels for better PDF compatibility
        replacements = {
            '🔴': '● CRITICAL:',
            '🟠': '● HIGH:',
            '🟡': '● MEDIUM:',
            '🔵': '● LOW:',
            '✅': '✓',
            '❌': '✗',
            '⚠️': '⚠'
        }
        
        clean_line = line
        for emoji, replacement in replacements.items():
            clean_line = clean_line.replace(emoji, replacement)
        
        return clean_line

    def _create_error_pdf(self, error_message: str) -> bytes:
        """
        Create error PDF document.
        
        Args:
            error_message (str): Error description
            
        Returns:
            bytes: Error PDF as bytes
        """
        try:
            buffer = io.BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=A4)
            
            story = [
                Paragraph("Export Error", getSampleStyleSheet()['Title']),
                Spacer(1, 12),
                Paragraph(f"Failed to convert report: {error_message}", getSampleStyleSheet()['Normal']),
                Spacer(1, 12),
                Paragraph("Please try again or contact support if the problem persists.", getSampleStyleSheet()['Normal'])
            ]
            
            doc.build(story)
            buffer.seek(0)
            return buffer.getvalue()
            
        except Exception as e:
            logger.error(f"Error creating error PDF: {e}")
            return b"Error creating PDF document"

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
            
            # Check for extremely long content
            if len(markdown_content) > 2000000:  # 2MB limit for PDF
                logger.warning(f"Markdown content very large: {len(markdown_content):,} characters")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Markdown validation error: {e}")
            return False

    def get_document_info(self, markdown_content: str) -> dict:
        """
        Get information about the PDF to be created.
        
        Args:
            markdown_content (str): Markdown content
            
        Returns:
            dict: Document information
        """
        try:
            lines = markdown_content.split('\n')
            
            # Count different elements
            headings = len([line for line in lines if line.strip().startswith('#')])
            paragraphs = len([line for line in lines if line.strip() and not line.strip().startswith('#') and not line.strip().startswith('-')])
            bullet_points = len([line for line in lines if line.strip().startswith('-') or line.strip().startswith('*')])
            severity_items = len([line for line in lines if self._contains_severity_indicator(line)])
            
            # Estimate pages (rough calculation)
            estimated_pages = max(1, len(markdown_content) // 2500)  # Roughly 2500 chars per page
            
            return {
                'total_lines': len(lines),
                'headings': headings,
                'paragraphs': paragraphs,
                'bullet_points': bullet_points,
                'severity_items': severity_items,
                'estimated_pages': estimated_pages,
                'character_count': len(markdown_content),
                'word_count_estimate': len(markdown_content.split()),
                'file_size_estimate': f"{len(markdown_content) // 1024}KB"
            }
            
        except Exception as e:
            logger.error(f"Error getting document info: {e}")
            return {
                'total_lines': 0,
                'headings': 0,
                'paragraphs': 0,
                'bullet_points': 0,
                'severity_items': 0,
                'estimated_pages': 1,
                'character_count': 0,
                'word_count_estimate': 0,
                'file_size_estimate': '0KB'
            }

    def create_table_from_data(self, data: List[List[str]], headers: List[str] = None) -> Table:
        """
        Create a formatted table for PDF inclusion.
        
        Args:
            data (list): List of rows (each row is a list of strings)
            headers (list): Optional header row
            
        Returns:
            Table: ReportLab table object
        """
        try:
            # Prepare table data
            table_data = []
            if headers:
                table_data.append(headers)
            table_data.extend(data)
            
            # Create table
            table = Table(table_data)
            
            # Style the table
            table_style = TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#34495e')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 10),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ])
            
            table.setStyle(table_style)
            return table
            
        except Exception as e:
            logger.error(f"Error creating table: {e}")
            return None
