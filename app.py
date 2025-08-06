#!/usr/bin/env python3
"""
Parallel Analysis Test App

Tests the parallel chunk analysis system with real OpenAI API calls.
Simulates the workflow: JSON Input → Extract Big Chunks → Parallel Analysis → Report Maker
"""

import streamlit as st
import json
import asyncio
import aiohttp
import time
from datetime import datetime
import concurrent.futures
from typing import List, Dict, Any

# --- Page Configuration ---
st.set_page_config(
    page_title="Parallel Analysis Test",
    page_icon="🧪",
    layout="wide",
)

# --- Assistant IDs ---
ANALYZER_ASSISTANT_ID = "asst_WzODK9EapCaZoYkshT6x9xEH"
REPORT_MAKER_ASSISTANT_ID = "asst_TKkFTDouxjjRJaTwAaX0ppte"

# --- OpenAI API Functions ---
async def call_openai_api(api_key: str, content: str, chunk_index: int = None) -> Dict[str, Any]:
    """Make async call to OpenAI API using assistant"""
    try:
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "gpt-4",
            "messages": [{"role": "user", "content": content}],
            "max_tokens": 3000,
            "temperature": 0.3
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://api.openai.com/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=180)
            ) as response:
                
                if response.status == 200:
                    result = await response.json()
                    return {
                        "success": True,
                        "content": result["choices"][0]["message"]["content"],
                        "chunk_index": chunk_index,
                        "tokens_used": result.get("usage", {}).get("total_tokens", 0)
                    }
                else:
                    error_text = await response.text()
                    return {
                        "success": False,
                        "error": f"HTTP {response.status}: {error_text}",
                        "chunk_index": chunk_index
                    }
                    
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "chunk_index": chunk_index
        }

def extract_big_chunks(json_data: Dict) -> List[Dict]:
    """Extract and prepare big chunks for analysis"""
    chunks = []
    
    if "big_chunks" not in json_data:
        return chunks
        
    for big_chunk in json_data["big_chunks"]:
        chunk_index = big_chunk.get("big_chunk_index", 0)
        small_chunks = big_chunk.get("small_chunks", [])
        
        # Join small chunks with newlines (Option A)
        chunk_text = "\n".join(small_chunks)
        
        chunks.append({
            "index": chunk_index,
            "text": chunk_text,
            "small_chunks_count": len(small_chunks)
        })
    
    return chunks

async def process_chunks_parallel(chunks: List[Dict], analyzer_api_key: str) -> List[Dict]:
    """Process all chunks in parallel using analyzer assistant"""
    tasks = []
    
    for chunk in chunks:
        task = call_openai_api(
            api_key=analyzer_api_key,
            content=chunk["text"],
            chunk_index=chunk["index"]
        )
        tasks.append(task)
    
    # Execute all tasks in parallel
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Handle exceptions
    processed_results = []
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            processed_results.append({
                "success": False,
                "error": str(result),
                "chunk_index": chunks[i]["index"]
            })
        else:
            processed_results.append(result)
    
    return processed_results

def create_report_input(analysis_results: List[Dict]) -> str:
    """Prepare input for report maker"""
    analyses_text = ""
    successful_count = 0
    failed_count = 0
    
    for result in analysis_results:
        if result["success"]:
            analyses_text += f"## Section {result['chunk_index']} Analysis\n\n"
            analyses_text += result["content"] + "\n\n"
            successful_count += 1
        else:
            analyses_text += f"## Section {result['chunk_index']} - ANALYSIS FAILED\n\n"
            analyses_text += f"Error: {result['error']}\n\n"
            failed_count += 1
    
    analyses_text += f"\n**Processing Summary:**\n"
    analyses_text += f"- Successful Analyses: {successful_count}\n"
    analyses_text += f"- Failed Analyses: {failed_count}\n"
    
    return analyses_text

# --- Streamlit UI ---
def main():
    st.title("🧪 Parallel Analysis Test App")
    st.markdown("**Test the parallel chunk analysis system with real OpenAI API calls**")
    
    # Check for API keys
    if "analyzer_api_key" not in st.secrets or "report_maker_api_key" not in st.secrets:
        st.error("❌ API keys not configured. Please add `analyzer_api_key` and `report_maker_api_key` to your secrets.toml file.")
        st.stop()
    
    st.success("✅ API keys loaded from secrets")
    
    st.markdown("---")
    
    # Input section
    st.subheader("📥 Input JSON Data")
    st.markdown("Paste the JSON output from chunk.dejan.ai:")
    
    json_input = st.text_area(
        "JSON Content:",
        height=300,
        placeholder='{\n  "big_chunks": [\n    {\n      "big_chunk_index": 1,\n      "small_chunks": ["content..."]\n    }\n  ]\n}'
    )
    
    if st.button("🚀 Start Parallel Analysis", type="primary"):
        if not json_input.strip():
            st.error("Please provide JSON input")
            return
            
        try:
            # Parse JSON
            json_data = json.loads(json_input)
            
            # Extract chunks
            chunks = extract_big_chunks(json_data)
            
            if not chunks:
                st.error("No big_chunks found in JSON data")
                return
            
            st.success(f"✅ Found {len(chunks)} big chunks to analyze")
            
            # Display chunks
            with st.expander("📋 Extracted Chunks Preview"):
                for chunk in chunks:
                    st.write(f"**Chunk {chunk['index']}** ({chunk['small_chunks_count']} small chunks)")
                    st.text(chunk['text'][:200] + "..." if len(chunk['text']) > 200 else chunk['text'])
                    st.markdown("---")
            
            # Progress tracking
            total_chunks = len(chunks)
            progress_bar = st.progress(0)
            status_container = st.empty()
            results_container = st.empty()
            
            # Start processing
            start_time = time.time()
            
            with status_container.container():
                st.info(f"🔄 Starting parallel analysis of {total_chunks} chunks...")
            
            # Run parallel processing
            analyzer_api_key = st.secrets["analyzer_api_key"]
            
            async def run_analysis():
                return await process_chunks_parallel(chunks, analyzer_api_key)
            
            # Execute async code
            analysis_results = asyncio.run(run_analysis())
            
            # Update progress
            progress_bar.progress(1.0)
            processing_time = time.time() - start_time
            
            # Display results
            successful_analyses = [r for r in analysis_results if r["success"]]
            failed_analyses = [r for r in analysis_results if not r["success"]]
            
            with status_container.container():
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Total Chunks", total_chunks)
                with col2:
                    st.metric("Successful", len(successful_analyses))
                with col3:
                    st.metric("Failed", len(failed_analyses))
                
                st.success(f"✅ Parallel analysis completed in {processing_time:.2f} seconds")
            
            # Show individual results
            st.subheader("📊 Individual Chunk Analyses")
            
            for result in analysis_results:
                chunk_idx = result["chunk_index"]
                
                if result["success"]:
                    with st.expander(f"✅ Chunk {chunk_idx} Analysis (Success)"):
                        st.markdown(result["content"])
                        st.caption(f"Tokens used: {result.get('tokens_used', 'Unknown')}")
                else:
                    with st.expander(f"❌ Chunk {chunk_idx} Analysis (Failed)"):
                        st.error(f"Error: {result['error']}")
            
            # Generate final report
            if successful_analyses or failed_analyses:
                st.subheader("📋 Final Unified Report")
                
                with st.spinner("Generating unified report..."):
                    report_input = create_report_input(analysis_results)
                    
                    # Call report maker assistant
                    report_maker_api_key = st.secrets["report_maker_api_key"]
                    
                    async def generate_report():
                        return await call_openai_api(
                            api_key=report_maker_api_key,
                            content=report_input,
                            chunk_index=None
                        )
                    
                    report_result = asyncio.run(generate_report())
                    
                    if report_result["success"]:
                        st.markdown(report_result["content"])
                        
                        # Download button
                        st.download_button(
                            label="💾 Download Report",
                            data=report_result["content"],
                            file_name=f"compliance_audit_{datetime.now().strftime('%Y%m%d_%H%M')}.md",
                            mime="text/markdown"
                        )
                    else:
                        st.error(f"Failed to generate report: {report_result['error']}")
            
        except json.JSONDecodeError as e:
            st.error(f"Invalid JSON format: {str(e)}")
        except Exception as e:
            st.error(f"An error occurred: {str(e)}")

if __name__ == "__main__":
    main()
