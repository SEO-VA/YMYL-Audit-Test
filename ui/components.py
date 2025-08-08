#!/usr/bin/env python3
"""
UI Components for YMYL Audit Tool

Reusable Streamlit UI components for the application interface.

FIXED: Enhanced components to support stale AI results prevention and better user feedback
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
    
    # FIXED: Add session state management options
    with st.sidebar.expander("🧹 Session Management"):
        if st.button("Clear All Analysis Data", help="Clear all stored analysis results"):
            keys_to_clear = [k for k in st.session_state.keys() if k.startswith(('latest_', 'ai_', 'current_url', 'processing_'))]
            for key in keys_to_clear:
                del st.session_state[key]
            st.success(f"Cleared {len(keys_to_clear)} session keys")
            st.experimental_rerun()
    
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
    
    FIXED: Enhanced with current context display and warnings
    
    Returns:
        tuple: (url, process_clicked)
    """
    # FIXED: Show current analysis context if available
    current_url = st.session_state.get('current_url_analysis')
    if current_url:
        st.info(f"📋 **Currently analyzing**: {current_url}")
        
        # Check if we have AI results for this URL
        ai_result = st.session_state.get('ai_analysis_result')
        if ai_result and ai_result.get('success'):
            analysis_time = ai_result.get('processing_time', 0)
            st.success(f"✅ **AI Analysis Complete** for this URL (took {analysis_time:.1f}s)")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        url = st.text_input(
            "Enter the URL to process:", 
            help="Include http:// or https:// - Processing a new URL will clear previous AI analysis results",
            placeholder="https://example.com/page-to-analyze"
        )
    
    with col2:
        st.markdown("<br>", unsafe_allow_html=True)  # Spacing to align with input
        
        # FIXED: Show warning if URL is different from current analysis
        button_type = "primary"
        button_help = "Process the URL to extract content and prepare for AI analysis"
        
        if current_url and url and url != current_url:
            button_help = "⚠️ Processing new URL will clear current AI analysis results"
            st.caption("🔄 New URL detected")
        
        process_clicked = st.button(
            "🚀 Process URL", 
            type=button_type, 
            use_container_width=True,
            help=button_help
        )
    
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
        # FIXED: Limit log lines to prevent memory issues
        if len(log_lines) > 50:
            log_lines.pop(0)
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
        # FIXED: Limit milestone history
        if len(milestones) > 10:
            milestones.pop(0)
        log_area.markdown("\n".join(milestones))
    
    return log_area, update_progress

def create_ai_analysis_section(api_key: Optional[str], json_output: str, source_result: Optional[Dict] = None) -> bool:
    """
    Create AI analysis section with processing button.
    
    FIXED: Enhanced validation and user feedback for stale results prevention
    
    Args:
        api_key (str): OpenAI API key
        json_output (str): JSON output from chunk processing
        source_result (dict): Source processing result for validation
        
    Returns:
        bool: True if analysis button was clicked, False otherwise
    """
    if not api_key:
        st.info("💡 **Tip**: Add your OpenAI API key to enable AI compliance analysis!")
        return False
    
    # FIXED: Enhanced AI analysis section with better feedback
    st.markdown("### 🤖 AI Compliance Analysis")
    
    # Show analysis readiness status
    if json_output:
        try:
            import json
            data = json.loads(json_output)
            chunk_count = len(data.get('big_chunks', []))
            
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.write(f"📊 **Content Ready**: {chunk_count} chunks prepared for AI analysis")
                
                # Check for existing AI results
                ai_result = st.session_state.get('ai_analysis_result')
                if ai_result and ai_result.get('success'):
                    # FIXED: Validate freshness of AI results
                    is_fresh = True
                    if source_result:
                        source_timestamp = source_result.get('processing_timestamp', 0)
                        ai_timestamp = ai_result.get('processing_timestamp', -1)
                        is_fresh = (source_timestamp == ai_timestamp)
                    
                    if is_fresh:
                        st.success("✅ **Fresh AI Analysis Available** - View results in tabs below")
                    else:
                        st.warning("⚠️ **Stale AI Results Detected** - Run analysis again for current content")
            
            with col2:
                button_label = "🤖 Run AI Analysis"
                button_type = "secondary"
                button_help = "Analyze content for YMYL compliance using AI"
                
                # FIXED: Customize button based on current state
                ai_result = st.session_state.get('ai_analysis_result')
                if ai_result and ai_result.get('success'):
                    if source_result:
                        source_timestamp = source_result.get('processing_timestamp', 0)
                        ai_timestamp = ai_result.get('processing_timestamp', -1)
                        if source_timestamp == ai_timestamp:
                            button_label = "🔄 Re-run Analysis"
                            button_help = "Run AI analysis again on current content"
                        else:
                            button_label = "🆕 Analyze New Content"
                            button_help = "Run AI analysis on the new content"
                            button_type = "primary"
                
                return st.button(
                    button_label,
                    type=button_type, 
                    use_container_width=True,
                    help=button_help
                )
                
        except json.JSONDecodeError:
            st.error("❌ Invalid JSON output - cannot proceed with AI analysis")
            return False
    else:
        st.info("📝 Process a URL first to enable AI analysis")
        return False

def create_content_freshness_indicator(content_result: Dict, ai_result: Optional[Dict] = None):
    """
    Create indicator showing freshness of analysis results.
    
    FIXED: New component to show relationship between content and AI results
    
    Args:
        content_result (dict): Content processing result
        ai_result (dict): AI analysis result (optional)
    """
    if not ai_result:
        return
    
    # Check timestamps
    content_timestamp = content_result.get('processing_timestamp', 0)
    ai_timestamp = ai_result.get('processing_timestamp', -1)
    content_url = content_result.get('url', '')
    ai_url = ai_result.get('source_url', '')
    
    is_fresh = (content_timestamp == ai_timestamp and content_url == ai_url)
    
    if is_fresh:
        st.success("✅ **AI Results Match Current Content** - Analysis is up to date")
    else:
        st.warning("⚠️ **AI Results May Be Outdated** - Consider re-running AI analysis")
        
        with st.expander("🔍 Freshness Details"):
            st.write(f"**Content Timestamp**: {content_timestamp}")
            st.write(f"**AI Analysis Timestamp**: {ai_timestamp}")
            st.write(f"**Content URL**: {content_url}")
            st.write(f"**AI Analysis URL**: {ai_url}")

def create_results_tabs(result: Dict[str, Any], ai_result: Optional[Dict[str, Any]] = None):
    """
    Create results display tabs.
    
    FIXED: Enhanced with freshness validation and better user guidance
    
    Args:
        result (dict): Processing results
        ai_result (dict): AI analysis results (optional)
    """
    # FIXED: Show freshness indicator before tabs
    if ai_result and ai_result.get('success'):
        create_content_freshness_indicator(result, ai_result)
    
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
            _create_ai_report_tab(ai_result, result)
        
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

def _create_ai_report_tab(ai_result: Dict[str, Any], content_result: Optional[Dict[str, Any]] = None):
    """
    Create AI compliance report tab content.
    
    FIXED: Enhanced with freshness validation and metadata display
    """
    st.markdown("### YMYL Compliance Analysis Report")
    
    # FIXED: Show analysis metadata and freshness info
    if content_result:
        col1, col2, col3 = st.columns(3)
        
        with col1:
            processing_time = ai_result.get('processing_time', 0)
            st.metric("Processing Time", f"{processing_time:.2f}s")
        
        with col2:
            source_url = ai_result.get('source_url', content_result.get('url', 'Unknown'))
            if len(source_url) > 30:
                display_url = source_url[:30] + "..."
            else:
                display_url = source_url
            st.metric("Source URL", display_url)
        
        with col3:
            timestamp_match = (
                content_result.get('processing_timestamp', 0) == 
                ai_result.get('processing_timestamp', -1)
            )
            freshness = "Fresh ✅" if timestamp_match else "Stale ⚠️"
            st.metric("Result Status", freshness)
    
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
    """
    Create processing summary tab content.
    
    FIXED: Enhanced with freshness indicators and better metrics display
    """
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
            
            # FIXED: Show freshness status in summary
            st.markdown("#### Analysis Status")
            content_timestamp = result.get('processing_timestamp', 0)
            ai_timestamp = ai_result.get('processing_timestamp', -1)
            is_fresh = (content_timestamp == ai_timestamp)
            
            colH, colI = st.columns(2)
            with colH:
                freshness_status = "Fresh ✅" if is_fresh else "Stale ⚠️"
                st.metric("Result Freshness", freshness_status)
            with colI:
                source_match = result.get('url') == ai_result.get('source_url')
                source_status = "Match ✅" if source_match else "Mismatch ⚠️"
                st.metric("Source URL", source_status)
            
            # Performance insights
            if stats.get('total_processing_time', 0) > 0 and stats.get('total_chunks', 0) > 0:
                avg_time = stats['total_processing_time'] / stats['total_chunks']
                efficiency = "High" if stats['total_processing_time'] < stats['total_chunks'] * 2 else "Moderate"
                st.info(f"📊 **Performance**: Average {avg_time:.2f}s per chunk | Parallel efficiency: {efficiency}")
        
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
    
    return {
        'progress_bar': progress_bar,
        'status_container': status_container,
        'log_container': log_container
    }

def display_error_message(error: str, error_type: str = "Error"):
    """Display formatted error message."""
    st.error(f"**{error_type}**: {error}")

def display_success_message(message: str):
    """Display formatted success message."""
    st.success(message)

def create_info_panel(title: str, content: str, icon: str = "ℹ️"):
    """Create an information panel."""
    st.info(f"{icon} **{title}**: {content}")

# FIXED: New utility functions for stale results management
def show_stale_results_warning(result: Dict[str, Any], ai_result: Dict[str, Any]) -> bool:
    """
    Show warning about stale results and return whether user wants to clear them.
    
    Returns:
        bool: True if user clicked clear button
    """
    st.warning("⚠️ **Stale AI Results Detected**: These results may be from a previous URL analysis.")
    
    col1, col2 = st.columns([3, 1])
    with col1:
        st.write("The AI analysis shown may not correspond to the current content.")
    with col2:
        return st.button("🧹 Clear Stale Results", type="secondary")

def create_analysis_context_display():
    """Display current analysis context information."""
    current_url = st.session_state.get('current_url_analysis')
    if current_url:
        with st.expander("📋 Current Analysis Context"):
            st.write(f"**URL**: {current_url}")
            st.write(f"**Timestamp**: {st.session_state.get('processing_timestamp', 'Unknown')}")
            
            ai_result = st.session_state.get('ai_analysis_result')
            if ai_result:
                ai_url = ai_result.get('source_url', 'Unknown')
                ai_timestamp = ai_result.get('processing_timestamp', 'Unknown')
                st.write(f"**AI Analysis URL**: {ai_url}")
                st.write(f"**AI Analysis Timestamp**: {ai_timestamp}")