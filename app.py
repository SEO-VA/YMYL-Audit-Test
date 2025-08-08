#!/usr/bin/env python3
"""
YMYL Audit Tool - Main Application

Streamlined main application that orchestrates all components.
This is the clean, refactored version with modular architecture.

FIXED: Clear stale AI results when starting new URL analysis to prevent confusion
"""

import asyncio
import streamlit as st
from extractors.content_extractor import ContentExtractor
from processors.chunk_processor import ChunkProcessor
from ai.analysis_engine import AnalysisEngine
from utils.json_utils import extract_big_chunks, parse_json_output
from ui.components import (
    create_page_header,
    create_sidebar_config,
    create_how_it_works_section,
    create_url_input_section,
    create_debug_logger,
    create_simple_progress_tracker,
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

def clear_analysis_session_state():
    """
    Clear all analysis-related session state data.
    
    FIXED: Comprehensive clearing of stale AI results and related data
    """
    keys_to_clear = [
        "latest_result",
        "ai_analysis_result", 
        "ai_report",
        "ai_stats",
        "analysis_statistics",
        "current_url_analysis",  # Track which URL was analyzed
        "processing_start_time",
        "chunk_analysis_results"
    ]
    
    cleared_count = 0
    for key in keys_to_clear:
        if key in st.session_state:
            del st.session_state[key]
            cleared_count += 1
    
    if cleared_count > 0:
        logger.info(f"Cleared {cleared_count} stale session state keys")
    
    return cleared_count

def process_url_workflow(url: str, debug_mode: bool = False) -> dict:
    """
    Process URL through the complete extraction and chunking workflow.
    
    FIXED: Clear stale AI results and track current URL to prevent cross-contamination
    
    Args:
        url (str): URL to process
        debug_mode (bool): Whether to show detailed logs
        
    Returns:
        dict: Processing results
    """
    result = {
        'success': False,
        'url': url,
        'extracted_content': None,
        'json_output': None,
        'error': None,
        'processing_timestamp': st.session_state.get('processing_timestamp', None)
    }
    
    try:
        logger.info(f"Starting workflow for URL: {url}")
        
        # FIXED: Clear ALL stale analysis data when starting new URL processing
        current_url = st.session_state.get('current_url_analysis')
        if current_url != url:
            cleared_count = clear_analysis_session_state()
            st.session_state['current_url_analysis'] = url
            st.session_state['processing_timestamp'] = st.session_state.get('processing_timestamp', 0) + 1
            
            if cleared_count > 0:
                st.info(f"🧹 Cleared previous analysis data for fresh start ({cleared_count} items)")
        
        # Setup logging based on mode
        if debug_mode:
            log_placeholder = st.empty()
            log_callback = create_debug_logger(log_placeholder)
        else:
            log_area, log_callback = create_simple_progress_tracker()
        
        # Step 1: Content Extraction
        log_callback("🚀 Initializing content extractor...")
        with ContentExtractor() as extractor:
            log_callback(f"🔍 Fetching and extracting content from: {url}")
            success, content, error = extractor.extract_content(url)
            
            if not success:
                result['error'] = f"Content extraction failed: {error}"
                return result
            
            result['extracted_content'] = content
            log_callback(f"✅ Content extracted: {len(content):,} characters")
        
        # Step 2: Chunk Processing
        log_callback("🤖 Initializing chunk processor...")
        with ChunkProcessor(log_callback=log_callback if debug_mode else None) as processor:
            if not debug_mode:
                with st.status("You are not waiting, Chunk Norris is waiting for you"):
                    success, json_output, error = processor.process_content(content)
            else:
                success, json_output, error = processor.process_content(content)
            
            if not success:
                result['error'] = f"Chunk processing failed: {error}"
                return result
            
            result['json_output'] = json_output
            log_callback("🎉 Workflow Complete!")
        
        # FIXED: Store processing timestamp to track freshness
        result['processing_timestamp'] = st.session_state.get('processing_timestamp', 0)
        result['success'] = True
        logger.info("Workflow completed successfully")
        return result
        
    except Exception as e:
        error_msg = f"Unexpected workflow error: {str(e)}"
        result['error'] = error_msg
        logger.error(error_msg)
        return result

def validate_analysis_freshness(result: dict, ai_result: dict = None) -> bool:
    """
    Validate that AI results correspond to current content processing.
    
    FIXED: Prevent displaying AI results from different URL analysis
    
    Args:
        result (dict): Current content processing result
        ai_result (dict): AI analysis result to validate
        
    Returns:
        bool: True if AI result is fresh/valid for current content
    """
    if not ai_result or not result:
        return True  # No AI result to validate
    
    # Check if processing timestamps match
    content_timestamp = result.get('processing_timestamp', 0)
    ai_timestamp = ai_result.get('processing_timestamp', -1)
    
    if content_timestamp != ai_timestamp:
        logger.warning(f"AI result timestamp mismatch: content={content_timestamp}, ai={ai_timestamp}")
        return False
    
    # Check if URLs match
    content_url = result.get('url')
    ai_url = ai_result.get('source_url')
    
    if content_url and ai_url and content_url != ai_url:
        logger.warning(f"AI result URL mismatch: content={content_url}, ai={ai_url}")
        return False
    
    return True

async def process_ai_analysis(json_output: str, api_key: str, source_result: dict = None) -> dict:
    """
    Process AI compliance analysis.
    
    FIXED: Include source tracking to ensure AI results match current content
    
    Args:
        json_output (str): JSON output from chunk processing
        api_key (str): OpenAI API key
        source_result (dict): Source content processing result for validation
        
    Returns:
        dict: AI analysis results with freshness tracking
    """
    try:
        logger.info("Starting AI analysis workflow")
        
        # Parse JSON and extract chunks
        json_data = parse_json_output(json_output)
        if not json_data:
            return {'success': False, 'error': 'Failed to parse JSON content'}
        
        chunks = extract_big_chunks(json_data)
        if not chunks:
            return {'success': False, 'error': 'No chunks found in JSON data'}
        
        # Create progress tracking UI elements
        progress_container = st.container()
        
        with progress_container:
            st.info(f"🚀 Starting analysis of {len(chunks)} content chunks...")
            
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
            
            # Process with real-time updates
            logger.info("Starting parallel AI analysis...")
            results = await analysis_engine.process_json_content(json_output)
            
            # Update final progress
            progress_bar.progress(1.0)
            progress_text.text("✅ Analysis completed!")
            
            # FIXED: Add tracking information to results
            if results.get('success') and source_result:
                results['processing_timestamp'] = source_result.get('processing_timestamp', 0)
                results['source_url'] = source_result.get('url')
                results['content_hash'] = hash(json_output)  # Quick content verification
            
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
                    
                    st.success(f"✅ Analysis completed in {processing_time:.2f} seconds")
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
    
    FIXED: Show user which URL/content is currently loaded
    """
    current_url = st.session_state.get('current_url_analysis')
    if current_url:
        st.info(f"📋 **Current Analysis Context**: {current_url}")
        
        # Check for stale AI results
        ai_result = st.session_state.get('ai_analysis_result')
        content_result = st.session_state.get('latest_result')
        
        if ai_result and content_result:
            is_fresh = validate_analysis_freshness(content_result, ai_result)
            if not is_fresh:
                st.warning("⚠️ **Notice**: AI analysis results may be from a previous URL. Run AI analysis again for current content.")

def main():
    """Main application function."""
    # Create page layout
    create_page_header()
    
    # Create sidebar configuration
    config = create_sidebar_config()
    debug_mode = config['debug_mode']
    api_key = config['api_key']
    
    # FIXED: Display current analysis context
    display_analysis_status_info()
    
    # Create main content layout
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # URL input section
        url, process_clicked = create_url_input_section()
        
        # Process URL when button is clicked
        if process_clicked:
            if not url:
                display_error_message("Please enter a URL to process")
                return
            
            # FIXED: Process URL with automatic stale data clearing
            result = process_url_workflow(url, debug_mode)
            st.session_state["latest_result"] = result
            
            if result["success"]:
                display_success_message("Processing completed successfully!")
                # Show that we're ready for fresh AI analysis
                st.info("🤖 Ready for AI compliance analysis on fresh content!")
            else:
                display_error_message(result['error'])
    
    with col2:
        create_how_it_works_section()
    
    # Results section
    if 'latest_result' in st.session_state and st.session_state['latest_result'].get('success'):
        result = st.session_state['latest_result']
        st.markdown("---")
        st.subheader("📊 Results")
        
        # AI Analysis button and processing
        if create_ai_analysis_section(api_key, result['json_output']):
            if not api_key:
                display_error_message("OpenAI API key is required for AI analysis")
            else:
                try:
                    # FIXED: Pass source result for tracking and validation
                    with st.spinner("🤖 Initializing AI analysis..."):
                        ai_results = asyncio.run(process_ai_analysis(
                            result['json_output'], 
                            api_key, 
                            source_result=result
                        ))
                    
                    # Store results in session state
                    st.session_state['ai_analysis_result'] = ai_results
                    
                    if not ai_results.get('success'):
                        display_error_message(ai_results.get('error', 'Unknown error occurred'))
                    else:
                        st.success("✅ Fresh AI analysis completed for current content!")
                        
                except Exception as e:
                    error_msg = f"An error occurred during AI analysis: {str(e)}"
                    display_error_message(error_msg)
                    logger.error(error_msg)
        
        # FIXED: Validate AI results freshness before display
        ai_result = st.session_state.get('ai_analysis_result')
        if ai_result and not validate_analysis_freshness(result, ai_result):
            st.warning("⚠️ **Stale AI Results Detected**: The AI analysis shown below may be from a previous URL analysis.")
            if st.button("🧹 Clear Stale Results", type="secondary"):
                clear_analysis_session_state()
                st.success("Stale results cleared! Run AI analysis again for fresh results.")
                st.experimental_rerun()
        
        # Display results in tabs
        create_results_tabs(result, ai_result)

# FIXED: Add utility function for debugging session state
def debug_session_state():
    """Debug function to show current session state (for development)"""
    if st.sidebar.checkbox("🐛 Debug Session State", help="Show current session state for debugging"):
        st.sidebar.write("**Current Session State:**")
        for key, value in st.session_state.items():
            if key.startswith(('latest_', 'ai_', 'current_url', 'processing_')):
                st.sidebar.write(f"- {key}: {type(value).__name__}")

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
        # FIXED: Add debug session state option
        debug_session_state()
        main()
    except Exception as e:
        st.error(f"Application error: {str(e)}")
        logger.error(f"Application error: {str(e)}")
        
        # Show error details in debug mode
        if st.sidebar.checkbox("Show Error Details", key="show_error_details"):
            st.exception(e)