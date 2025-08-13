#!/usr/bin/env python3
"""
UI Components for YMYL Audit Tool
Reusable Streamlit UI components for the application interface.
UPDATED: Simplified export to Word-only format with Google Docs compatibility
REMOVED: HTML, PDF, and multi-format export options
"""
import streamlit_js_eval as st_js
import streamlit as st
import time
import re
from datetime import datetime
from typing import Dict, Any, Optional, List, Callable, Tuple
from config.settings import DEFAULT_TIMEZONE
from utils.logging_utils import log_with_timestamp
from utils.json_utils import get_display_json_string
from exporters.word_exporter import WordExporter  # UPDATED: Only Word export
def create_page_header():
    """Create the main page header with title and description."""
    st.title("🕵 YMYL Audit Tool")
    st.markdown("**Automatically extract content from websites, generate JSON chunks, and perform YMYL compliance analysis**")
    st.markdown("---")
def create_user_friendly_log_recap():
    """Create a consolidated, user-friendly log recap for normal users."""
    # Check if we have any processing history in session state
    log_entries = []
    # Collect URL processing logs
    if 'latest_result' in st.session_state:
        result = st.session_state['latest_result']
        if result.get('success'):
            input_mode = result.get('input_mode', 'url')
            if input_mode == 'url':
                log_entries.append({
                    'step': 'Content Extraction',
                    'status': 'completed',
                    'details': f"Successfully extracted content from {result.get('url', 'URL')}",
                    'data': f"{len(result.get('extracted_content', '')):,} characters extracted"
                })
            else:
                log_entries.append({
                    'step': 'JSON Input Processing', 
                    'status': 'completed',
                    'details': "Direct JSON content validated and processed",
                    'data': "Content ready for analysis"
                })
    # Collect AI analysis logs
    if 'ai_analysis_result' in st.session_state:
        ai_result = st.session_state['ai_analysis_result']
        if ai_result.get('success'):
            stats = ai_result.get('statistics', {})
            processing_time = ai_result.get('processing_time', 0)
            log_entries.append({
                'step': 'AI Compliance Analysis',
                'status': 'completed', 
                'details': f"Analyzed {stats.get('total_chunks', 0)} content sections",
                'data': f"Completed in {processing_time:.1f} seconds with {stats.get('success_rate', 0):.0f}% success rate"
            })
    # Display the recap
    if log_entries:
        st.subheader("📋 Processing Summary")
        st.info("Here's what happened during your analysis:")
        for i, entry in enumerate(log_entries, 1):
            status_icon = "✅" if entry['status'] == 'completed' else "⏳"
            with st.expander(f"{status_icon} Step {i}: {entry['step']}", expanded=True):
                st.write(f"**What happened:** {entry['details']}")
                st.write(f"**Result:** {entry['data']}")
                # Add helpful next steps
                if entry['step'] == 'Content Extraction':
                    st.caption("💡 Next: Run AI analysis to check for YMYL compliance issues")
                elif entry['step'] == 'AI Compliance Analysis':
                    st.caption("💡 View your report in the 'AI Compliance Report' tab above")
    else:
        st.info("🚀 Ready to start! Choose your input method above and begin processing.")
def track_user_error(error_type, error_message, context=""):
    """Track errors for user-friendly display later."""
    if 'user_error_history' not in st.session_state:
        st.session_state['user_error_history'] = []
    error_entry = {
        'timestamp': datetime.now().strftime('%H:%M:%S'),
        'type': error_type,
        'message': error_message,
        'context': context,
        'user_friendly': _make_error_user_friendly(error_type, error_message)
    }
    st.session_state['user_error_history'].append(error_entry)
    # Keep only last 5 errors
    if len(st.session_state['user_error_history']) > 5:
        st.session_state['user_error_history'].pop(0)
def _make_error_user_friendly(error_type, error_message):
    """Convert technical errors to user-friendly messages."""
    friendly_messages = {
        'timeout': "The website took too long to respond. Try again or check if the URL is working.",
        'connection': "Couldn't connect to the website. Check your internet connection and the URL.",
        'json': "The content format isn't quite right. Please check your JSON input.",
        'api': "There was an issue with the AI analysis service. Please try again in a moment.",
        'parsing': "Had trouble understanding the content format. Please verify your input.",
    }
    # Try to match error type
    for key, friendly_msg in friendly_messages.items():
        if key in error_type.lower() or key in error_message.lower():
            return friendly_msg
    # Default friendly message
    return "Something went wrong, but you can try again. If the problem continues, the issue might be temporary."            
def create_simple_status_updater():
    """Create a simple status updater that shows one clear message at a time."""
    if 'simple_status_container' not in st.session_state:
        st.session_state['simple_status_container'] = st.empty()
    def update_simple_status(message, status_type="info"):
        """Update the simple status display."""
        container = st.session_state['simple_status_container']
        if status_type == "info":
            container.info(f"🔄 {message}")
        elif status_type == "success":
            container.success(f"✅ {message}")
        elif status_type == "error":
            container.error(f"❌ {message}")
        elif status_type == "warning":
            container.warning(f"⚠️ {message}")
    return update_simple_status
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
    # Session state management options
    with st.sidebar.expander("🧹 Session Management"):
        if st.button("Clear All Analysis Data", help="Clear all stored analysis results"):
            keys_to_clear = [k for k in st.session_state.keys() if k.startswith(('latest_', 'ai_', 'current_url', 'processing_', 'input_'))]
            for key in keys_to_clear:
                del st.session_state[key]
            st.success(f"Cleared {len(keys_to_clear)} session keys")
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
    """Create the 'How it works' information section with user guidance."""
    st.subheader("ℹ️ How it works")
    st.markdown("""
1. **Choose Input**: Paste URL OR provide chunked content directly.
2. **Extract Content**: Click on "🚀 Process URL" or "Validate Chunked content" to start content extraction.
3. **YMYL Analysis**: Click on "Run AI Analysis" to start the audit.
4. **Download Report**: Get a perfectly formatted Word document that imports cleanly into Google Docs.
""")
def create_dual_input_section() -> Tuple[str, str, bool]:
    """
    Create dual input section with URL/Direct JSON toggle.
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
    # Show current analysis context if available AND not currently processing
    current_url = st.session_state.get('current_url_analysis')
    is_processing = st.session_state.get('is_processing', False)
    if current_url and not is_processing:
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
    """Create direct JSON input interface."""
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
    # Process button
    col1, col2 = st.columns([2, 1])
    with col1:
        st.markdown("")  # Spacing
    with col2:
        process_clicked = st.button(
            "✨ Validate Chunked content", 
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
        # Limit log lines to prevent memory issues
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
        # Limit milestone history
        if len(milestones) > 10:
            milestones.pop(0)
        log_area.markdown("\n".join(milestones))
    return log_area, update_progress
def create_ai_analysis_section(api_key: Optional[str], json_output: Any, source_result: Optional[Dict] = None) -> bool:
    """
    Create AI analysis section with processing button.
    Works with both URL and direct JSON input modes
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
    # Show different messaging based on input mode
    input_mode = st.session_state.get('input_mode', '🌐 URL Input')
    st.markdown("### ✨ AI Compliance Analysis")
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
            with col2:
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
            with col1:
                button_label = "✨ Run AI Analysis"
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
    Works with both URL and direct JSON inputs
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
    Create results display tabs
    Shows appropriate context for URL vs Direct JSON inputs
    """
    # Show freshness indicator before tabs
    if ai_result and ai_result.get('success'):
        create_content_freshness_indicator(result, ai_result)
    if ai_result and ai_result.get('success'):
        # With AI analysis results
        tab1, tab2, tab3, tab4, tab5, = st.tabs([
            "🎯 AI Compliance Report", 
            "📊 Individual Analyses", 
            "🔧 JSON Output", 
            "📄 Source Content", 
            "📈 Summary",
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
        tab1, tab2, tab3, = st.tabs([
            "🎯 JSON Output", 
            "📄 Source Content", 
            "📈 Summary",
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
    UPDATED: Simplified to Word-only export with Google Docs instructions
    """
    st.markdown("### YMYL Compliance Analysis Report")
    ai_report = ai_result['report']
    # Word download section
    st.markdown("#### 📄 Download Report")
    try:
        # Generate Word document
        word_exporter = WordExporter()
        word_bytes = word_exporter.convert(ai_report, "YMYL Compliance Audit Report")
        # Download button
        timestamp = int(time.time())
        filename = f"ymyl_compliance_report_{timestamp}.docx"
        # Centered download button
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.download_button(
                label="📄 Download Word Document",
                data=word_bytes,
                file_name=filename,
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                help="Downloads Word document that imports perfectly into Google Docs",
                type="primary",
                use_container_width=True
            )
        st.success("✅ **Ready to download!** Imports cleanly into Google Docs with perfect formatting.")
        # Google Docs instructions
        _add_google_docs_instructions()
        # Optional: Copy to clipboard functionality
        _add_copy_functionality(ai_report)
    except Exception as e:
        st.error(f"Error creating Word document: {e}")
        # Fallback to markdown
        timestamp = int(time.time())
        st.download_button(
            label="📝 Download Report (Markdown Fallback)",
            data=ai_report,
            file_name=f"ymyl_compliance_report_{timestamp}.md",
            mime="text/markdown"
        )
    # Keep existing view options
    with st.expander("📖 View Formatted Report"):
        st.markdown(ai_report)
    with st.expander("📝 View Raw Markdown"):
        st.code(ai_report, language='markdown')
def _add_google_docs_instructions():
    """Add helpful instructions for Google Docs import."""
    with st.expander("💡 How to use with Google Docs"):
        st.markdown("""
        **Perfect Google Docs Integration:**
        1. **Download** the Word document using the button above
        2. **Open** Google Docs in your browser (docs.google.com)
        3. **Click** File → Import → Upload
        4. **Select** the downloaded Word file
        5. **Enjoy** perfectly formatted report in Google Docs!
        ✅ **All formatting preserved:** Headers, bullet points, severity colors, and styling will look exactly right.
        **Why this works better than other formats:**
        - 🎯 Uses Word's built-in styles that Google Docs recognizes
        - 🎨 Severity indicators show as colored text labels like `[CRITICAL]` in red
        - 📝 No raw markdown syntax - everything is properly formatted
        - 🔄 Easy to edit and collaborate on in Google Docs
        """)
def _add_copy_functionality(ai_report: str):
    """Add copy to clipboard functionality."""
    with st.expander("📋 Copy Report Text"):
        st.markdown("**Copy formatted text for pasting into other applications:**")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("📋 Copy Report Text", key="copy_report_button"):
                try:
                    # Convert markdown to clean text for copying
                    clean_text = _convert_markdown_to_clean_text(ai_report)
                    # Try to copy to clipboard
                    try:
                        # Escape the text properly for JavaScript
                        escaped_text = clean_text.replace('\\', '\\\\').replace('`', '\\`').replace('\n', '\\n').replace('\r', '\\r')
                        st_js.st_js_eval(f"navigator.clipboard.writeText(`{escaped_text}`)")
                        st.success("✅ Report text copied to clipboard!")
                    except Exception as e:
                        # Fallback: show text area for manual copy
                        st.info("Copy this text manually:")
                        st.text_area(
                            "Report text:",
                            value=clean_text,
                            height=150,
                            key="manual_copy_text",
                            help="Select all text and copy"
                        )
                except Exception as e:
                    st.error("Copy failed - showing text to copy manually:")
                    st.text_area(
                        "Copy this text:",
                        value=ai_report,
                        height=150,
                        key="manual_copy_fallback"
                    )
        with col2:
            st.info("**💡 Tip:** This creates clean, formatted text perfect for pasting into emails, documents, or other applications.")
def _convert_markdown_to_clean_text(markdown_content: str) -> str:
    """Convert markdown to clean, readable text for copying."""
    import re
    try:
        lines = markdown_content.split('\n')
        formatted_lines = []
        for line in lines:
            if not line.strip():
                formatted_lines.append('')
                continue
            # Main title (# Title)
            if line.startswith('# '):
                title = line[2:].strip()
                formatted_lines.append(f"{title}")
                formatted_lines.append('=' * len(title))
            # Section headers (## Section)
            elif line.startswith('## '):
                header = line[3:].strip()
                formatted_lines.append('')
                formatted_lines.append(f"{header}")
                formatted_lines.append('-' * len(header))
            # Subsection headers (### Subsection)
            elif line.startswith('### '):
                subheader = line[4:].strip()
                formatted_lines.append('')
                formatted_lines.append(f"{subheader}")
            # Horizontal rules (---)
            elif line.startswith('---'):
                formatted_lines.append('')
                formatted_lines.append('-' * 60)
                formatted_lines.append('')
            # Bold text (**text**)
            elif line.startswith('**') and line.endswith('**'):
                bold_text = line[2:-2].strip()
                formatted_lines.append('')
                formatted_lines.append(f"{bold_text.upper()}")
            # Bullet points (- item)
            elif line.startswith('- '):
                bullet_text = line[2:].strip()
                formatted_lines.append(f"* {bullet_text}") # Changed bullet point character
            # Violations with severity (replace emojis with text)
            elif any(emoji in line for emoji in ['🔴', '🟠', '🟡', '🔵']):
                formatted_line = _format_severity_for_text(line)
                formatted_lines.append(f"    {formatted_line}")
            # Regular paragraphs
            else:
                # Clean markdown syntax
                clean_line = _clean_markdown_syntax(line)
                if clean_line.strip():
                    formatted_lines.append(clean_line)
        # Join and clean up excessive whitespace
        result = '\n'.join(formatted_lines)
        result = re.sub(r'\n{3,}', '\n\n', result) # Adjusted for consistent newlines
        return result.strip()
    except Exception as e:
        # Fallback: basic cleanup
        return _basic_markdown_cleanup(markdown_content)
def _format_severity_for_text(line: str) -> str:
    """Format severity lines for plain text."""
    severity_replacements = {
        '🔴': 'CRITICAL:',
        '🟠': 'HIGH:',
        '🟡': 'MEDIUM:',
        '🔵': 'LOW:',
        '✅': 'OK',
        '❌': 'FAIL',
        '⚠️': 'WARN'
    }
    formatted_line = line
    for emoji, replacement in severity_replacements.items():
        formatted_line = formatted_line.replace(emoji, replacement)
    # Clean up any remaining markdown
    formatted_line = _clean_markdown_syntax(formatted_line)
    return formatted_line
def _clean_markdown_syntax(text: str) -> str:
    """Remove markdown syntax while preserving formatting intent."""
    import re
    # Remove bold/italic markers but keep the text
    text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)  # **bold** → bold
    text = re.sub(r'\*(.*?)\*', r'\1', text)      # *italic* → italic
    # Remove link syntax but keep the text
    text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)  # [text](url) → text
    # Remove code syntax
    text = re.sub(r'`([^`]+)`', r'\1', text)  # `code` → code
    # Clean up extra spaces
    text = re.sub(r'\s+', ' ', text).strip()
    return text
def _basic_markdown_cleanup(markdown_content: str) -> str:
    """Basic fallback cleanup if main formatting fails."""
    import re
    try:
        content = markdown_content
        # Convert headers
        content = re.sub(r'^# (.+)$', r'\1\n' + '=' * 50, content, flags=re.MULTILINE)
        content = re.sub(r'^## (.+)$', r'\n\1\n' + '-' * 30, content, flags=re.MULTILINE)
        content = re.sub(r'^### (.+)$', r'\n\1', content, flags=re.MULTILINE)
        # Convert bullets
        content = re.sub(r'^- (.+)', r'* \1', content, flags=re.MULTILINE) # Changed bullet point character
        # Replace emojis
        content = content.replace('🔴', 'CRITICAL:')
        content = content.replace('🟠', 'HIGH:')
        content = content.replace('🟡', 'MEDIUM:')
        content = content.replace('🔵', 'LOW:')
        content = content.replace('✅', 'OK')
        content = content.replace('❌', 'FAIL')
        # Remove remaining markdown
        content = re.sub(r'\*\*(.*?)\*\*', r'\1', content)
        content = re.sub(r'\*(.*?)\*', r'\1', content)
        content = re.sub(r'`([^`]+)`', r'\1', content)
        # Clean up spacing
        content = re.sub(r'\n{3,}', '\n\n', content) # Adjusted for consistent newlines
        return content.strip()
    except Exception as e:
        return markdown_content
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
            readable_content = convert_violations_json_to_readable(detail["content"])
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
                            import json
                            parsed = json.loads(detail['content'])
                            violation_count = len(parsed.get('violations', []))
                            st.write(f"**Violations Found:** {violation_count}")
                            st.write(f"**Valid JSON:** OK") # Changed emoji
                        except:
                            st.write(f"**Violations Found:** Parse Error") # Changed emoji
                            st.write(f"**Valid JSON:** No") # Changed emoji
        else:
            with st.expander(f"FAIL Chunk {chunk_idx} Analysis (Failed)"): # Changed emoji
                st.error(f"Error: {detail.get('error', 'Unknown error')}")
                if 'processing_time' in detail:
                    st.caption(f"Processing time: {detail['processing_time']:.2f}s")
def _create_json_tab(result: Dict[str, Any]):
    """
    Create JSON output tab content with proper Unicode display.
    """
    st.subheader("🔧 JSON Output")
    # Display source info
    input_mode = st.session_state.get('input_mode', '🌐 URL Input')
    if input_mode == "🌐 URL Input":
        source_info = result.get('url', 'Unknown URL')
        st.info(f"**Source**: {source_info}")
    else:
        st.info("**Source**: Direct JSON Input")
    # Use the raw JSON string which has Unicode already decoded
    json_output_raw = result.get('json_output_raw')
    if json_output_raw:
        # Perfect! We have the decoded raw string
        display_json = json_output_raw
        st.success("✅ Using decoded raw JSON data") # Kept emoji as it's standard
    else:
        # Fallback: convert dict back to pretty JSON string
        json_output_dict = result.get('json_output')
        if json_output_dict:
            from utils.json_utils import get_display_json_string
            display_json = get_display_json_string(json_output_dict)
            st.warning("⚠️ Using fallback conversion from dict") # Kept emoji as it's standard
        else:
            # Last resort
            display_json = '{"error": "No JSON data found"}'
            st.error("❌ No JSON data available") # Kept emoji as it's standard
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
        with st.expander("🔍 Content Info"): # Kept emoji as it's standard
            st.write(f"**Content Length**: {char_count:,} characters")
            st.write(f"**Unicode Escapes Found**: {unicode_count}")
            st.write(f"**Data Source**: {'json_output_raw' if json_output_raw else 'converted from dict'}")
            if unicode_count == 0:
                st.success("✅ All Unicode characters properly decoded and readable") # Kept emoji as it's standard
            else:
                st.warning(f"⚠️ {unicode_count} Unicode escape sequences still present") # Kept emoji as it's standard
            # Show sample with Japanese characters
            sample = display_json[:400] + "..." if len(display_json) > 400 else display_json
            st.code(sample, language='json')
            # Test for Japanese characters specifically
            japanese_chars = ['マ', 'カ', 'オ', 'ゲ', 'ー', 'ミ', 'ン', 'グ']
            found_japanese = [char for char in japanese_chars if char in display_json]
            if found_japanese:
                st.success(f"✅ Japanese characters detected: {', '.join(found_japanese[:5])}") # Kept emoji as it's standard
            else:
                st.info("ℹ️ No Japanese characters found in sample") # Kept emoji as it's standard
def _create_content_tab(result: Dict[str, Any]):
    """
    Create source content tab content.
    Shows appropriate content based on input mode
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
    Shows different metrics based on input mode
    """
    # Add the user-friendly recap at the top
    create_user_friendly_log_recap()
    st.markdown("---")
    st.markdown("### Technical Details")    
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
                freshness_status = "Fresh OK" if is_fresh else "Stale WARN" # Changed text/emoji
                st.metric("Result Freshness", freshness_status)
            with colI:
                source_match = result.get('url', 'Direct JSON Input') == ai_result.get('source_url', '')
                source_status = "Match OK" if source_match else "Different Source" # Changed text/emoji
                st.metric("Source", source_status)
            # Performance insights
            if stats.get('total_processing_time', 0) > 0 and stats.get('total_chunks', 0) > 0:
                avg_time = stats['total_processing_time'] / stats['total_chunks']
                efficiency = "High" if stats['total_processing_time'] < stats['total_chunks'] * 2 else "Moderate"
                st.info(f"📊 **Performance**: Average {avg_time:.2f}s per chunk | Parallel efficiency: {efficiency}") # Kept emoji as it's standard
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
    st.subheader("🔍 Processing Logs") # Kept emoji as it's standard
    log_container = st.container()
    with log_container:
        st.info(f"🚀 Starting AI analysis of {len(chunks)} chunks...") # Kept emoji as it's standard
        st.write("**Configuration:**")
        col1, col2 = st.columns(2)
        with col1:
            st.write("- Analysis Engine: OpenAI Assistant API")
            st.write("- Processing Mode: Parallel")
        with col2:
            st.write(f"- API Key: {'✅ Valid' if api_key.startswith('sk-') else '❌ Invalid'}") # Kept emoji as it's standard
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
    """Display formatted error message and track for recap."""
    # Track the error
    track_user_error(error_type, error)
    # Show user-friendly version
    if 'user_error_history' in st.session_state and st.session_state['user_error_history']:
        latest_error = st.session_state['user_error_history'][-1]
        user_friendly_msg = latest_error['user_friendly']
        st.error(f"**{error_type}**: {user_friendly_msg}")
        # Show technical details in expander for advanced users
        with st.expander("🔧 Technical Details (for troubleshooting)"): # Kept emoji as it's standard
            st.code(f"Original error: {error}")
            st.caption(f"Time: {latest_error['timestamp']}")
    else:
        # Fallback to original behavior
        st.error(f"**{error_type}**: {error}")
def display_success_message(message: str):
    """Display formatted success message."""
    st.success(message)
def create_info_panel(title: str, content: str, icon: str = "ℹ️"): # Kept emoji as it's standard
    """Create an information panel."""
    st.info(f"{icon} **{title}**: {content}")
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
