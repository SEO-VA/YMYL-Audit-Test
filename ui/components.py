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

# Import export manager with error handling
try:
    from exporters.export_manager import ExportManager
    EXPORTS_AVAILABLE = True
except ImportError:
    EXPORTS_AVAILABLE = False


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
    
    # Assistant configuration info
    try:
        from config.settings import ANALYZER_ASSISTANT_ID
        st.sidebar.markdown("### 🤖 Assistant Configuration")
        st.sidebar.info(f"**Assistant ID**: `{ANALYZER_ASSISTANT_ID[:20]}...`")
        st.sidebar.caption("Using OpenAI Assistant with PDF knowledge base")
    except ImportError:
        pass
    
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
3. **YMYL Analysis**: AI-powered YMYL audit of the content using Assistant with PDF knowledge.
4. **Export**: Generate professional reports in multiple formats.
""")
    st.info("💡 **Features**: AI-powered YMYL compliance analysis with multi-format export and PDF knowledge base!")


def create_url_input_section() -> str:
    """
    Create URL input section with validation.
    
    Returns:
        str: URL entered by user
    """
    st.markdown("### 🌐 Website Analysis")
    
    # URL input with helpful placeholder
    url = st.text_input(
        "Enter URL to analyze:", 
        placeholder="https://example.com/page-to-audit",
        help="Enter the complete URL including http:// or https://"
    )
    
    # URL validation feedback
    if url:
        if url.startswith(('http://', 'https://')):
            st.success("✅ Valid URL format")
        else:
            st.warning("⚠️ URL should start with http:// or https://")
            url = ""  # Clear invalid URL
    
    return url


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


def create_processing_status_display():
    """
    Create processing status display for real-time updates.
    
    Returns:
        dict: Display containers
    """
    st.markdown("### 🔄 Processing Status")
    
    # Create containers for different status elements
    progress_container = st.container()
    metrics_container = st.container()
    log_container = st.container()
    
    with progress_container:
        progress_bar = st.progress(0)
        status_text = st.empty()
    
    with metrics_container:
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            metric_processed = st.empty()
        with col2:
            metric_success_rate = st.empty()
        with col3:
            metric_current_status = st.empty()
        with col4:
            metric_time = st.empty()
    
    with log_container:
        log_area = st.empty()
    
    return {
        'progress_bar': progress_bar,
        'status_text': status_text,
        'metric_processed': metric_processed,
        'metric_success_rate': metric_success_rate,
        'metric_current_status': metric_current_status,
        'metric_time': metric_time,
        'log_area': log_area
    }


def create_cancellation_button() -> bool:
    """
    Create cancellation button for long-running processes.
    
    Returns:
        bool: True if cancel button was clicked
    """
    return st.button(
        "🛑 Cancel Processing",
        type="secondary",
        help="Cancel the current AI analysis"
    )


def display_chunk_preview(chunks: List[Dict[str, Any]], max_preview: int = 5):
    """
    Display preview of content chunks.
    
    Args:
        chunks (list): List of content chunks
        max_preview (int): Maximum number of chunks to preview
    """
    st.markdown("### 📄 Content Preview")
    
    if not chunks:
        st.info("No content chunks available")
        return
    
    st.info(f"Found {len(chunks)} content sections. Showing preview of first {min(len(chunks), max_preview)} sections:")
    
    for i, chunk in enumerate(chunks[:max_preview]):
        chunk_index = chunk.get('index', i + 1)
        content = chunk.get('text', chunk.get('content', ''))
        char_count = len(content)
        
        with st.expander(f"Preview - Section {chunk_index} ({char_count:,} characters)"):
            # Show first 200 characters
            preview = content[:200]
            if len(content) > 200:
                preview += "..."
            st.text(preview)
    
    if len(chunks) > max_preview:
        st.caption(f"... and {len(chunks) - max_preview} more sections")


def create_export_section(report_content: str, url: str):
    """
    Create export section with download buttons.
    
    Args:
        report_content (str): Report content to export
        url (str): Source URL for filename
    """
    st.markdown("### 📥 Export Report")
    
    if not EXPORTS_AVAILABLE:
        st.warning("⚠️ Export functionality not available")
        # Fallback markdown download
        timestamp = int(time.time())
        st.download_button(
            label="💾 Download Report (Markdown)",
            data=report_content,
            file_name=f"ymyl_audit_report_{timestamp}.md",
            mime="text/markdown"
        )
        return
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.info("Generate professional reports in multiple formats")
    
    with col2:
        if st.button("📄 Generate Exports", type="secondary"):
            _generate_export_files(report_content, url)


def _generate_export_files(report_content: str, url: str):
    """Generate and display export files"""
    with st.spinner("📄 Generating export files..."):
        try:
            export_manager = ExportManager()
            
            results = export_manager.export_all_formats(
                markdown_content=report_content,
                title=f"YMYL Audit Report - {url}",
                formats=["html", "pdf", "docx", "markdown"]
            )
            
            if results.get("success"):
                _display_download_buttons(results, export_manager)
            else:
                st.error(f"❌ Export failed: {results.get('error', 'Unknown error')}")
                
        except Exception as e:
            st.error(f"❌ Export generation failed: {str(e)}")


def _display_download_buttons(results: Dict[str, Any], export_manager):
    """Display download buttons for export results"""
    formats_data = results.get('formats', {})
    
    if not formats_data:
        st.error("❌ No export formats were generated")
        return
    
    st.success("✅ Export files generated successfully!")
    
    # Create download buttons in columns
    cols = st.columns(len(formats_data))
    
    format_configs = {
        'html': {'label': "📄 HTML", 'mime': "text/html"},
        'pdf': {'label': "📑 PDF", 'mime': "application/pdf"},
        'docx': {'label': "📝 Word", 'mime': "application/vnd.openxmlformats-officedocument.wordprocessingml.document"},
        'markdown': {'label': "📋 Markdown", 'mime': "text/markdown"}
    }
    
    for i, (fmt, data) in enumerate(formats_data.items()):
        if i < len(cols) and fmt in format_configs:
            with cols[i]:
                filename = export_manager.create_filename("ymyl_audit_report", fmt)
                config = format_configs[fmt]
                
                st.download_button(
                    label=config['label'],
                    data=data,
                    file_name=filename,
                    mime=config['mime']
                )


def _create_ai_report_tab(ai_result: Dict[str, Any]):
    """Create AI compliance report tab content."""
    st.markdown("### YMYL Compliance Analysis Report")
    
    ai_report = ai_result['report']
    
    # Copy section
    st.markdown("#### 📋 Copy Report")
    st.code(ai_report, language='markdown')
    
    # Export section
    create_export_section(ai_report, ai_result.get('url', 'unknown'))
    
    # Formatted report viewer
    with st.expander("📖 View Formatted Report"):
        st.markdown(ai_report)


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
    st.code(result.get('json_output', '{}'), language='json')
    st.download_button(
        label="💾 Download JSON",
        data=result.get('json_output', '{}'),
        file_name=f"chunks_{int(time.time())}.json",
        mime="application/json"
    )


def _create_content_tab(result: Dict[str, Any]):
    """Create extracted content tab content."""
    st.text_area(
        "Raw extracted content:", 
        value=result.get('extracted_content', ''), 
        height=400,
        help="Original content extracted from the webpage"
    )


def _create_summary_tab(result: Dict[str, Any], ai_result: Optional[Dict[str, Any]] = None):
    """Create processing summary tab content."""
    st.subheader("Processing Summary")
    
    # Parse JSON for chunk statistics
    try:
        import json
        json_data = json.loads(result.get('json_output', '{}'))
        big_chunks = json_data.get('big_chunks', [])
        total_small_chunks = sum(len(chunk.get('small_chunks', [])) for chunk in big_chunks)
        
        # Content extraction metrics
        st.markdown("#### Content Extraction")
        colA, colB, colC = st.columns(3)
        colA.metric("Big Chunks", len(big_chunks))
        colB.metric("Total Small Chunks", total_small_chunks)
        colC.metric("Content Length", f"{len(result.get('extracted_content', '')):,} chars")
        
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
    
    st.info(f"**Source URL**: {result.get('url', 'Unknown')}")


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
        
        # Show chunk preview
        st.write("**Chunk Details:**")
        for i, chunk in enumerate(chunks[:5]):  # Show first 5 chunks
            content_key = 'text' if 'text' in chunk else 'content'
            char_count = len(chunk.get(content_key, ''))
            st.write(f"- Chunk {chunk.get('index', i+1)}: {char_count:,} characters")
        if len(chunks) > 5:
            st.write(f"- ... and {len(chunks) - 5} more chunks")
    
    # Progress tracking
    progress_bar = st.progress(0)
    status_container = st.empty()
    
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


def show_performance_metrics(stats: Dict[str, Any]):
    """
    Display performance metrics in a formatted way.
    
    Args:
        stats (dict): Processing statistics
    """
    if not stats:
        return
    
    st.markdown("### ⚡ Performance Metrics")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total_chunks = stats.get('total_chunks', 0)
        st.metric("Total Processed", total_chunks)
    
    with col2:
        successful = stats.get('successful', 0)
        st.metric("Successful", successful)
    
    with col3:
        total_time = stats.get('total_processing_time', 0)
        st.metric("Total Time", f"{total_time:.1f}s")
    
    with col4:
        if total_chunks > 0:
            avg_time = total_time / total_chunks
            st.metric("Avg/Chunk", f"{avg_time:.1f}s")
    
    # Additional metrics
    if total_chunks > 0:
        success_rate = (successful / total_chunks) * 100
        st.progress(success_rate / 100)
        st.caption(f"Success Rate: {success_rate:.1f}%")
