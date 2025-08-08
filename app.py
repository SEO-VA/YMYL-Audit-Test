#!/usr/bin/env python3
"""
YMYL Audit Tool - Main Application

Streamlined main application that orchestrates all components.
This is the clean, refactored version with modular architecture.
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

def process_url_workflow(url: str, debug_mode: bool = False) -> dict:
    """
    Process URL through the complete extraction and chunking workflow.
    
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
        'error': None
    }
    
    try:
        logger.info(f"Starting workflow for URL: {url}")
        
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
        
        result['success'] = True
        logger.info("Workflow completed successfully")
        return result
        
    except Exception as e:
        error_msg = f"Unexpected workflow error: {str(e)}"
        result['error'] = error_msg
        logger.error(error_msg)
        return result

async def process_ai_analysis(json_output: str, api_key: str) -> dict:
    """
    Process AI compliance analysis.
    
    Args:
        json_output (str): JSON output from chunk processing
        api_key (str): OpenAI API key
        
    Returns:
        dict: AI analysis results
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
        
        # Create processing interface
        ui_elements = create_ai_processing_interface(json_output, api_key, chunks)
        
        # Initialize analysis engine
        analysis_engine = AnalysisEngine(api_key)
        
        # Process with real-time updates
        with st.spinner("🤖 Running parallel analysis..."):
            results = await analysis_engine.process_json_content(json_output)
        
        # Update progress to completion
        ui_elements['progress_bar'].progress(1.0)
        
        if results['success']:
            processing_time = results.get('processing_time', 0)
            stats = results.get('statistics', {})
            
            with ui_elements['status_container'].container():
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Total Chunks", stats.get('total_chunks', 0))
                with col2:
                    st.metric("Successful", stats.get('successful_analyses', 0))
                with col3:
                    st.metric("Failed", stats.get('failed_analyses', 0))
                
                st.success(f"✅ Analysis completed in {processing_time:.2f} seconds")
        
        return results
        
    except Exception as e:
        error_msg = f"AI analysis error: {str(e)}"
        logger.error(error_msg)
        return {'success': False, 'error': error_msg}

def main():
    """Main application function."""
    # Create page layout
    create_page_header()
    
    # Create sidebar configuration
    config = create_sidebar_config()
    debug_mode = config['debug_mode']
    api_key = config['api_key']
    
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
            
            # Clear previous results
            for key in ("latest_result", "ai_analysis_result"):
                st.session_state.pop(key, None)
            
            # Process URL
            result = process_url_workflow(url, debug_mode)
            st.session_state["latest_result"] = result
            
            if result["success"]:
                display_success_message("Processing completed successfully!")
            else:
                display_error_message(result['error'])
    
    with col2:
        create_how_it_works_section()
    
    # Results section
    if 'latest_result' in st.session_state and st.session_state['latest_result'].get('success'):
        result = st.session_state['latest_result']
        st.markdown("---")
        st.subheader("📊 Results")
        
        # AI Analysis button
        if create_ai_analysis_section(api_key, result['json_output']):
            try:
                # Run AI analysis
                ai_results = asyncio.run(process_ai_analysis(result['json_output'], api_key))
                st.session_state['ai_analysis_result'] = ai_results
                
                if not ai_results.get('success'):
                    display_error_message(ai_results.get('error', 'Unknown error occurred'))
                    
            except Exception as e:
                error_msg = f"An error occurred during AI analysis: {str(e)}"
                display_error_message(error_msg)
                logger.error(error_msg)
        
        # Display results in tabs
        ai_result = st.session_state.get('ai_analysis_result')
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
