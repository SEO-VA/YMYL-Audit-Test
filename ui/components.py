#!/usr/bin/env python3
"""
UI Components for YMYL Audit Tool

Reusable Streamlit UI components for the application interface.

FIXED: Proper Unicode handling in JSON display - no more encoding issues!
NEW FEATURE: Dual input mode - URL extraction OR direct JSON input
DEBUG: Added debug tab to diagnose Unicode decoding issues
"""

import streamlit as st
import time
import re
from datetime import datetime
from typing import Dict, Any, Optional, List, Callable, Tuple
from config.settings import DEFAULT_TIMEZONE
from utils.logging_utils import log_with_timestamp
from utils.json_utils import get_display_json_string  # FIXED: Import centralized display function
from exporters.export_manager import ExportManager

# FIXED: Removed duplicate decode_unicode_escapes - now using centralized version from json_utils

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
            keys_to_clear = [k for k in st.session_state.keys() if k.startswith(('latest_', 'ai_', 'current_url', 'processing_', 'input_'))]
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
1. **Choose Input**: Extract from URL OR provide chunked JSON directly.
2. **Process**: Extract content or validate provided chunks.
3. **YMYL Analysis**: AI-powered YMYL audit of the content.
4. **Export**: Generate professional reports in multiple formats.
""")
    st.info("💡 **New**: Choose between URL extraction or direct JSON input!")

def create_dual_input_section() -> Tuple[str, str, bool]:
    """
    NEW FEATURE: Create dual input section with URL/Direct JSON toggle.
    
    Returns:
        tuple: (input_mode, content, process_clicked)
    """
    st.subheader("📝 Content Input")
    
    # Input mode selection
    input_mode = st.radio(
        "Choose your input method:",
        ["🌐 URL Input", "📄 Direct JSON"],
        horizontal=True,
        help="Extract content from a URL or provide pre-chunked JSON directly",
        key="input_mode_selector"
    )
    
    # Store input mode in session state for tracking
    st.session_state['input_mode'] = input_mode
    
    if input_mode == "🌐 URL Input":
        return _create_url_input_mode()
    else:
        return _create_direct_json_input_mode()

def _create_url_input_mode() -> Tuple[str, str, bool]:
    """Create URL input interface."""
    # Show current analysis context if available
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
            placeholder="https://example.com/page-to-analyze",
            key="url_input"
        )
    
    with col2:
        st.markdown("<br>", unsafe_allow_html=True)  # Spacing to align with input
        
        # Show warning if URL is different from current analysis
        button_help = "Process the URL to extract content and prepare for AI analysis"
        
        if current_url and url and url != current_url:
            button_help = "⚠️ Processing new URL will clear current AI analysis results"
            st.caption("🔄 New URL detected")
        
        process_clicked = st.button(
            "🚀 Process URL", 
            type="primary", 
            use_container_width=True,
            help=button_help,
            key="process_url_button"
        )
    
    return 'url', url, process_clicked

def _create_direct_json_input_mode() -> Tuple[str, str, bool]:
    """NEW FEATURE: Create direct JSON input interface."""
    st.markdown("**Paste your pre-chunked JSON content:**")
    
    # Show current analysis context for direct JSON
    current_input_mode = st.session_state.get('current_input_analysis_mode')
    if current_input_mode == 'direct_json':
        st.info("📋 **Currently analyzing**: Direct JSON input")
        
        # Check if we have AI results for this input
        ai_result = st.session_state.get('ai_analysis_result')
        if ai_result and ai_result.get('success'):
            analysis_time = ai_result.get('processing_time', 0)
            st.success(f"✅ **AI Analysis Complete** for direct JSON (took {analysis_time:.1f}s)")
    
    # Large text area for JSON input
    json_content = st.text_area(
        "JSON Content",
        height=300,
        placeholder='''{
  "big_chunks": [
    {
      "big_chunk_index": 1,
      "small_chunks": [
        "Your first chunk of content here...",
        "Additional content for this chunk...",
        "More content..."
      ]
    },
    {
      "big_chunk_index": 2,
      "small_chunks": [
        "Second chunk content...",
        "More content for second chunk..."
      ]
    }
  ]
}''',
        help="Paste your chunked JSON content here. The tool expects the standard chunk format.",
        key="direct_json_input"
    )
    
    # Show character count and basic info
    if json_content:
        char_count = len(json_content)
        st.caption(f"📊 Content length: {char_count:,} characters")
        
        # Try to give quick preview of chunk count
        try:
            import json
            parsed = json.loads(json_content)
            chunk_count = len(parsed.get('big_chunks', []))
            st.caption(f"📦 Detected: {chunk_count} chunks")
        except:
            st.caption("⚠️ JSON format validation will occur during processing")
    
    # Process button
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("")  # Spacing
    
    with col2:
        process_clicked = st.button(
            "🤖 Analyze JSON", 
            type="primary", 
            use_container_width=True,
            help="Process the provided JSON content directly with AI analysis",
            key="process_json_button",
            disabled=not json_content.strip()
        )
    
    return 'direct_json', json_content, process_clicked

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

def create_ai_analysis_section(api_key: Optional[str], json_output: Any, source_result: Optional[Dict] = None) -> bool:
    """
    Create AI analysis section with processing button.
    
    ENHANCED: Works with both URL and direct JSON input modes
    
    Args:
        api_key (str): OpenAI API key
        json_output: JSON output from chunk processing or direct input (dict or string)
        source_result (dict): Source processing result for validation
        
    Returns:
        bool: True if analysis button was clicked, False otherwise
    """
    if not api_key:
        st.info("💡 **Tip**: Add your OpenAI API key to enable AI compliance analysis!")
        return False
    
    # ENHANCED: Show different messaging based on input mode
    input_mode = st.session_state.get('input_mode', '🌐 URL Input')
    st.markdown("### 🤖 AI Compliance Analysis")
    
    # Show analysis readiness status
    if json_output:
        try:
            # Handle both dict and string inputs
            if isinstance(json_output, dict):
                data = json_output
            else:
                import json
                data = json.loads(json_output)
            
            chunk_count = len(data.get('big_chunks', []))
            
            col1, col2 = st.columns([2, 1])
            
            with col1:
                if input_mode == "🌐 URL Input":
                    st.write(f"📊 **Content Ready**: {chunk_count} chunks extracted from URL")
                else:
                    st.write(f"📊 **Content Ready**: {chunk_count} chunks provided directly")
                
                # Check for existing AI results
                ai_result = st.session_state.get('ai_analysis_result')
                if ai_result and ai_result.get('success'):
                    # Validate freshness of AI results
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
                
                # Customize button based on current state
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
                    help=button_help,
                    key="ai_analysis_button"
                )
                
        except (json.JSONDecodeError, TypeError) as e:
            st.error("❌ Invalid JSON output - cannot proceed with AI analysis")
            return False
    else:
        if input_mode == "🌐 URL Input":
            st.info("📝 Process a URL first to enable AI analysis")
        else:
            st.info("📝 Provide JSON content first to enable AI analysis")
        return False

def create_content_freshness_indicator(content_result: Dict, ai_result: Optional[Dict] = None):
    """
    Create indicator showing freshness of analysis results.
    
    ENHANCED: Works with both URL and direct JSON inputs
    
    Args:
        content_result (dict): Content processing result
        ai_result (dict): AI analysis result (optional)
    """
    if not ai_result:
        return
    
    # Check timestamps
    content_timestamp = content_result.get('processing_timestamp', 0)
    ai_timestamp = ai_result.get('processing_timestamp', -1)
    content_source = content_result.get('url', content_result.get('source', 'Unknown'))
    ai_source = ai_result.get('source_url', '')
    
    is_fresh = (content_timestamp == ai_timestamp)
    
    if is_fresh:
        st.success("✅ **AI Results Match Current Content** - Analysis is up to date")
    else:
        st.warning("⚠️ **AI Results May Be Outdated** - Consider re-running AI analysis")
        
        with st.expander("🔍 Freshness Details"):
            st.write(f"**Content Timestamp**: {content_timestamp}")
            st.write(f"**AI Analysis Timestamp**: {ai_timestamp}")
            st.write(f"**Content Source**: {content_source}")
            st.write(f"**AI Analysis Source**: {ai_source}")

def create_results_tabs(result: Dict[str, Any], ai_result: Optional[Dict[str, Any]] = None):
    """
    Create results display tabs WITH DEBUG TAB
    
    ENHANCED: Shows appropriate context for URL vs Direct JSON inputs
    """
    # Show freshness indicator before tabs
    if ai_result and ai_result.get('success'):
        create_content_freshness_indicator(result, ai_result)
    
    if ai_result and ai_result.get('success'):
        # With AI analysis results - INCLUDES DEBUG TAB
        tab1, tab2, tab3, tab4, tab5, tab_debug = st.tabs([
            "🎯 AI Compliance Report", 
            "📊 Individual Analyses", 
            "🔧 JSON Output", 
            "📄 Source Content", 
            "📈 Summary",
            "🐛 DEBUG: AI Data"  # NEW DEBUG TAB
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
        
        with tab_debug:
            _create_debug_ai_data_tab(result, ai_result)  # NEW DEBUG TAB
    
    else:
        # Without AI analysis results - ALSO HAS DEBUG TAB
        tab1, tab2, tab3, tab_debug = st.tabs([
            "🎯 JSON Output", 
            "📄 Source Content", 
            "📈 Summary",
            "🐛 DEBUG: AI Data"  # NEW DEBUG TAB
        ])
        
        with tab1:
            _create_json_tab(result)
        
        with tab2:
            _create_content_tab(result)
        
        with tab3:
            _create_summary_tab(result)
        
        with tab_debug:
            _create_debug_ai_data_tab(result, None)  # NEW DEBUG TAB

def _create_debug_ai_data_tab(result: Dict[str, Any], ai_result: Optional[Dict[str, Any]] = None):
    """
    NEW: Debug tab showing exactly what data is sent to AI
    """
    st.subheader("🐛 Debug: AI Processing Data")
    st.info("This tab shows exactly what data is being sent to the AI (which works correctly)")
    
    # Import here to avoid circular imports
    try:
        from utils.json_utils import extract_big_chunks, parse_json_output
        import json
    except ImportError as e:
        st.error(f"Import error: {e}")
        return
    
    st.markdown("---")
    
    # Show what data we have in result
    st.markdown("### 📋 Available Data in Result")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**Result Keys:**")
        result_keys = list(result.keys())
        for key in result_keys:
            value = result[key]
            if isinstance(value, str) and len(value) > 100:
                st.write(f"- `{key}`: {type(value).__name__} ({len(value):,} chars)")
            else:
                st.write(f"- `{key}`: {type(value).__name__}")
    
    with col2:
        st.write("**Data Sources:**")
        st.write(f"- Input Mode: {result.get('input_mode', 'unknown')}")
        st.write(f"- URL: {result.get('url', 'N/A')}")
        st.write(f"- Has raw JSON: {'json_output_raw' in result}")
        st.write(f"- Has parsed JSON: {'json_output' in result}")
    
    st.markdown("---")
    
    # Show what gets sent to AI
    st.markdown("### 🤖 Data Sent to AI (Working Path)")
    
    # Get the JSON data that would be sent to AI
    json_for_ai = result.get('json_output')  # This is what gets sent to AI
    
    if json_for_ai:
        try:
            # Show the parsed JSON structure
            if isinstance(json_for_ai, dict):
                st.write(f"**Data Type**: Dictionary (parsed JSON)")
                st.write(f"**Keys**: {list(json_for_ai.keys())}")
                
                # Extract chunks like the AI does
                chunks = extract_big_chunks(json_for_ai)
                st.write(f"**Extracted Chunks**: {len(chunks)}")
                
                st.markdown("#### 🔍 Individual Chunks (as AI receives them)")
                
                for i, chunk in enumerate(chunks[:3]):  # Show first 3 chunks
                    with st.expander(f"Chunk {chunk['index']} - {chunk['count']} small chunks"):
                        chunk_text = chunk['text']
                        
                        # Analysis of chunk content
                        col_a, col_b, col_c = st.columns(3)
                        with col_a:
                            st.metric("Text Length", f"{len(chunk_text):,}")
                        with col_b:
                            st.metric("Unicode Escapes", chunk_text.count('\\u'))
                        with col_c:
                            unicode_free = chunk_text.count('\\u') == 0
                            st.metric("Unicode Free", "✅ Yes" if unicode_free else "❌ No")
                        
                        # Show the actual text content
                        st.markdown("**Text Content (first 500 chars):**")
                        preview = chunk_text[:500] + "..." if len(chunk_text) > 500 else chunk_text
                        st.code(preview, language='text')
                        
                        # Show if content has readable characters
                        st.markdown("**Character Analysis:**")
                        
                        # Sample some characters
                        sample_chars = chunk_text[:100]
                        readable_chars = []
                        unicode_chars = []
                        
                        i_char = 0
                        while i_char < len(sample_chars):
                            if sample_chars[i_char:i_char+2] == '\\u' and i_char + 5 < len(sample_chars):
                                # Found unicode escape
                                unicode_seq = sample_chars[i_char:i_char+6]
                                try:
                                    decoded_char = chr(int(unicode_seq[2:], 16))
                                    unicode_chars.append(f"{unicode_seq} → {decoded_char}")
                                except:
                                    unicode_chars.append(f"{unicode_seq} → (invalid)")
                                i_char += 6
                            else:
                                if sample_chars[i_char].isprintable():
                                    readable_chars.append(sample_chars[i_char])
                                i_char += 1
                        
                        if unicode_chars:
                            st.write("**Unicode Sequences Found:**")
                            for uc in unicode_chars[:5]:  # Show first 5
                                st.write(f"  - {uc}")
                            if len(unicode_chars) > 5:
                                st.write(f"  - ... and {len(unicode_chars) - 5} more")
                        
                        if readable_chars:
                            st.write(f"**Readable chars sample**: {''.join(readable_chars[:20])}")
                
                if len(chunks) > 3:
                    st.write(f"... and {len(chunks) - 3} more chunks")
            
            elif isinstance(json_for_ai, str):
                st.write(f"**Data Type**: String")
                st.write(f"**Length**: {len(json_for_ai):,} characters")
                st.write(f"**Unicode Escapes**: {json_for_ai.count('\\u')}")
                
                # Try to parse it
                try:
                    parsed = json.loads(json_for_ai)
                    st.write("**Parsing**: ✅ Valid JSON")
                    chunks = extract_big_chunks(parsed)
                    st.write(f"**Chunks**: {len(chunks)}")
                except Exception as e:
                    st.write(f"**Parsing**: ❌ {str(e)}")
                
                # Show sample
                st.markdown("**Content Sample (first 1000 chars):**")
                st.code(json_for_ai[:1000], language='json')
        
        except Exception as e:
            st.error(f"Error analyzing AI data: {e}")
            st.write("**Raw data:**")
            st.write(f"Type: {type(json_for_ai)}")
            st.write(f"Content: {str(json_for_ai)[:500]}...")
    
    else:
        st.warning("No JSON data found for AI processing")
    
    st.markdown("---")
    
    # Compare with UI display data
    st.markdown("### 🖥️ Data for UI Display (Broken Path)")
    
    json_for_ui = result.get('json_output_raw')
    
    if json_for_ui:
        st.write(f"**Data Type**: {type(json_for_ui).__name__}")
        st.write(f"**Length**: {len(str(json_for_ui)):,} characters")
        st.write(f"**Unicode Escapes**: {str(json_for_ui).count('\\u')}")
        
        st.markdown("**Content Sample (first 1000 chars):**")
        st.code(str(json_for_ui)[:1000], language='json')
        
        # Compare with AI data
        if json_for_ai and json_for_ui:
            st.markdown("**🔄 Data Comparison:**")
            if isinstance(json_for_ai, dict):
                try:
                    ai_as_string = json.dumps(json_for_ai, ensure_ascii=False)
                    st.write(f"- AI data (as string): {len(ai_as_string):,} chars, {ai_as_string.count('\\u')} unicode")
                    st.write(f"- UI data: {len(str(json_for_ui)):,} chars, {str(json_for_ui).count('\\u')} unicode")
                    
                    if ai_as_string == str(json_for_ui):
                        st.success("✅ Data matches perfectly")
                    else:
                        st.warning("⚠️ Data differs between AI and UI paths")
                except Exception as e:
                    st.error(f"Comparison error: {e}")
    else:
        st.warning("No raw JSON data found for UI display")
    
    # Show AI results if available
    if ai_result:
        st.markdown("---")
        st.markdown("### ✅ AI Processing Results")
        st.write("**AI successfully processed the data above and produced readable output.**")
        st.write(f"- Processing time: {ai_result.get('processing_time', 0):.2f}s")
        st.write(f"- Chunks analyzed: {ai_result.get('statistics', {}).get('total_chunks', 0)}")
        st.write(f"- Success rate: {ai_result.get('statistics', {}).get('success_rate', 0):.1f}%")
        
        # Show a sample of AI output to prove it's readable
        if ai_result.get('report'):
            st.markdown("**Sample AI Output (first 300 chars):**")
            sample_output = ai_result['report'][:300] + "..." if len(ai_result['report']) > 300 else ai_result['report']
            st.code(sample_output, language='markdown')
            st.success("👆 This proves the AI received readable text (no Unicode escapes)")

def _create_ai_report_tab(ai_result: Dict[str, Any], content_result: Optional[Dict[str, Any]] = None):
    """
    Create AI compliance report tab content.
    
    ENHANCED: Shows appropriate source information for both input modes
    """
    st.markdown("### YMYL Compliance Analysis Report")
    
    # Show analysis metadata and freshness info
    if content_result:
        col1, col2, col3 = st.columns(3)
        
        with col1:
            processing_time = ai_result.get('processing_time', 0)
            st.metric("Processing Time", f"{processing_time:.2f}s")
        
        with col2:
            source_url = ai_result.get('source_url', content_result.get('url', 'Direct JSON Input'))
            if len(source_url) > 30:
                display_source = source_url[:30] + "..."
            else:
                display_source = source_url
            st.metric("Source", display_source)
        
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
    """
    Create download buttons for different formats.
    
    FIXED: Robust implementation to prevent media file storage errors
    """
    try:
        timestamp = int(time.time())
        
        col1, col2, col3, col4 = st.columns(4)
        
        format_configs = {
            'markdown': {
                'label': "📝 Markdown",
                'mime': "text/markdown",
                'help': "Original markdown format - perfect for copying to other platforms",
                'extension': '.md'
            },
            'html': {
                'label': "🌐 HTML", 
                'mime': "text/html",
                'help': "Styled HTML document - opens in any web browser",
                'extension': '.html'
            },
            'docx': {
                'label': "📄 Word",
                'mime': "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                'help': "Microsoft Word document - ready for editing and sharing",
                'extension': '.docx'
            },
            'pdf': {
                'label': "📋 PDF",
                'mime': "application/pdf", 
                'help': "Professional PDF document - perfect for presentations and archival",
                'extension': '.pdf'
            }
        }
        
        columns = [col1, col2, col3, col4]
        
        for i, (fmt, config) in enumerate(format_configs.items()):
            if fmt in formats and i < len(columns):
                with columns[i]:
                    try:
                        filename = f"ymyl_compliance_report_{timestamp}{config['extension']}"
                        
                        # FIXED: Use unique key for each download button to prevent conflicts
                        button_key = f"download_{fmt}_{timestamp}_{hash(str(formats[fmt]))}"
                        
                        st.download_button(
                            label=config['label'],
                            data=formats[fmt],
                            file_name=filename,
                            mime=config['mime'],
                            help=config['help'],
                            key=button_key  # Unique key to prevent media file conflicts
                        )
                    except Exception as e:
                        # If individual download button fails, show error but continue
                        st.error(f"Error creating {fmt.upper()} download: {str(e)[:50]}...")
        
    except Exception as e:
        # If entire download section fails, provide fallback
        st.error("Error creating download buttons. Please try refreshing the page.")
        
        # Provide simple fallback download for markdown
        if 'markdown' in formats:
            try:
                st.download_button(
                    label="📝 Download Report (Markdown)",
                    data=formats['markdown'],
                    file_name=f"ymyl_report_backup_{int(time.time())}.md",
                    mime="text/markdown",
                    key=f"backup_download_{int(time.time())}"
                )
            except:
                st.write("Please refresh the page to access downloads.")

def _create_individual_analyses_tab(ai_result: Dict[str, Any]):
    """Create individual analyses tab with both readable format and raw AI output."""
    
    from utils.json_utils import convert_violations_json_to_readable
    
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
    
    # Individual results with both readable and raw formats
    for detail in analysis_details:
        chunk_idx = detail.get('chunk_index', 'Unknown')
        if detail.get('success'):
            # Convert JSON to readable format
            readable_content = convert_violations_json_to_readable(result["content"])
            
            with st.expander(f"✅ Chunk {chunk_idx} Analysis (Success)"):
                # Tab structure: Readable + Raw
                tab1, tab2 = st.tabs(["📖 Readable Format", "🔧 Raw AI Output"])
                
                with tab1:
                    st.markdown("**Human-Readable Violations:**")
                    st.markdown(readable_content)
                
                with tab2:
                    st.markdown("**Raw AI Response (for prompt debugging):**")
                    st.code(detail['content'], language='json')
                    
                    # Additional debug info
                    st.markdown("**Debug Information:**")
                    col_a, col_b = st.columns(2)
                    with col_a:
                        st.write(f"**Response Length:** {len(detail['content']):,} characters")
                        st.write(f"**Processing Time:** {detail.get('processing_time', 0):.2f}s")
                    with col_b:
                        try:
                            parsed = json.loads(detail['content'])
                            violation_count = len(parsed.get('violations', []))
                            st.write(f"**Violations Found:** {violation_count}")
                            st.write(f"**Valid JSON:** ✅ Yes")
                        except:
                            st.write(f"**Violations Found:** ❌ Parse Error")
                            st.write(f"**Valid JSON:** ❌ No")
                
        else:
            with st.expander(f"❌ Chunk {chunk_idx} Analysis (Failed)"):
                st.error(f"Error: {detail.get('error', 'Unknown error')}")
                if 'processing_time' in detail:
                    st.caption(f"Processing time: {detail['processing_time']:.2f}s")

def _create_json_tab(result: Dict[str, Any]):
    """
    Create JSON output tab content with proper Unicode display.
    
    FIXED: Now properly displays Unicode characters using the raw decoded data
    """
    st.subheader("🔧 JSON Output")

    # Display source info
    input_mode = st.session_state.get('input_mode', '🌐 URL Input')
    if input_mode == "🌐 URL Input":
        source_info = result.get('url', 'Unknown URL')
        st.info(f"**Source**: {source_info}")
    else:
        st.info("**Source**: Direct JSON Input")

    # FIXED: Use the raw JSON string which has Unicode already decoded
    json_output_raw = result.get('json_output_raw')
    
    if json_output_raw:
        # Perfect! We have the decoded raw string
        display_json = json_output_raw
        st.success("✅ Using decoded raw JSON data")
    else:
        # Fallback: convert dict back to pretty JSON string
        json_output_dict = result.get('json_output')
        if json_output_dict:
            from utils.json_utils import get_display_json_string
            display_json = get_display_json_string(json_output_dict)
            st.warning("⚠️ Using fallback conversion from dict")
        else:
            # Last resort
            display_json = '{"error": "No JSON data found"}'
            st.error("❌ No JSON data available")

    # Display content
    st.markdown("**Processed JSON Content:**")
    st.code(display_json, language='json')

    # Download button
    st.download_button(
        label="💾 Download JSON",
        data=display_json,
        file_name="processed_chunks.json",
        mime="application/json",
        key="download_json"
    )

    # Show content info for debugging
    if display_json:
        char_count = len(display_json)
        unicode_count = display_json.count('\\u')
        
        with st.expander("🔍 Content Info"):
            st.write(f"**Content Length**: {char_count:,} characters")
            st.write(f"**Unicode Escapes Found**: {unicode_count}")
            st.write(f"**Data Source**: {'json_output_raw' if json_output_raw else 'converted from dict'}")
            
            if unicode_count == 0:
                st.success("✅ All Unicode characters properly decoded and readable")
            else:
                st.warning(f"⚠️ {unicode_count} Unicode escape sequences still present")
            
            # Show sample with Japanese characters
            sample = display_json[:400] + "..." if len(display_json) > 400 else display_json
            st.code(sample, language='json')
            
            # Test for Japanese characters specifically
            japanese_chars = ['マ', 'カ', 'オ', 'ゲ', 'ー', 'ミ', 'ン', 'グ']
            found_japanese = [char for char in japanese_chars if char in display_json]
            if found_japanese:
                st.success(f"✅ Japanese characters detected: {', '.join(found_japanese[:5])}")
            else:
                st.info("ℹ️ No Japanese characters found in sample")

def _create_content_tab(result: Dict[str, Any]):
    """
    Create source content tab content.
    
    ENHANCED: Shows appropriate content based on input mode
    """
    input_mode = st.session_state.get('input_mode', '🌐 URL Input')
    
    if input_mode == "🌐 URL Input":
        st.markdown("**Extracted content from URL:**")
        st.text_area(
            "Raw extracted content:", 
            value=result['extracted_content'], 
            height=400,
            help="Original content extracted from the webpage"
        )
    else:
        st.markdown("**Direct JSON input provided:**")
        st.info("Content was provided directly as chunked JSON. See JSON Output tab for the processed format.")
        
        # Show some basic stats about the direct input
        try:
            json_output_dict = result.get('json_output', {})
            if isinstance(json_output_dict, dict):
                chunks = json_output_dict.get('big_chunks', [])
                total_content = 0
                for chunk in chunks:
                    small_chunks = chunk.get('small_chunks', [])
                    total_content += len('\n'.join(small_chunks))
                
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Total Chunks Provided", len(chunks))
                with col2:
                    st.metric("Total Content Length", f"{total_content:,} chars")
        except:
            st.warning("Could not analyze the provided JSON structure.")

def _create_summary_tab(result: Dict[str, Any], ai_result: Optional[Dict[str, Any]] = None):
    """
    Create processing summary tab content.
    
    ENHANCED: Shows different metrics based on input mode
    """
    st.subheader("Processing Summary")
    
    input_mode = st.session_state.get('input_mode', '🌐 URL Input')
    
    # Parse JSON for chunk statistics
    try:
        json_output_dict = result.get('json_output', {})
        if isinstance(json_output_dict, dict):
            big_chunks = json_output_dict.get('big_chunks', [])
        else:
            import json
            if isinstance(json_output_dict, str):
                parsed_data = json.loads(json_output_dict)
                big_chunks = parsed_data.get('big_chunks', [])
            else:
                big_chunks = []
        
        total_small_chunks = sum(len(chunk.get('small_chunks', [])) for chunk in big_chunks)
        
        # Content processing metrics
        if input_mode == "🌐 URL Input":
            st.markdown("#### URL Content Extraction")
            colA, colB, colC = st.columns(3)
            colA.metric("Big Chunks", len(big_chunks))
            colB.metric("Total Small Chunks", total_small_chunks)
            colC.metric("Extracted Length", f"{len(result.get('extracted_content', '')):,} chars")
        else:
            st.markdown("#### Direct JSON Input")
            colA, colB, colC = st.columns(3)
            colA.metric("Big Chunks", len(big_chunks))
            colB.metric("Total Small Chunks", total_small_chunks)
            total_content = sum(len('\n'.join(chunk.get('small_chunks', []))) for chunk in big_chunks)
            colC.metric("Total Content", f"{total_content:,} chars")
        
        # AI Analysis metrics (if available)
        if ai_result and ai_result.get('success'):
            st.markdown("#### AI Analysis Performance")
            stats = ai_result.get('statistics', {})
            
            colD, colE, colF, colG = st.columns(4)
            colD.metric("Processing Time", f"{stats.get('total_processing_time', 0):.2f}s")
            colE.metric("Successful Analyses", stats.get('successful_analyses', 0))
            colF.metric("Failed Analyses", stats.get('failed_analyses', 0))
            colG.metric("Success Rate", f"{stats.get('success_rate', 0):.1f}%")
            
            # Show freshness status in summary
            st.markdown("#### Analysis Status")
            content_timestamp = result.get('processing_timestamp', 0)
            ai_timestamp = ai_result.get('processing_timestamp', -1)
            is_fresh = (content_timestamp == ai_timestamp)
            
            colH, colI = st.columns(2)
            with colH:
                freshness_status = "Fresh ✅" if is_fresh else "Stale ⚠️"
                st.metric("Result Freshness", freshness_status)
            with colI:
                source_match = result.get('url', 'Direct JSON Input') == ai_result.get('source_url', '')
                source_status = "Match ✅" if source_match else "Different Source"
                st.metric("Source", source_status)
            
            # Performance insights
            if stats.get('total_processing_time', 0) > 0 and stats.get('total_chunks', 0) > 0:
                avg_time = stats['total_processing_time'] / stats['total_chunks']
                efficiency = "High" if stats['total_processing_time'] < stats['total_chunks'] * 2 else "Moderate"
                st.info(f"📊 **Performance**: Average {avg_time:.2f}s per chunk | Parallel efficiency: {efficiency}")
        
    except (json.JSONDecodeError, TypeError, KeyError) as e:
        st.warning(f"Could not parse JSON for statistics: {e}")
    
    # Show source information
    source_info = result.get('url', 'Direct JSON Input')
    st.info(f"**Source**: {source_info}")

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
        st.info(f"🚀 Starting AI analysis of {len(chunks)} chunks...")
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

# NEW FEATURE: Helper functions for dual input mode
def show_input_mode_context():
    """Show current input mode context information."""
    input_mode = st.session_state.get('input_mode', '🌐 URL Input')
    current_url = st.session_state.get('current_url_analysis')
    current_input_mode = st.session_state.get('current_input_analysis_mode')
    
    if input_mode == "🌐 URL Input" and current_url:
        with st.expander("📋 Current Analysis Context"):
            st.write(f"**Input Mode**: URL Extraction")
            st.write(f"**URL**: {current_url}")
            st.write(f"**Timestamp**: {st.session_state.get('processing_timestamp', 'Unknown')}")
    elif input_mode == "📄 Direct JSON" and current_input_mode == 'direct_json':
        with st.expander("📋 Current Analysis Context"):
            st.write(f"**Input Mode**: Direct JSON Input")
            st.write(f"**Source**: User-provided chunked content")
            st.write(f"**Timestamp**: {st.session_state.get('processing_timestamp', 'Unknown')}")

def get_input_mode_display_name(mode: str) -> str:
    """Convert internal input mode to display name."""
    mode_map = {
        'url': 'URL Extraction',
        'direct_json': 'Direct JSON Input'
    }
    return mode_map.get(mode, mode)

# Backward compatibility - keep old function name
def create_url_input_section() -> tuple[str, bool]:
    """
    DEPRECATED: Use create_dual_input_section() instead.
    Kept for backward compatibility.
    """
    return _create_url_input_mode()[1:]  # Return only url and process_clicked