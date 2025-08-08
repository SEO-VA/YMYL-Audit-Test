#!/usr/bin/env python3
"""
Main Streamlit App for YMYL Audit Tool
Updated to use optimized Assistant client with performance fixes
"""
import streamlit as st
import asyncio
from typing import Dict, Any, List

# Your existing imports
from extractors.content_extractor import ContentExtractor
from processors.chunk_processor import ChunkProcessor
from ui.components import (
    create_page_header, create_sidebar_config, 
    create_url_input_section, create_results_tabs
)
from utils.json_utils import extract_big_chunks, parse_json_output

# Import export manager with error handling
try:
    from exporters.export_manager import ExportManager
    EXPORTS_AVAILABLE = True
except ImportError as e:
    EXPORTS_AVAILABLE = False
    print(f"Export functionality not available: {e}")

# Import optimized AI client
try:
    from ai.assistant_client import (
        process_chunks_async, 
        cancel_current_processing,
        process_chunks_with_cancellation
    )
    AI_AVAILABLE = True
except ImportError as e:
    AI_AVAILABLE = False
    print(f"AI functionality not available: {e}")


def main():
    """Main Streamlit application"""
    st.set_page_config(
        page_title="YMYL Audit Tool", 
        page_icon="🔍", 
        layout="wide"
    )
    
    # Check for API key first
    if not hasattr(st, 'secrets') or 'openai_api_key' not in st.secrets:
        st.error("❌ OpenAI API key not configured. Please add 'openai_api_key' to your Streamlit secrets.")
        st.stop()
    
    # UI Components
    create_page_header()
    create_sidebar_config()
    
    # URL Processing Section
    url = create_url_input_section()
    
    if url and st.button("🚀 Start Analysis", type="primary"):
        process_url_workflow(url)


def process_url_workflow(url: str):
    """Complete workflow from URL to final report"""
    
    # Step 1: Extract Content
    with st.spinner("🌐 Extracting content from webpage..."):
        with ContentExtractor() as extractor:
            success, content, error = extractor.extract_content(url)
        
        if not success:
            st.error(f"❌ Failed to extract content: {error}")
            return
        
        st.success(f"✅ Content extracted: {len(content)} characters")
    
    # Step 2: Process into Chunks
    with st.spinner("🔄 Processing content into chunks..."):
        with ChunkProcessor() as processor:
            success, json_output, error = processor.process_content(content)
        
        if not success:
            st.error(f"❌ Failed to process chunks: {error}")
            return
        
        # Parse chunks
        json_data = parse_json_output(json_output)
        if not json_data:
            st.error("❌ Failed to parse chunk JSON output")
            return
            
        chunks = extract_big_chunks(json_data)
        st.success(f"✅ Content chunked: {len(chunks)} sections identified")
    
    # Store in session state for AI processing
    st.session_state.chunks = chunks
    st.session_state.url = url
    st.session_state.json_output = json_output
    st.session_state.extracted_content = content
    
    # Step 3: AI Analysis Section
    st.markdown("### 🤖 AI Analysis")
    
    if not AI_AVAILABLE:
        st.warning("⚠️ AI functionality not available. Please check your ai module setup.")
        display_chunked_results_only(chunks, json_output, content, url)
        return
    
    # Create two columns for AI analysis
    col1, col2 = st.columns([2, 1])
    
    with col1:
        if st.button("🧠 Analyze with AI", type="secondary"):
            process_ai_analysis_async()
    
    with col2:
        st.info(f"Ready to analyze {len(chunks)} content sections")
        
        # Add cancellation button if processing is in progress
        if st.session_state.get('ai_processing', False):
            if st.button("🛑 Cancel Processing", type="secondary"):
                cancel_current_processing()
                st.session_state.ai_processing = False
                st.warning("🛑 Processing cancelled")
                st.experimental_rerun()
    
    # Always show chunked results
    display_chunked_results(chunks, json_output, content, url)


def process_ai_analysis_async():
    """
    Process AI analysis using the optimized Assistant client
    """
    if "chunks" not in st.session_state:
        st.error("❌ No chunks available for analysis")
        return
    
    chunks = st.session_state.chunks
    
    # Set processing flag
    st.session_state.ai_processing = True
    
    # Progress tracking setup
    progress_bar = st.progress(0)
    status_text = st.empty()
    metrics_container = st.empty()
    
    def progress_callback(completed: int, total: int, success: bool):
        """Update progress in real-time"""
        progress = completed / total
        progress_bar.progress(progress)
        
        # Update status
        status_icon = "✅" if success else "❌"
        status_text.text(f"Processing: {completed}/{total} chunks {status_icon}")
        
        # Update metrics
        if completed > 0:
            success_rate = (completed / total) * 100
            with metrics_container.container():
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Progress", f"{completed}/{total}")
                with col2:
                    st.metric("Success Rate", f"{success_rate:.0f}%")
                with col3:
                    st.metric("Current", status_icon)
    
    # Run async processing with error handling
    try:
        with st.spinner("🧠 Analyzing content with AI..."):
            # Run the async function with cancellation support
            report, stats = asyncio.run(
                process_chunks_with_cancellation(chunks, progress_callback)
            )
        
        # Clear progress indicators
        progress_bar.empty()
        status_text.empty()
        metrics_container.empty()
        
        # Check if processing was cancelled
        if stats.get('cancelled', False):
            st.warning("🛑 Processing was cancelled")
            st.session_state.ai_processing = False
            return
        
        # Store results
        st.session_state.ai_report = report
        st.session_state.ai_stats = stats
        st.session_state.ai_processing = False
        
        # Show success message
        successful = stats.get('successful', 0)
        total = stats.get('total_chunks', 0)
        processing_time = stats.get('total_processing_time', 0)
        
        st.success(f"✅ AI Analysis Complete!")
        
        # Show detailed stats
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Processed", f"{successful}/{total}")
        with col2:
            st.metric("Total Time", f"{processing_time:.1f}s")
        with col3:
            avg_time = processing_time / total if total > 0 else 0
            st.metric("Avg/Chunk", f"{avg_time:.1f}s")
        with col4:
            success_rate = (successful / total * 100) if total > 0 else 0
            st.metric("Success Rate", f"{success_rate:.0f}%")
        
        # Display results
        display_ai_results(report, stats)
        
    except asyncio.CancelledError:
        # Handle cancellation gracefully
        progress_bar.empty()
        status_text.empty()
        metrics_container.empty()
        st.warning("🛑 Processing was cancelled")
        st.session_state.ai_processing = False
        
    except Exception as e:
        # Handle other errors
        progress_bar.empty()
        status_text.empty()
        metrics_container.empty()
        st.session_state.ai_processing = False
        st.error(f"❌ AI Analysis failed: {str(e)}")
        
        # Show debug info in expander
        with st.expander("🐛 Error Details"):
            import traceback
            st.code(traceback.format_exc())


def display_chunked_results(chunks: List[Dict[str, Any]], json_output: str, content: str, url: str):
    """Display the chunked content results with all tabs"""
    
    # Check if we have AI results
    ai_report = st.session_state.get('ai_report')
    ai_stats = st.session_state.get('ai_stats')
    
    if ai_report and ai_stats:
        # Create tabs with AI results
        tabs = st.tabs([
            "🎯 AI Report", 
            "📊 AI Statistics", 
            "📄 Content Sections",
            "🔧 JSON Output", 
            "📝 Raw Content",
            "📥 Downloads"
        ])
        
        with tabs[0]:
            display_ai_report_tab(ai_report)
        
        with tabs[1]:
            display_ai_statistics_tab(ai_stats)
            
        with tabs[2]:
            display_content_sections_tab(chunks)
        
        with tabs[3]:
            display_json_tab(json_output)
        
        with tabs[4]:
            display_raw_content_tab(content)
            
        with tabs[5]:
            display_downloads_tab(ai_report, url)
    else:
        # Create tabs without AI results
        tabs = st.tabs([
            "📄 Content Sections",
            "🔧 JSON Output", 
            "📝 Raw Content"
        ])
        
        with tabs[0]:
            display_content_sections_tab(chunks)
        
        with tabs[1]:
            display_json_tab(json_output)
        
        with tabs[2]:
            display_raw_content_tab(content)


def display_chunked_results_only(chunks: List[Dict[str, Any]], json_output: str, content: str, url: str):
    """Display results when AI is not available"""
    st.markdown("### 📄 Content Analysis Results")
    
    tabs = st.tabs([
        "📄 Content Sections",
        "🔧 JSON Output", 
        "📝 Raw Content"
    ])
    
    with tabs[0]:
        display_content_sections_tab(chunks)
    
    with tabs[1]:
        display_json_tab(json_output)
    
    with tabs[2]:
        display_raw_content_tab(content)


def display_ai_report_tab(report: str):
    """Display AI analysis report"""
    st.markdown("### 🔍 YMYL Compliance Analysis Report")
    st.markdown(report)


def display_ai_statistics_tab(stats: Dict[str, Any]):
    """Display AI processing statistics"""
    st.markdown("### 📈 AI Processing Statistics")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Chunks", stats.get('total_chunks', 0))
    with col2:
        st.metric("Successful", stats.get('successful', 0))
    with col3:
        st.metric("Failed", stats.get('failed', 0))
    with col4:
        st.metric("Processing Time", f"{stats.get('total_processing_time', 0):.1f}s")
    
    # Additional metrics
    if stats.get('total_chunks', 0) > 0:
        avg_time = stats.get('average_time_per_chunk', 0)
        success_rate = (stats.get('successful', 0) / stats.get('total_chunks', 1)) * 100
        
        st.markdown("### Performance Metrics")
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Average Time per Chunk", f"{avg_time:.2f}s")
        with col2:
            st.metric("Success Rate", f"{success_rate:.1f}%")


def display_content_sections_tab(chunks: List[Dict[str, Any]]):
    """Display the chunked content sections"""
    if not chunks:
        st.info("No content sections available")
        return
    
    st.markdown(f"### 📄 Content Sections ({len(chunks)} sections)")
    
    for i, chunk in enumerate(chunks):
        chunk_index = chunk.get('index', i + 1)
        content = chunk.get('text', chunk.get('content', ''))
        char_count = len(content)
        
        with st.expander(f"Section {chunk_index} ({char_count:,} characters)"):
            # Show content preview
            preview_length = min(500, len(content))
            preview = content[:preview_length]
            if len(content) > preview_length:
                preview += "..."
            
            st.text_area(
                "Content:", 
                value=preview, 
                height=200,
                disabled=True
            )
            
            # Show full content in code block for copying
            with st.expander("View Full Content"):
                st.code(content, language="text")


def display_json_tab(json_output: str):
    """Display JSON output"""
    st.markdown("### 🔧 JSON Output")
    st.code(json_output, language='json')
    
    # Download button
    import time
    timestamp = int(time.time())
    st.download_button(
        label="💾 Download JSON",
        data=json_output,
        file_name=f"chunks_{timestamp}.json",
        mime="application/json"
    )


def display_raw_content_tab(content: str):
    """Display raw extracted content"""
    st.markdown("### 📝 Raw Extracted Content")
    st.text_area(
        "Raw content extracted from webpage:", 
        value=content, 
        height=400,
        help="This is the original content extracted from the webpage before chunking"
    )


def display_downloads_tab(report: str, url: str):
    """Display download options for the AI report"""
    st.markdown("### 📥 Download Analysis Report")
    
    if not EXPORTS_AVAILABLE:
        st.warning("⚠️ Export functionality not available")
        # Fallback markdown download
        import time
        timestamp = int(time.time())
        st.download_button(
            label="💾 Download Report (Markdown)",
            data=report,
            file_name=f"ymyl_audit_report_{timestamp}.md",
            mime="text/markdown"
        )
        return
    
    if st.button("📄 Generate Export Files", type="secondary"):
        generate_exports(report, url)


def display_ai_results(report: str, stats: Dict[str, Any]):
    """Legacy function for backward compatibility"""
    # This function is called from the processing but results are shown in tabs
    pass


def generate_exports(report_content: str, url: str):
    """Generate export files in multiple formats"""
    
    if not EXPORTS_AVAILABLE:
        st.error("❌ Export functionality not available. Please check your exporters module.")
        return
    
    with st.spinner("📄 Generating export files..."):
        try:
            export_manager = ExportManager()
            
            # Use your existing export manager's API
            results = export_manager.export_all_formats(
                markdown_content=report_content,  # Your API uses markdown_content
                title=f"YMYL Audit Report - {url}",
                formats=["html", "pdf", "docx", "markdown"]  # Your API uses 'docx' not 'word'
            )
            
            # Handle your export manager's response format
            if not results.get("success"):
                st.error(f"❌ Export failed: {results.get('error', 'Unknown error')}")
                return
            
            # Your API structure: results['formats'][format_name]
            formats_data = results.get('formats', {})
            
            if not formats_data:
                st.error("❌ No export formats were generated")
                return
            
            st.success("✅ Export files generated successfully!")
            
            # Create download buttons
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                if 'html' in formats_data:
                    filename = export_manager.create_filename("ymyl_audit_report", "html")
                    st.download_button(
                        "📄 HTML", 
                        data=formats_data['html'], 
                        file_name=filename,
                        mime="text/html"
                    )
            
            with col2:
                if 'pdf' in formats_data:
                    filename = export_manager.create_filename("ymyl_audit_report", "pdf")
                    st.download_button(
                        "📑 PDF", 
                        data=formats_data['pdf'], 
                        file_name=filename,
                        mime="application/pdf"
                    )
            
            with col3:
                if 'docx' in formats_data:  # Your system uses 'docx' not 'word'
                    filename = export_manager.create_filename("ymyl_audit_report", "docx")
                    st.download_button(
                        "📝 Word", 
                        data=formats_data['docx'], 
                        file_name=filename,
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                    )
            
            with col4:
                if 'markdown' in formats_data:
                    filename = export_manager.create_filename("ymyl_audit_report", "markdown")
                    st.download_button(
                        "📋 Markdown", 
                        data=formats_data['markdown'], 
                        file_name=filename,
                        mime="text/markdown"
                    )
            
            # Show export statistics
            metadata = results.get('metadata', {})
            if metadata:
                st.info(f"📊 {metadata.get('successful_formats', 0)} formats exported in {metadata.get('processing_time', 0):.2f}s")
            
            # Show any errors for individual formats
            errors = results.get('errors', {})
            if errors:
                with st.expander("⚠️ Export Warnings"):
                    for format_name, error in errors.items():
                        st.warning(f"{format_name.upper()}: {error}")
            
        except Exception as e:
            st.error(f"❌ Export generation failed: {str(e)}")
            # Show more detailed error info in debug mode
            import traceback
            with st.expander("🐛 Debug Info"):
                st.code(traceback.format_exc())


if __name__ == "__main__":
    main()
