#!/usr/bin/env python3
"""
YMYL Audit Tool - Main Application with Authentication

Streamlined main application that orchestrates all components.
This is the clean, refactored version with modular architecture.

NEW FEATURE: Dual input mode - URL extraction OR direct JSON input
SECURITY: Added simple authentication using Streamlit secrets
FIXED: Proper Unicode handling and data flow for UI display
"""
import re
import asyncio
import streamlit as st
import time
from collections import defaultdict
from extractors.content_extractor import ContentExtractor
from processors.chunk_processor import ChunkProcessor
from ai.analysis_engine import AnalysisEngine
from utils.json_utils import parse_json_output, decode_unicode_escapes  # FIXED: Import centralized function
from ui.components import (
    create_page_header,
    create_sidebar_config,
    create_how_it_works_section,
    create_dual_input_section,
    create_debug_logger,
    create_simple_progress_tracker,
    create_simple_status_updater,
    create_ai_analysis_section,
    create_results_tabs,
    create_ai_processing_interface,
    display_error_message,
    display_success_message,
    create_info_panel,
    show_input_mode_context
)
from utils.logging_utils import setup_logger

# Configure Streamlit page
st.set_page_config(
    page_title="YMYL Audit Tool",
    page_icon="🚀",
    layout="wide",
)

# Setup logging
logger = setup_logger(__name__)

# FIXED: Removed duplicate decode_unicode_escapes function - now using centralized version

# =============================================================================
# AUTHENTICATION SYSTEM
# =============================================================================

def check_authentication():
    """
    Simple authentication system using Streamlit secrets.
    Returns True if user is authenticated, False otherwise.
    """
    
    # Initialize session state
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
        st.session_state.username = None
    
    # If already authenticated, show logout option in sidebar
    if st.session_state.authenticated:
        with st.sidebar:
            st.success(f"✅ Logged in as: **{st.session_state.username}**")
            if st.button("🚪 Logout", type="secondary"):
                st.session_state.authenticated = False
                st.session_state.username = None
                # Clear any rate limiting data
                st.success("👋 Logged out successfully!")
                st.rerun()
        return True
    
    # Show login form
    st.markdown("### 🔐 Authentication Required")
    st.info("Please log in to access the YMYL Audit Tool")
    
    # Try to get credentials from secrets
    try:
        username = st.secrets["auth"]["username"]
        password = st.secrets["auth"]["password"]
    except (KeyError, FileNotFoundError):
        st.error("❌ **Configuration Error**: Authentication credentials not found in secrets.")
        
        with st.expander("🔧 Setup Instructions"):
            st.markdown("""
            **To set up authentication, you need to create a secrets file:**
            
            **For local development:**
            1. Create a file `.streamlit/secrets.toml` in your project root
            2. Add your credentials:
            
            ```toml
            [auth]
            username = "your_username"
            password = "your_password"
            ```
            
            **For Streamlit Cloud deployment:**
            1. Go to your app settings
            2. Click "Advanced settings" during deployment (or "Edit secrets" after deployment)
            3. Paste the same content in the Secrets field:
            
            ```toml
            [auth]
            username = "your_username"
            password = "your_password"
            ```
            
            ⚠️ **Important**: Never commit the `secrets.toml` file to your repository!
            """)
        return False
    
    # Login form
    with st.form("login_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        
        with col1:
            input_username = st.text_input("👤 Username", placeholder="Enter your username")
        
        with col2:
            input_password = st.text_input("🔑 Password", type="password", placeholder="Enter your password")
        
        login_button = st.form_submit_button("🚀 Login", type="primary", use_container_width=True)
        
        if login_button:
            if not input_username or not input_password:
                st.error("❌ Please enter both username and password")
                return False
            
            # Check credentials
            if input_username == username and input_password == password:
                st.session_state.authenticated = True
                st.session_state.username = input_username
                st.success(f"✅ Welcome, {input_username}!")
                time.sleep(0.5)  # Brief pause for user feedback
                st.rerun()
            else:
                st.error("❌ Invalid username or password")
                time.sleep(1)  # Simple brute force protection
                return False
    
    return False


# =============================================================================
# ENHANCED DATA HANDLING FOR UNICODE FIX
# =============================================================================

def clear_analysis_session_state():
    """
    Clear all analysis-related session state data.
    
    FIXED: Enhanced cleanup to prevent media file storage errors
    """
    keys_to_clear = [
        "latest_result",
        "ai_analysis_result", 
        "ai_report",
        "ai_stats",
        "analysis_statistics",
        "current_url_analysis",
        "current_input_analysis_mode",
        "processing_start_time",
        "chunk_analysis_results"
    ]
    
    cleared_count = 0
    for key in keys_to_clear:
        if key in st.session_state:
            del st.session_state[key]
            cleared_count += 1
    
    # FIXED: Also clear any download-related keys to prevent media file errors
    download_keys_to_clear = []
    for key in st.session_state.keys():
        if key.startswith('download_') or key.startswith('backup_download_'):
            download_keys_to_clear.append(key)
    
    for key in download_keys_to_clear:
        try:
            del st.session_state[key]
            cleared_count += 1
        except:
            pass  # Ignore errors when clearing download keys
    
    if cleared_count > 0:
        logger.info(f"Cleared {cleared_count} stale session state keys (including download keys)")
    
    return cleared_count

def process_url_workflow(url: str, debug_mode: bool = False) -> dict:
    """
    Process URL through the complete extraction and chunking workflow.
    
    FIXED: Proper data storage for Unicode display
    
    Args:
        url (str): URL to process
        debug_mode (bool): Whether to show detailed logs
        
    Returns:
        dict: Processing results with both raw and parsed JSON
    """
    result = {
        'success': False,
        'url': url,
        'extracted_content': None,
        'json_output_raw': None,      # FIXED: Store raw decoded JSON string
        'json_output': None,          # FIXED: Store parsed JSON dict
        'error': None,
        'input_mode': 'url',
        'processing_timestamp': st.session_state.get('processing_timestamp', None)
    }
    
    try:
        logger.info(f"Starting URL workflow for: {url}")
        
        # Clear stale analysis data when starting new URL processing
        current_url = st.session_state.get('current_url_analysis')
        if current_url != url:
            cleared_count = clear_analysis_session_state()
            st.session_state['current_url_analysis'] = url
            st.session_state['current_input_analysis_mode'] = 'url'
            st.session_state['processing_timestamp'] = st.session_state.get('processing_timestamp', 0) + 1
            
            if cleared_count > 0:
                st.info(f"🧹 Cleared previous analysis data for fresh start ({cleared_count} items)")
        
        # Setup logging based on mode
    if debug_mode:
        log_placeholder = st.empty()
        log_callback = create_debug_logger(log_placeholder)
        use_simple_logging = False
    else:
        # Use simple status for normal users
        simple_status = create_simple_status_updater()
        use_simple_logging = True
        
        # Create a dummy log_callback for backward compatibility
        def log_callback(message):
            # Extract meaningful parts from technical messages
            if "Initializing content extractor" in message:
                simple_status("Connecting to website...", "info")
            elif "Fetching and extracting content" in message:
                simple_status("Reading webpage content...", "info")
            elif "Content extracted" in message:
                simple_status("Content successfully extracted", "success")
            elif "Initializing chunk processor" in message:
                simple_status("Processing content into sections...", "info")
            elif "workflow complete" in message:
                simple_status("Content ready for AI analysis!", "success")
            # For debug mode, we still want to see some messages
            elif debug_mode:
                # Keep original technical logging in debug mode
                pass
        
        # Step 1: Content Extraction
    if use_simple_logging:
        simple_status("Connecting to website...", "info")
    else:
        log_callback("🚀 Initializing content extractor...")
        
    with ContentExtractor() as extractor:
        if use_simple_logging:
            simple_status("Reading webpage content...", "info")
        else:
            log_callback(f"🔍 Fetching and extracting content from: {url}")
        
        # Step 2: Chunk Processing
    if use_simple_logging:
        simple_status("Processing content into sections...", "info")
    else:
        log_callback("🤖 Initializing chunk processor...")
            if not success:
                error_msg = f"Content extraction failed: {error}"
                result['error'] = error_msg
                if use_simple_logging:
                    simple_status("Couldn't extract content from website", "error")
                return result
        
    with ChunkProcessor(log_callback=log_callback if debug_mode else None) as processor:
        if not debug_mode:
            if use_simple_logging:
                with st.status("Processing content... (this may take a moment)"):
                    success, json_output_raw, error = processor.process_content(content)
                    if success:
                        simple_status("Content successfully processed!", "success")
            else:
                with st.status("You are not waiting, Chunk Norris is waiting for you"):
                    success, json_output_raw, error = processor.process_content(content)
        else:
            success, json_output_raw, error = processor.process_content(content)
            
            if not success:
                error_msg = f"Chunk processing failed: {error}"
                result['error'] = error_msg
                if use_simple_logging:
                    simple_status("Problem processing the content", "error")
                return result
            
            # FIXED: Store both raw and parsed versions
            result['json_output_raw'] = json_output_raw  # Raw decoded JSON string for UI
            result['json_output'] = parse_json_output(json_output_raw)  # Parsed dict for AI
            
            if use_simple_logging:
            simple_status("Content ready for AI analysis!", "success")
        else:
            log_callback("🎉 URL workflow complete!")
        
        # Store processing timestamp and mode
        result['processing_timestamp'] = st.session_state.get('processing_timestamp', 0)
        result['success'] = True
        logger.info("URL workflow completed successfully")
        return result
        
    except Exception as e:
        error_msg = f"Unexpected URL workflow error: {str(e)}"
        result['error'] = error_msg
        logger.error(error_msg)
        return result

def process_direct_json_workflow(json_content: str, debug_mode: bool = False) -> dict:
    """
    NEW FEATURE: Process direct JSON input, skipping URL extraction and chunking.
    
    FIXED: Proper Unicode decoding for direct JSON input
    
    Args:
        json_content (str): Direct JSON input from user
        debug_mode (bool): Whether to show detailed logs
        
    Returns:
        dict: Processing results with same structure as URL workflow
    """
    result = {
        'success': False,
        'url': 'Direct JSON Input',
        'extracted_content': 'Content provided directly as chunked JSON',
        'json_output_raw': None,      # FIXED: Store raw JSON string
        'json_output': None,          # FIXED: Store parsed JSON dict
        'error': None,
        'input_mode': 'direct_json',
        'processing_timestamp': st.session_state.get('processing_timestamp', 0) + 1
    }
    
    try:
        logger.info(f"Starting direct JSON workflow ({len(json_content):,} characters)")
        
        # Clear stale analysis data when starting new direct JSON processing
        current_mode = st.session_state.get('current_input_analysis_mode')
        if current_mode != 'direct_json':
            cleared_count = clear_analysis_session_state()
            st.session_state['current_url_analysis'] = None
            st.session_state['current_input_analysis_mode'] = 'direct_json'
            st.session_state['processing_timestamp'] = result['processing_timestamp']
            
            if cleared_count > 0:
                st.info(f"🧹 Cleared previous analysis data for fresh start ({cleared_count} items)")
        
        # Setup logging based on mode
    if debug_mode:
        log_placeholder = st.empty()
        log_callback = create_debug_logger(log_placeholder)
        use_simple_logging = False
    else:
        # Use simple status for normal users
        simple_status = create_simple_status_updater()
        use_simple_logging = True
        
        # Create a dummy log_callback for backward compatibility
        def log_callback(message):
            if "Validating and processing JSON" in message:
                simple_status("Checking JSON format...", "info")
            elif "Decoding Unicode escapes" in message:
                simple_status("Processing text content...", "info")
            elif "workflow complete" in message:
                simple_status("JSON content ready for analysis!", "success")
        
        # Basic validation
    if use_simple_logging:
        simple_status("Checking JSON format...", "info")
    else:
        log_callback("📋 Validating and processing JSON input...")
        
        if not json_content.strip():
            error_msg = "Please provide JSON content"
            result['error'] = error_msg
            if use_simple_logging:
                simple_status("Please provide JSON content to analyze", "error")
            return result
        
        # FIXED: Apply Unicode decoding to direct input
    if use_simple_logging:
        simple_status("Processing text content...", "info")
    else:
        log_callback("🔤 Decoding Unicode escapes in JSON content...")
        decoded_json_content = decode_unicode_escapes(json_content)
        
        # Try to parse JSON to check basic validity
        try:
            import json
            parsed_json = json.loads(decoded_json_content)
            
            # Basic structure check
            if not isinstance(parsed_json, dict):
                error_msg = "JSON must be an object (not an array or primitive)"
                result['error'] = error_msg
                if use_simple_logging:
                    simple_status("JSON format issue - please check your content", "error")
                return result
            
            if 'big_chunks' not in parsed_json:
                error_msg = "JSON must contain 'big_chunks' array"
                result['error'] = error_msg
                if use_simple_logging:
                    simple_status("JSON missing required 'big_chunks' section", "error")
                return result
            
            big_chunks = parsed_json['big_chunks']
            if not isinstance(big_chunks, list) or len(big_chunks) == 0:
                result['error'] = "'big_chunks' must be a non-empty array"
                return result
            
            log_callback(f"✅ Valid JSON with {len(big_chunks)} chunks detected")
            
        except json.JSONDecodeError as e:
            result['error'] = f"Invalid JSON format: {str(e)}"
            return result
        
        # FIXED: Store both versions properly
        result['json_output_raw'] = decoded_json_content  # Decoded string for UI display
        result['json_output'] = parsed_json  # Parsed dict for AI processing
        
        if use_simple_logging:
        simple_status("JSON content ready for analysis!", "success")
    else:
        log_callback("🎉 Direct JSON workflow complete!")
        
        result['success'] = True
        logger.info(f"Direct JSON workflow completed successfully ({len(big_chunks)} chunks)")
        return result
        
    except Exception as e:
        error_msg = f"Unexpected direct JSON workflow error: {str(e)}"
        result['error'] = error_msg
        logger.error(error_msg)
        return result

def validate_analysis_freshness(result: dict, ai_result: dict = None) -> bool:
    """
    Validate that AI results correspond to current content processing.
    
    ENHANCED: Works with both URL and direct JSON input modes
    
    Args:
        result (dict): Current content processing result
        ai_result (dict): AI analysis result to validate
        
    Returns:
        bool: True if AI result is fresh/valid for current content
    """
    if not ai_result or not result:
        return True  # No AI result to validate, this is normal
    
    # Check processing timestamps
    content_timestamp = result.get('processing_timestamp')
    ai_timestamp = ai_result.get('processing_timestamp')
    
    if content_timestamp is not None and ai_timestamp is not None:
        if content_timestamp != ai_timestamp:
            # Only log warning in debug mode to reduce noise
            debug_mode = st.session_state.get('debug_mode', False)
            if debug_mode:
                logger.warning(f"AI result timestamp mismatch: content={content_timestamp}, ai={ai_timestamp}")
            return False
    
    # Check input modes match
    content_mode = result.get('input_mode', 'url')
    ai_mode = ai_result.get('input_mode', 'url')
    
    if content_mode != ai_mode:
        logger.warning(f"AI result input mode mismatch: content={content_mode}, ai={ai_mode}")
        return False
    
    return True

async def process_ai_analysis(json_output: str, api_key: str, source_result: dict = None) -> dict:
    """
    Process AI compliance analysis.
    
    FIXED: Use parsed JSON dict (not raw string) for AI processing
    
    Args:
        json_output (str): Raw JSON string or parsed dict
        api_key (str): OpenAI API key
        source_result (dict): Source content processing result for validation
        
    Returns:
        dict: AI analysis results with freshness tracking
    """
    try:
        logger.info("Starting AI analysis workflow")
        
        # FIXED: Handle both string and dict inputs properly
        if isinstance(json_output, str):
            json_data = parse_json_output(json_output)
        elif isinstance(json_output, dict):
            json_data = json_output
        else:
            return {'success': False, 'error': 'Invalid JSON output format'}
        
        if not json_data:
            return {'success': False, 'error': 'Failed to parse JSON content'}
        
        # Create progress tracking UI elements
        progress_container = st.container()
        
        with progress_container:
            input_mode = source_result.get('input_mode', 'url') if source_result else 'unknown'
            source_display = source_result.get('url', 'Direct JSON Input') if source_result else 'Unknown'
            
            if input_mode == 'url':
                st.info(f"🚀 Starting AI analysis of content extracted from URL")
            else:
                st.info(f"🚀 Starting AI analysis of direct JSON input")
            
            # Progress bar for overall progress
            progress_bar = st.progress(0.0)
            progress_text = st.empty()
            
            # Status metrics container
            status_container = st.empty()
            
            # Real-time progress callback
            def update_ui_progress(progress_data):
                """Update UI elements with progress information."""
                try:
                    progress = progress_data.get('progress', 0)
                    message = progress_data.get('message', 'Processing...')
                    
                    # Update progress bar
                    progress_bar.progress(min(progress, 1.0))
                    
                    # Update progress text
                    progress_text.text(f"📊 {message}")
                    
                except Exception as e:
                    logger.warning(f"Error updating UI progress: {e}")
            
            # Initialize analysis engine with progress callback
            analysis_engine = AnalysisEngine(api_key, progress_callback=update_ui_progress)
            
            # FIXED: Pass the raw JSON string for processing, not dict
            json_string_for_ai = source_result.get('json_output_raw') if source_result else json.dumps(json_data)
            
            # Process with real-time updates
            logger.info("Starting parallel AI analysis...")
            results = await analysis_engine.process_json_content(json_string_for_ai)
            
            # Update final progress
            progress_bar.progress(1.0)
            progress_text.text("✅ Analysis completed!")
            
            # Add tracking information to results
            if results.get('success') and source_result:
                results['processing_timestamp'] = source_result.get('processing_timestamp', 0)
                results['source_url'] = source_result.get('url', 'Direct JSON Input')
                results['input_mode'] = source_result.get('input_mode', 'url')
                results['content_hash'] = hash(json_string_for_ai)  # Quick content verification
            
            # Show final statistics
            if results['success']:
                stats = results.get('statistics', {})
                processing_time = results.get('processing_time', 0)
                
                with status_container.container():
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("Total Chunks", stats.get('total_chunks', 0))
                    with col2:
                        st.metric("Successful", stats.get('successful_analyses', 0))
                    with col3:
                        st.metric("Failed", stats.get('failed_analyses', 0))
                    with col4:
                        st.metric("Success Rate", f"{stats.get('success_rate', 0):.1f}%")
                    
                    if input_mode == 'url':
                        st.success(f"✅ AI analysis completed for URL content in {processing_time:.2f} seconds")
                    else:
                        st.success(f"✅ AI analysis completed for direct JSON input in {processing_time:.2f} seconds")
            else:
                st.error(f"❌ Analysis failed: {results.get('error', 'Unknown error')}")
        
        return results
        
    except Exception as e:
        error_msg = f"AI analysis error: {str(e)}"
        logger.error(error_msg)
        return {'success': False, 'error': error_msg}

def display_analysis_status_info():
    """
    Display information about current analysis status.
    
    ENHANCED: Show status for both URL and direct JSON inputs
    """
    input_mode = st.session_state.get('input_mode', '🌐 URL Input')
    
    if input_mode == "🌐 URL Input":
        current_url = st.session_state.get('current_url_analysis')
        if current_url:
            st.info(f"📋 **Current Analysis Context**: {current_url}")
    else:
        current_mode = st.session_state.get('current_input_analysis_mode')
        if current_mode == 'direct_json':
            st.info(f"📋 **Current Analysis Context**: Direct JSON Input")
    
    # Check for stale AI results
    ai_result = st.session_state.get('ai_analysis_result')
    content_result = st.session_state.get('latest_result')
    
    if ai_result and content_result:
        is_fresh = validate_analysis_freshness(content_result, ai_result)
        if not is_fresh:
            st.warning("⚠️ **Notice**: AI analysis results may be from a previous analysis. Run AI analysis again for current content.")

def main():
    """
    Main application function.
    
    ENHANCED: Support for dual input mode (URL + Direct JSON) with authentication
    """
    # Check authentication first
    if not check_authentication():
        return  # Stop here if not authenticated
    
    # Create page layout
    create_page_header()
    
    # Create sidebar configuration
    config = create_sidebar_config()
    debug_mode = config['debug_mode']
    api_key = config['api_key']
    
    # Store debug mode in session state for use in validation
    st.session_state['debug_mode'] = debug_mode
    
    # Display current analysis context
    display_analysis_status_info()
    
    # Create main content layout
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # NEW: Dual input section (URL or Direct JSON)
        input_mode, content, process_clicked = create_dual_input_section()
        
        # Process input when button is clicked
        if process_clicked:
            if not content:
                if input_mode == 'url':
                    display_error_message("Please enter a URL to process")
                else:
                    display_error_message("Please provide JSON content to analyze")
                return
            
            # Route to appropriate workflow based on input mode
            if input_mode == 'url':
                result = process_url_workflow(content, debug_mode)
                success_message = "URL processing completed successfully!"
            else:  # direct_json
                result = process_direct_json_workflow(content, debug_mode)
                success_message = "Direct JSON processing completed successfully!"
            
            # Store result
            st.session_state["latest_result"] = result
            
            if result["success"]:
                display_success_message(success_message)
                st.info("🤖 Ready for AI compliance analysis!")
            else:
                display_error_message(result['error'])
    
    with col2:
        create_how_it_works_section()
        # NEW: Show input mode context
        show_input_mode_context()
    
    # Results section
    if 'latest_result' in st.session_state and st.session_state['latest_result'].get('success'):
        result = st.session_state['latest_result']
        st.markdown("---")
        st.subheader("📊 Results")
        
        # FIXED: Pass the parsed JSON dict for AI analysis
        json_for_ai = result['json_output']  # This is the parsed dict
        
        # AI Analysis button and processing
        if create_ai_analysis_section(api_key, json_for_ai, result):
            if not api_key:
                display_error_message("OpenAI API key is required for AI analysis")
            else:
                try:
                    # Pass the parsed JSON dict for processing
                    with st.spinner("🤖 Initializing AI analysis..."):
                        ai_results = asyncio.run(process_ai_analysis(
                            json_for_ai, 
                            api_key, 
                            source_result=result
                        ))
                    
                    # Store results in session state
                    st.session_state['ai_analysis_result'] = ai_results
                    
                    if not ai_results.get('success'):
                        display_error_message(ai_results.get('error', 'Unknown error occurred'))
                    else:
                        input_mode = result.get('input_mode', 'url')
                        if input_mode == 'url':
                            st.success("✅ Fresh AI analysis completed for URL content!")
                        else:
                            st.success("✅ Fresh AI analysis completed for direct JSON input!")
                        
                except Exception as e:
                    error_msg = f"An error occurred during AI analysis: {str(e)}"
                    display_error_message(error_msg)
                    logger.error(error_msg)
        
        # Validate AI results freshness before display
        ai_result = st.session_state.get('ai_analysis_result')
        if ai_result and not validate_analysis_freshness(result, ai_result):
            st.warning("⚠️ **Stale AI Results Detected**: The AI analysis shown below may be from a previous analysis.")
            if st.button("🧹 Clear Stale Results", type="secondary", key="clear_stale_results"):
                clear_analysis_session_state()
                st.success("Stale results cleared! Run AI analysis again for fresh results.")
                st.experimental_rerun()
        
        # Display results in tabs
        create_results_tabs(result, ai_result)

def create_workflow_functions():
    """
    Create workflow helper functions for backwards compatibility.
    These maintain the same interface as the original monolithic version.
    """
    
    def process_url_workflow_with_logging(url, log_callback=None):
        """Legacy function wrapper for backwards compatibility."""
        # Determine debug mode based on callback presence
        debug_mode = log_callback is not None
        return process_url_workflow(url, debug_mode)
    
    return {
        'process_url_workflow_with_logging': process_url_workflow_with_logging
    }

# Create legacy functions for any existing code that might import them
legacy_functions = create_workflow_functions()
process_url_workflow_with_logging = legacy_functions['process_url_workflow_with_logging']

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        st.error(f"Application error: {str(e)}")
        logger.error(f"Application error: {str(e)}")
        
        # Show error details in debug mode
        if st.sidebar.checkbox("Show Error Details", key="show_error_details"):
            st.exception(e)