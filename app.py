"""
Updated app.py for Responses API integration
Removes all the complex Assistant/Thread management
"""
import streamlit as st
import asyncio
from typing import Dict, Any, List

# Your existing imports
from extractors.content_extractor import ContentExtractor
from processors.chunk_processor import ChunkProcessor
from exporters.export_manager import ExportManager
from ui.components import (
    create_page_header, create_sidebar_config, 
    create_url_input_section, create_results_tabs
)
from utils.json_utils import extract_big_chunks, parse_json_output

# New simplified AI client
from ai.responses_client import process_chunks_async


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
        
        chunks = extract_big_chunks(json_output)
        st.success(f"✅ Content chunked: {len(chunks)} sections identified")
    
    # Store in session state for AI processing
    st.session_state.chunks = chunks
    st.session_state.url = url
    
    # Step 3: AI Analysis (Optional)
    st.markdown("### 🤖 AI Analysis")
    
    col1, col2 = st.columns([1, 2])
    with col1:
        if st.button("🧠 Analyze with AI", type="secondary"):
            process_ai_analysis_async()
    
    with col2:
        st.info(f"Ready to analyze {len(chunks)} content sections")
    
    # Always show chunked results
    display_chunked_results(chunks)


def process_ai_analysis_async():
    """
    Process AI analysis using the new Responses API
    Much simpler than the previous approach
    """
    if "chunks" not in st.session_state:
        st.error("❌ No chunks available for analysis")
        return
    
    chunks = st.session_state.chunks
    
    # Progress tracking
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    def progress_callback(completed: int, total: int, success: bool):
        """Update progress in real-time"""
        progress = completed / total
        progress_bar.progress(progress)
        status_text.text(f"Processing: {completed}/{total} chunks ({'✅' if success else '❌'})")
    
    # Run async processing
    try:
        with st.spinner("🧠 Analyzing content with AI..."):
            # Run the async function
            report, stats = asyncio.run(
                process_chunks_async(chunks, progress_callback)
            )
        
        # Clear progress indicators
        progress_bar.empty()
        status_text.empty()
        
        # Store results
        st.session_state.ai_report = report
        st.session_state.ai_stats = stats
        
        # Show success message
        st.success(f"✅ AI Analysis Complete!")
        st.info(f"📊 Processed {stats['successful']}/{stats['total_chunks']} sections in {stats.get('total_processing_time', 0):.1f}s")
        
        # Display results
        display_ai_results(report, stats)
        
    except Exception as e:
        progress_bar.empty()
        status_text.empty()
        st.error(f"❌ AI Analysis failed: {str(e)}")


def display_chunked_results(chunks: List[Dict[str, Any]]):
    """Display the chunked content results"""
    if not chunks:
        return
    
    st.markdown("### 📄 Content Sections")
    
    for i, chunk in enumerate(chunks):
        with st.expander(f"Section {i+1}: {chunk.get('title', 'Untitled')} ({len(chunk.get('content', ''))} chars)"):
            st.markdown(f"**Content Preview:**")
            preview = chunk.get('content', '')[:500]
            if len(chunk.get('content', '')) > 500:
                preview += "..."
            st.text(preview)


def display_ai_results(report: str, stats: Dict[str, Any]):
    """Display AI analysis results with export options"""
    
    # Create tabs for different views
    tabs = st.tabs(["📋 Full Report", "📊 Statistics", "📥 Downloads"])
    
    with tabs[0]:
        st.markdown("### 🔍 YMYL Compliance Analysis")
        st.markdown(report)
    
    with tabs[1]:
        st.markdown("### 📈 Processing Statistics")
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Sections", stats.get('total_chunks', 0))
        with col2:
            st.metric("Successful", stats.get('successful', 0))
        with col3:
            st.metric("Failed", stats.get('failed', 0))
        with col4:
            st.metric("Avg Time/Section", f"{stats.get('average_time_per_chunk', 0):.2f}s")
    
    with tabs[2]:
        st.markdown("### 💾 Export Analysis Report")
        
        if st.button("📥 Generate Export Files", type="secondary"):
            generate_exports(report, st.session_state.get('url', 'Unknown URL'))


def generate_exports(report_content: str, url: str):
    """Generate export files in multiple formats"""
    
    with st.spinner("📄 Generating export files..."):
        try:
            export_manager = ExportManager()
            
            # Generate all formats
            results = export_manager.export_all_formats(
                content=report_content,
                title=f"YMYL Audit Report - {url}",
                formats=["html", "pdf", "word", "markdown"]
            )
            
            # Create download buttons
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                if results["html"]["success"]:
                    st.download_button(
                        "📄 HTML", 
                        data=results["html"]["content"], 
                        file_name=results["html"]["filename"],
                        mime="text/html"
                    )
            
            with col2:
                if results["pdf"]["success"]:
                    st.download_button(
                        "📑 PDF", 
                        data=results["pdf"]["content"], 
                        file_name=results["pdf"]["filename"],
                        mime="application/pdf"
                    )
            
            with col3:
                if results["word"]["success"]:
                    st.download_button(
                        "📝 Word", 
                        data=results["word"]["content"], 
                        file_name=results["word"]["filename"],
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                    )
            
            with col4:
                if results["markdown"]["success"]:
                    st.download_button(
                        "📋 Markdown", 
                        data=results["markdown"]["content"], 
                        file_name=results["markdown"]["filename"],
                        mime="text/markdown"
                    )
            
            st.success("✅ Export files generated successfully!")
            
        except Exception as e:
            st.error(f"❌ Export generation failed: {str(e)}")


if __name__ == "__main__":
    main()
