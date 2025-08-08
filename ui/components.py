#!/usr/bin/env python3
"""
UI Components for YMYL Audit Tool

Reusable Streamlit UI components for the application interface.
"""

import streamlit as st
import time
from datetime import datetime
from typing import Dict, Any, Optional, List, Callable
from config.settings import DEFAULT_TIMEZONE
from utils.logging_utils import log_with_timestamp
from exporters.export_manager import ExportManager

def create_page_header():
    """Create the main page header with title and description."""
    st.title("🕵 YMYL Audit Tool")
    st.markdown("**Automatically extract content from websites, generate JSON chunks, and perform YMYL compliance analysis**")
    st.markdown("---")

def create_sidebar_config(debug_mode_default: bool = True) -> Dict[str, Any]:
    """
    Create sidebar configuration section.
    
    Args:
        debug_mode_default (bool): Default debug mode setting
        
    Returns:
        dict: Configuration settings
    """
    st.sidebar.markdown("### 🔧 Configuration")
    
    # Debug mode toggle
    debug_mode = st.sidebar.checkbox(
        "🐛 Debug Mode", 
        value=debug_mode_default, 
        help="Show detailed processing logs"
    )
    
    # API Key configuration
    st.sidebar.markdown("### 🔑 AI Analysis Configuration")
    
    # Try to get API key from secrets first
    api_key = None
    try:
        api_key = st.secrets["openai_api_key"]
        st.sidebar.success("✅ API Key loaded from secrets")
    except Exception:
        api_key = st.sidebar.text_input(
            "OpenAI API Key:",
            type="password",
            help="Enter your OpenAI API key for AI analysis"
        )
        if api_key:
            st.sidebar.success("✅ API Key provided")
        else:
            st.sidebar.warning("⚠️ API Key needed for AI analysis")
    
    return {
        'debug_mode': debug_mode,
        'api_key': api_key
    }

def create_how_it_works_section():
    """Create the 'How it works' information section."""
    st.subheader("ℹ️ How it works")
    st.markdown("""
1. **Extract**: Extract the content from the webpage.
2. **Chunk**: Send extracted text to Chunk Norris for processing.
3. **YMYL Analysis**: AI-powered YMYL audit of the content.
4. **Export**: Generate professional reports in multiple formats.
""")
    st.info("💡 **New**: AI-powered YMYL compliance analysis with multi-format export!")

def create_url_input_section() -> tuple[str, bool]:
    """
    Create URL input section with processing button.
    
    Returns:
        tuple: (url, process_clicked)
    """
    col1, col2 = st.columns([2, 1])
    
    with col1:
        url = st.text_input("Enter the URL to process:", help="Include http:// or https://")
    
    with col2:
        st.markdown("<br>", unsafe_allow_html=True)  # Spacing to align with input
        process_clicked = st.button("🚀 Process URL", type="primary", use_container_width=True)
    
    return url, process_clicked

def create_debug_logger(placeholder) -> Callable[[str], None]:
    """
    Create debug logger function for detailed logging.
    
    Args:
        placeholder: Streamlit placeholder for log output
        
    Returns:
        function: Logging callback function
    """
    log_lines = []
    
    def log_callback(message: str):
        timestamped_msg = log_with_timestamp(message, DEFAULT_TIMEZONE)
        log_lines.append(timestamped_msg)
        placeholder.info("\n".join(log_lines))
    
    return log_callback

def create_simple_progress_tracker() -> tuple[Any, Callable[[str], None]]:
    """
    Create simple progress tracker for non-debug mode.
    
    Returns:
        tuple: (placeholder, update_function)
    """
    log_area = st.empty()
    milestones = []
    
    def update_progress(text: str):
        milestones.append(f"- {text}")
        log_area.markdown("\n".join(milestones))
    
    return log_area, update_progress

def create_ai_analysis_section(api_key: Optional[str], json_output: str) -> bool:
    """
    Create AI analysis section with processing button.
    
    Args:
        api_key (str): OpenAI API key
        json_output (str): JSON output from chunk processing
        
    Returns:
        bool: True if analysis button was clicked, False otherwise
    """
    if not api_key:
        st.info("💡 **Tip**: Add your OpenAI API key to enable AI compliance analysis!")
        return False
    
    return st.button(
        "🤖 Process with AI Compliance Analysis", 
        type="secondary", 
        use_container_width=True,
        help="Analyze content for YMYL compliance using AI"
    )

def create_results_tabs(result: Dict[str, Any], ai_result: Optional[Dict[str, Any]] = None):
    """
    Create results display tabs.
    
    Args:
        result (dict): Processing results
        ai_result (dict): AI analysis results (optional)
    """
    if ai_result and ai_result.get('success'):
        # With AI analysis results
        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "🎯 AI Compliance Report", 
            "📊 Individual Analyses", 
            "🔧 JSON Output", 
            "📄 Extracted Content", 
            "📈 Summary"
        ])
        
        with tab1:
            _create_ai_report_tab(ai_result)
        
        with tab2:
            _create_individual_analyses_tab(ai_result)
        
        with tab3:
            _create_json_tab(result)
        
        with tab4:
            _create_content_tab(result)
        
        with tab5:
            _create_summary_tab(result, ai_result)
    
    else:
        # Without AI analysis results
        tab1, tab2, tab3 = st.tabs([
            "🎯 JSON Output", 
            "📄 Extracted Content", 
            "📈 Summary"
        ])
        
        with tab1:
            _create_json_tab(result)
        
        with tab2:
            _create_content_tab(result)
        
        with tab3:
            _create_summary_tab(result)

def _create_ai_report_tab(ai_result: Dict[str, Any]):
    """Create AI compliance report tab content."""
    st.markdown("### YMYL Compliance Analysis Report")
    
    ai_report = ai_result['report']
    
    # Copy section
    st.markdown("#### 📋 Copy Report")
    st.code(ai_report, language='markdown')
    
    # Export section
    st.markdown("#### 📄 Download Formats")
    st.markdown("Choose your preferred format for professional use:")
    
    try:
        # Create export manager and generate all formats
        with ExportManager() as export_mgr:
            export_results = export_mgr.export_all_formats(ai_report)
            
            if export_results['success'] and export_results['formats']:
                _create_download_buttons(export_results['formats'])
            else:
                st.error("Failed to generate export formats")
                # Fallback to markdown download
                timestamp = int(time.time())
                st.download_button(
                    label="💾 Download Report (Markdown)",
                    data=ai_report,
                    file_name=f"ymyl_compliance_report_{timestamp}.md",
                    mime="text/markdown"
                )
    
    except Exception as e:
        st.error(f"Error creating export formats: {e}")
        # Fallback download
        timestamp = int(time.time())
        st.download_button(
            label="💾 Download Report (Markdown)",
            data=ai_report,
            file_name=f"ymyl_compliance_report_{timestamp}.md",
            mime="text/markdown"
        )
    
    # Format guide
    st.info("""
    💡 **Format Guide:**
    - **Markdown**: Best for developers and copy-pasting to other platforms
    - **HTML**: Opens in web browsers, styled and formatted
    - **Word**: Professional business format, editable and shareable
    - **PDF**: Final presentation format, preserves formatting across devices
    """)
    
    # Formatted report viewer
    with st.expander("📖 View Formatted Report"):
        st.markdown(ai_report)

def _create_download_buttons(formats: Dict[str, bytes]):
    """Create download buttons for different formats."""
    timestamp = int(time.time())
    
    col1, col2, col3, col4 = st.columns(4)
    
    format_configs = {
        'markdown': {
            'label': "📝 Markdown",
            'mime': "text/markdown",
            'help': "Original markdown format - perfect for copying to other platforms"
        },
        'html': {
            'label': "🌐 HTML", 
            'mime': "text/html",
            'help': "Styled HTML document - opens in any web browser"
        },
        'docx': {
            'label': "📄 Word",
            'mime': "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            'help': "Microsoft Word document - ready for editing and sharing"
        },
        'pdf': {
            'label': "📋 PDF",
            'mime': "application/pdf", 
            'help': "Professional PDF document - perfect for presentations and archival"
        }
    }
    
    columns = [col1, col2, col3, col4]
    
    for i, (fmt, config) in enumerate(format_configs.items()):
        if fmt in formats and i < len(columns):
            with columns[i]:
                file_extension = {
                    'markdown': '.md',
                    'html': '.html', 
                    'docx': '.docx',
                    'pdf': '.pdf'
                }.get(fmt, f'.{fmt}')
                
                st.download_button(
                    label=config['label'],
                    data=formats[fmt],
                    file_name=f"ymyl_compliance_report_{timestamp}{file_extension}",
                    mime=config['mime'],
                    help=config['help']
                )

def _create_individual_analyses_tab(ai_result: Dict[str, Any]):
    """Create individual analyses tab content."""
    st.markdown("### Individual Chunk Analysis Results")
    
    analysis_details = ai_result.get('analysis_results', [])
    stats = ai_result.get('statistics', {})
    
    # Processing metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Processing Time", f"{stats.get('total_processing_time', 0):.2f}s")
    with col2:
        st.metric("Total Chunks", stats.get('total_chunks', 0))
    with col3:
        st.metric("Successful", stats.get('successful_analyses', 0))
    with col4:
        st.metric("Failed", stats.get('failed_analyses', 0))
    
    st.markdown("---")
    
    # Individual results
    for detail in analysis_details:
        chunk_idx = detail.get('chunk_index', 'Unknown')
        if detail.get('success'):
            with st.expander(f"✅ Chunk {chunk_idx} Analysis (Success)"):
                st.markdown(detail['content'])
                if 'processing_time' in detail:
                    st.caption(f"Processing time: {detail['processing_time']:.2f}s")
        else:
            with st.expander(f"❌ Chunk {chunk_idx} Analysis (Failed)"):
                st.error(f"Error: {detail.get('error', 'Unknown error')}")

def _create_json_tab(result: Dict[str, Any]):
    """Create JSON output tab content."""
    st.code(result['json_output'], language='json')
    st.download_button(
        label="💾 Download JSON",
        data=result['json_output'],
        file_name=f"chunks_{int(time.time())}.json",
        mime="application/json"
    )

def _create_content_tab(result: Dict[str, Any]):
    """Create extracted content tab content."""
    st.text_area(
        "Raw extracted content:", 
        value=result['extracted_content'], 
        height=400,
        help="Original content extracted from the webpage"
    )

def _create_summary_tab(result: Dict[str, Any], ai_result: Optional[Dict[str, Any]] = None):
    """Create processing summary tab content."""
    st.subheader("Processing Summary")
    
    # Parse JSON for chunk statistics
    try:
        import json
        json_data = json.loads(result['json_output'])
        big_chunks = json_data.get('big_chunks', [])
        total_small_chunks = sum(len(chunk.get('small_chunks', [])) for chunk in big_chunks)
        
        # Content extraction metrics
        st.markdown("#### Content Extraction")
        colA, colB, colC = st.columns(3)
        colA.metric("Big Chunks", len(big_chunks))
        colB.metric("Total Small Chunks", total_small_chunks)
        colC.metric("Content Length", f"{len(result['extracted_content']):,} chars")
        
        # AI Analysis metrics (if available)
        if ai_result and ai_result.get('success'):
            st.markdown("#### AI Analysis Performance")
            stats = ai_result.get('statistics', {})
            
            colD, colE, colF, colG = st.columns(4)
            colD.metric("Processing Time", f"{stats.get('total_processing_time', 0):.2f}s")
            colE.metric("Successful Analyses", stats.get('successful_analyses', 0))
            colF.metric("Failed Analyses", stats.get('failed_analyses', 0))
            colG.metric("Success Rate", f"{stats.get('success_rate', 0):.1f}%")
            
            # Performance insights
            if stats.get('total_processing_time', 0) > 0 and stats.get('total_chunks', 0) > 0:
                avg_time = stats['total_processing_time'] / stats['total_chunks']
                st.info(f"📊 **Performance**: Average {avg_time:.2f}s per chunk | Parallel efficiency achieved")
        
    except (json.JSONDecodeError, TypeError, KeyError) as e:
        st.warning(f"Could not parse JSON for statistics: {e}")
    
    st.info(f"**Source URL**: {result['url']}")

def create_ai_processing_interface(json_output: str, api_key: str, chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Create enhanced AI processing interface with real-time updates.
    
    Args:
        json_output (str): JSON output from chunk processing
        api_key (str): OpenAI API key
        chunks (list): List of content chunks
        
    Returns:
        dict: Processing results
    """
    # Enhanced processing logs section
    st.subheader("🔍 Processing Logs")
    log_container = st.container()
    
    with log_container:
        st.info(f"🚀 Starting parallel analysis of {len(chunks)} chunks...")
        st.write("**Configuration:**")
        col1, col2 = st.columns(2)
        with col1:
            st.write("- Analysis Engine: OpenAI Assistant API")
            st.write("- Processing Mode: Parallel")
        with col2:
            st.write(f"- API Key: {'✅ Valid' if api_key.startswith('sk-') else '❌ Invalid'}")
            st.write(f"- Total Chunks: {len(chunks)}")
        
        st.write("**Chunk Details:**")
        for i, chunk in enumerate(chunks[:5]):  # Show first 5 chunks
            st.write(f"- Chunk {chunk['index']}: {len(chunk['text']):,} characters")
        if len(chunks) > 5:
            st.write(f"- ... and {len(chunks) - 5} more chunks")
    
    # Progress tracking
    progress_bar = st.progress(0)
    status_container = st.empty()
    
    # Processing would happen here in the main application
    # This function provides the UI structure
    
    return {
        'progress_bar': progress_bar,
        'status_container': status_container,
        'log_container': log_container
    }

def display_error_message(error: str, error_type: str = "Error"):
    """
    Display formatted error message.
    
    Args:
        error (str): Error message
        error_type (str): Type of error
    """
    st.error(f"**{error_type}**: {error}")

def display_success_message(message: str):
    """
    Display formatted success message.
    
    Args:
        message (str): Success message
    """
    st.success(message)

def create_info_panel(title: str, content: str, icon: str = "ℹ️"):
    """
    Create an information panel.
    
    Args:
        title (str): Panel title
        content (str): Panel content
        icon (str): Icon to display
    """
    st.info(f"{icon} **{title}**: {content}")
