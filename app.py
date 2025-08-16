#!/usr/bin/env python3
"""
YMYL Audit Tool - Main Application with Authentication

UPDATED: Single request AI analysis architecture
Enhanced with triple input mode: URL extraction, Direct JSON input, AND Raw Content chunking.
"""
import re
import asyncio
import streamlit as st
import time
import json
from collections import defaultdict
from extractors.content_extractor import ContentExtractor
from processors.chunk_processor import ChunkProcessor
from ai.analysis_engine import AnalysisEngine
from utils.json_utils import parse_json_output, decode_unicode_escapes
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
    create_info_panel
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
                time.sleep(0.5)
                st.rerun()
            else:
                st.error("❌ Invalid username or password")
                time.sleep(1)
                return False
    
    return False

# =============================================================================
# DATA HANDLING AND WORKFLOWS
# =============================================================================

def clear_analysis_session_state():
    """Clear all analysis-related session state data."""
    keys_to_clear = [
        "latest_result",
        "ai_analysis_result", 
        "ai_report",
        "ai_stats",
        "analysis_statistics",
        "current_url_analysis",
        "current_input_analysis_mode",
        "processing_start_time"
    ]
    
    cleared_count = 0
    for key in keys_to_clear:
        if key in st.session_state:
            del st.session_state[key]
            cleared_count += 1
    
    # Also clear any download-related keys to prevent media file errors
    download_keys_to_clear = []
    for key in st.session_state.keys():
        if key.startswith('download_') or key.startswith('backup_download_'):
            download_keys_to_clear.append(key)
    
    for key in download_keys_to_clear:
        try:
            del st.session_state[key]
            cleared_count += 1
        except:
            pass
    
    if cleared_count > 0:
        logger.info(f"Cleared {cleared_count} stale session state keys")
    
    return cleared_count

def process_url_workflow(url: str, debug_mode: bool = False) -> dict:
    """Process URL through the complete extraction and chunking workflow."""
    result = {
        'success': False,
        'url': url,
        'extracted_content': None,
        'json_output_raw': None,
        'json_output': None,
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
            simple_status = create_simple_status_updater()
            use_simple_logging = True
            
            def log_callback(message):
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
            
            success, content, error = extractor.extract_content(url)
            
            if not success:
                error_msg = f"Content extraction failed: {error}"
                result['error'] = error_msg
                if use_simple_logging:
                    simple_status("Couldn't extract content from website", "error")
                return result
            
            result['extracted_content'] = content
            if use_simple_logging:
                simple_status("Content successfully extracted", "success")
            else:
                log_callback(f"✅ Content extracted: {len(content):,} characters")
        
        # Step 2: Chunk Processing
        if use_simple_logging:
            simple_status("Processing content into sections...", "info")
        else:
            log_callback("✨ Initializing chunk processor...")
            
        with ChunkProcessor(log_callback=log_callback if debug_mode else None) as processor:
            if not debug_mode:
                if use_simple_logging:
                    with st.status("You are not waiting, Chunk Norris is waiting for you..."):
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
            
            result['json_output_raw'] = json_output_raw
            result['json_output'] = parse_json_output(json_output_raw)
            
            if use_simple_logging:
                simple_status("Content ready for AI analysis!", "success")
            else:
                log_callback("🎉 URL workflow complete!")
        
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
    """Process direct JSON input, skipping URL extraction and chunking."""
    result = {
        'success': False,
        'url': 'Direct JSON Input',
        'extracted_content': 'Content provided directly as chunked JSON',
        'json_output_raw': None,
        'json_output': None,
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
            simple_status = create_simple_status_updater()
            use_simple_logging = True
            
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
        
        # Apply Unicode decoding to direct input
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
            
            if not use_simple_logging:
                log_callback(f"✅ Valid JSON with {len(big_chunks)} chunks detected")
            
        except json.JSONDecodeError as e:
            result['error'] = f"Invalid JSON format: {str(e)}"
            return result
        
        result['json_output_raw'] = decoded_json_content
        result['json_output'] = parsed_json
        
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

def process_raw_content_workflow(raw_content: str, debug_mode: bool = False) -> dict:
    """Process raw content through chunking service, then prepare for AI analysis."""
    result = {
        'success': False,
        'url': 'Raw Content Input',
        'extracted_content': raw_content,
        'json_output_raw': None,
        'json_output': None,
        'error': None,
        'input_mode': 'raw_content',
        'processing_timestamp': st.session_state.get('processing_timestamp', 0) + 1
    }
    
    try:
        logger.info(f"Starting raw content workflow ({len(raw_content):,} characters)")
        
        # Clear stale analysis data when starting new raw content processing
        current_mode = st.session_state.get('current_input_analysis_mode')
        if current_mode != 'raw_content':
            cleared_count = clear_analysis_session_state()
            st.session_state['current_url_analysis'] = None
            st.session_state['current_input_analysis_mode'] = 'raw_content'
            st.session_state['processing_timestamp'] = result['processing_timestamp']
            
            if cleared_count > 0:
                st.info(f"🧹 Cleared previous analysis data for fresh start ({cleared_count} items)")
        
        # Setup logging based on mode
        if debug_mode:
            log_placeholder = st.empty()
            log_callback = create_debug_logger(log_placeholder)
            use_simple_logging = False
        else:
            simple_status = create_simple_status_updater()
            use_simple_logging = True
            
            def log_callback(message):
                if "Initializing chunk processor" in message:
                    simple_status("Preparing to chunk your content...", "info")
                elif "Navigating to" in message:
                    simple_status("Connecting to chunking service...", "info")
                elif "Using JavaScript to copy content" in message:
                    simple_status("Sending content for processing...", "info")
                elif "Clicking submit button" in message:
                    simple_status("Processing content into chunks...", "info")
                elif "Waiting for results" in message:
                    simple_status("Waiting for chunking to complete...", "info")
                elif "Extraction complete" in message:
                    simple_status("Content successfully chunked!", "success")
                elif "workflow complete" in message:
                    simple_status("Raw content ready for AI analysis!", "success")
        
        # Basic validation
        if use_simple_logging:
            simple_status("Validating raw content...", "info")
        else:
            log_callback("📋 Validating raw content input...")
            
        if not raw_content.strip():
            error_msg = "Please provide raw content to process"
            result['error'] = error_msg
            if use_simple_logging:
                simple_status("Please provide content to analyze", "error")
            return result
        
        # Check content length
        from config.settings import MAX_CONTENT_LENGTH
        if len(raw_content) > MAX_CONTENT_LENGTH:
            error_msg = f"Content too large: {len(raw_content):,} characters (max: {MAX_CONTENT_LENGTH:,})"
            result['error'] = error_msg
            if use_simple_logging:
                simple_status("Content is too large for processing", "error")
            return result
        
        # Step 1: Send raw content to chunking service
        if use_simple_logging:
            simple_status("Preparing to chunk your content...", "info")
        else:
            log_callback("✨ Initializing chunk processor for raw content...")
            
        with ChunkProcessor(log_callback=log_callback if debug_mode else None) as processor:
            if not debug_mode:
                if use_simple_logging:
                    with st.status("Chunking your content with Dejan service..."):
                        success, json_output_raw, error = processor.process_content(raw_content)
                        if success:
                            simple_status("Content successfully chunked!", "success")
                else:
                    with st.status("Processing content through chunking service"):
                        success, json_output_raw, error = processor.process_content(raw_content)
            else:
                success, json_output_raw, error = processor.process_content(raw_content)
                
            if not success:
                error_msg = f"Content chunking failed: {error}"
                result['error'] = error_msg
                if use_simple_logging:
                    simple_status("Problem chunking the content", "error")
                return result
            
            # Store both raw and parsed versions
            result['json_output_raw'] = json_output_raw
            result['json_output'] = parse_json_output(json_output_raw)
            
            if use_simple_logging:
                simple_status("Raw content ready for AI analysis!", "success")
            else:
                log_callback("🎉 Raw content workflow complete!")
        
        result['processing_timestamp'] = st.session_state.get('processing_timestamp', 0)
        result['success'] = True
        logger.info("Raw content workflow completed successfully")
        return result
        
    except Exception as e:
        error_msg = f"Unexpected raw content workflow error: {str(e)}"
        result['error'] = error_msg
        logger.error(error_msg)
        return result

def validate_analysis_freshness(result: dict, ai_result: dict = None) -> bool:
    """
    Validate that AI results correspond to current content processing.
    UPDATED: Simplified for single request architecture
    """
    if not ai_result or not result:
        return True
    
    # Check processing timestamps
    content_timestamp = result.get('processing_timestamp')
    ai_timestamp = ai_result.get('processing_timestamp')
    
    if content_timestamp is not None and ai_timestamp is not None:
        if content_timestamp != ai_timestamp:
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
    UPDATED: Single request architecture with import fix
    """
    try:
        logger.info("Starting single-request AI analysis workflow")
        
        # Handle both string and dict inputs
        if isinstance(json_output, str):
            json_data = parse_json_output(json_output)
        elif isinstance(json_output, dict):
            json_data = json_output
        else:
            return {'success': False, 'error': 'Invalid JSON output format'}
        
        if not json_data:
            return {'success': False, 'error': 'Failed to parse JSON content'}
        
        # Validate content size - FIXED: Use fallback if import fails
        json_string = json.dumps(json_data) if isinstance(json_data, dict) else json_output
        content_size = len(json_string)
        
        try:
            from config.settings import MAX_CONTENT_SIZE_FOR_AI
        except ImportError:
            MAX_CONTENT_SIZE_FOR_AI = 2000000  # 2MB fallback
        
        if content_size > MAX_CONTENT_SIZE_FOR_AI:
            return {
                'success': False, 
                'error': f'Content too large for single request: {content_size:,} chars (max: {MAX_CONTENT_SIZE_FOR_AI:,})'
            }
        
        # Create progress tracking UI
        progress_container = st.container()
        
        with progress_container:
            input_mode = source_result.get('input_mode', 'url') if source_result else 'unknown'
            
            if input_mode == 'url':
                st.info("🚀 Starting single-request AI analysis of extracted content")
            elif input_mode == 'direct_json':
                st.info("🚀 Starting single-request AI analysis of direct JSON input")
            elif input_mode == 'raw_content':
                st.info("🚀 Starting single-request AI analysis of chunked content")
            else:
                st.info("🚀 Starting single-request AI analysis")
            
            # Progress bar
            progress_bar = st.progress(0.0)
            progress_text = st.empty()
            
            # Progress callback
            def update_ui_progress(progress_data):
                try:
                    progress = progress_data.get('progress', 0)
                    message = progress_data.get('message', 'Processing...')
                    
                    progress_bar.progress(min(progress, 1.0))
                    progress_text.text(f"📊 {message}")
                    
                except Exception as e:
                    logger.warning(f"Error updating UI progress: {e}")
            
            # Initialize analysis engine
            analysis_engine = AnalysisEngine(api_key, progress_callback=update_ui_progress)
            
            # Use raw JSON string for processing
            json_string_for_ai = source_result.get('json_output_raw') if source_result else json_string
            
            # Process with single request
            logger.info("Starting single AI analysis request...")
            results = await analysis_engine.process_json_content(json_string_for_ai)
            
            # Update final progress
            progress_bar.progress(1.0)
            progress_text.text("✅ Single-request analysis completed!")
            
            # Add tracking information
            if results.get('success') and source_result:
                results['processing_timestamp'] = source_result.get('processing_timestamp', 0)
                results['source_url'] = source_result.get('url', 'Processed Content')
                results['input_mode'] = source_result.get('input_mode', 'unknown')
                results['content_hash'] = hash(json_string_for_ai)
            
            # Show final status
            if results['success']:
                processing_time = results.get('processing_time', 0)
                
                if input_mode == 'url':
                    st.success(f"✅ Single-request AI analysis completed for URL content in {processing_time:.2f} seconds")
                elif input_mode == 'direct_json':
                    st.success(f"✅ Single-request AI analysis completed for direct JSON in {processing_time:.2f} seconds")
                elif input_mode == 'raw_content':
                    st.success(f"✅ Single-request AI analysis completed for chunked content in {processing_time:.2f} seconds")
                else:
                    st.success(f"✅ Single-request AI analysis completed in {processing_time:.2f} seconds")
            else:
                st.error(f"❌ Analysis failed: {results.get('error', 'Unknown error')}")
        
        return results
        
    except Exception as e:
        error_msg = f"AI analysis error: {str(e)}"
        logger.error(error_msg)
        return {'success': False, 'error': error_msg}

def main():
    """
    Main application function.
    UPDATED: Single request AI analysis
    """
    # Check authentication first
    if not check_authentication():
        return
    
    # Create page layout
    create_page_header()
    
    # Create sidebar configuration
    config = create_sidebar_config()
    debug_mode = config['debug_mode']
    api_key = config['api_key']
    
    # Store debug mode in session state
    st.session_state['debug_mode'] = debug_mode
    
    # Create main content layout
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # Input section
        input_mode, content, process_clicked = create_dual_input_section()
        
        # Process input when button is clicked
        if process_clicked:
            if not content:
                if input_mode == "🌐 URL Input":
                    display_error_message("Please enter a URL to process")
                elif input_mode == "📄 Direct JSON":
                    display_error_message("Please provide JSON content to analyze")
                elif input_mode == "📝 Raw Content":
                    display_error_message("Please provide raw content to process")
                return
            
            # Route to appropriate workflow
            if input_mode == "🌐 URL Input":
                result = process_url_workflow(content, debug_mode)
            elif input_mode == "📄 Direct JSON":
                result = process_direct_json_workflow(content, debug_mode)
            elif input_mode == "📝 Raw Content":
                result = process_raw_content_workflow(content, debug_mode)
            else:
                display_error_message(f"Unknown input mode: {input_mode}")
                return
            
            # Store result
            st.session_state["latest_result"] = result
            
            if not result["success"]:
                display_error_message(result['error'])
    
    with col2:
        create_how_it_works_section()

    # Results section
    if 'latest_result' in st.session_state and st.session_state['latest_result'].get('success'):
        result = st.session_state['latest_result']
        st.markdown("---")
        st.subheader("📊 Results")
        
        # Get JSON for AI analysis
        json_for_ai = result['json_output']
        
        # AI Analysis button and processing (UPDATED)
        if create_ai_analysis_section(api_key, json_for_ai, result):
            if not api_key:
                display_error_message("OpenAI API key is required for AI analysis")
            else:
                try:
                    # Single request AI analysis
                    with st.spinner("✨ Initializing single-request AI analysis..."):
                        ai_results = asyncio.run(process_ai_analysis(
                            json_for_ai, 
                            api_key, 
                            source_result=result
                        ))
                    
                    # Store results
                    st.session_state['ai_analysis_result'] = ai_results
                    
                    if not ai_results.get('success'):
                        display_error_message(ai_results.get('error', 'Unknown error occurred'))
                    else:
                        input_mode = result.get('input_mode', 'url')
                        if input_mode == 'url':
                            st.success("✅ Single-request AI analysis completed for URL content!")
                        elif input_mode == 'direct_json':
                            st.success("✅ Single-request AI analysis completed for direct JSON!")
                        elif input_mode == 'raw_content':
                            st.success("✅ Single-request AI analysis completed for chunked content!")
                        
                except Exception as e:
                    error_msg = f"An error occurred during AI analysis: {str(e)}"
                    display_error_message(error_msg)
                    logger.error(error_msg)
        
        # Validate AI results freshness
        ai_result = st.session_state.get('ai_analysis_result')
        if ai_result and not validate_analysis_freshness(result, ai_result):
            st.warning("⚠️ **Stale AI Results Detected**: The AI analysis shown below may be from a previous analysis.")
            if st.button("🧹 Clear Stale Results", type="secondary", key="clear_stale_results"):
                clear_analysis_session_state()
                st.success("Stale results cleared! Run AI analysis again for fresh results.")

        # Display results in tabs
        create_results_tabs(result, ai_result)

def create_workflow_functions():
    """
    Create workflow helper functions for backwards compatibility.
    """
    
    def process_url_workflow_with_logging(url, log_callback=None):
        """Legacy function wrapper for backwards compatibility."""
        debug_mode = log_callback is not None
        return process_url_workflow(url, debug_mode)
    
    def process_raw_content_workflow_with_logging(content, log_callback=None):
        """Function for raw content processing with logging."""
        debug_mode = log_callback is not None
        return process_raw_content_workflow(content, debug_mode)
    
    return {
        'process_url_workflow_with_logging': process_url_workflow_with_logging,
        'process_raw_content_workflow_with_logging': process_raw_content_workflow_with_logging
    }

# Create legacy functions for any existing code that might import them
legacy_functions = create_workflow_functions()
process_url_workflow_with_logging = legacy_functions['process_url_workflow_with_logging']
process_raw_content_workflow_with_logging = legacy_functions['process_raw_content_workflow_with_logging']

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        st.error(f"Application error: {str(e)}")
        logger.error(f"Application error: {str(e)}")
        
        # Show error details in debug mode
        if st.sidebar.checkbox("Show Error Details", key="show_error_details"):
            st.exception(e)