#!/usr/bin/env python3
"""
Minimal Analysis Engine for YMYL Audit Tool
"""

import asyncio
import time
import json
from datetime import datetime
from typing import List, Dict, Any, Optional, Callable
from ai.assistant_client import AssistantClient
from utils.json_utils import extract_big_chunks, parse_json_output
from utils.logging_utils import setup_logger
from utils.json_utils import convert_violations_json_to_readable

logger = setup_logger(__name__)

class AnalysisEngine:
    """Minimal AI analysis engine."""
    
    def __init__(self, api_key: str, progress_callback: Optional[Callable] = None):
        self.assistant_client = AssistantClient(api_key)
        self.progress_callback = progress_callback
        self.analysis_start_time = None

    async def process_json_content(self, json_output: str) -> Dict[str, Any]:
        """Process JSON through AI analysis."""
        logger.info("Starting analysis")
        self.analysis_start_time = time.time()
        
        try:
            # Parse JSON
            json_data = parse_json_output(json_output)
            if not json_data:
                return {"success": False, "error": "Invalid JSON"}
            
            # Extract chunks
            chunks = extract_big_chunks(json_data)
            if not chunks:
                return {"success": False, "error": "No chunks found"}
            
            # Process chunks
            analysis_results = await self._process_chunks_parallel(chunks)
            
            # Create report
            report = self._create_final_report(analysis_results)
            
            processing_time = time.time() - self.analysis_start_time
            
            return {
                "success": True,
                "report": report,
                "analysis_results": analysis_results,
                "processing_time": processing_time
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _process_chunks_parallel(self, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process chunks in parallel."""
        semaphore = asyncio.Semaphore(10)  # Max 10 parallel
        
        async def process_chunk(chunk):
            async with semaphore:
                return await self.assistant_client.analyze_chunk(chunk["text"], chunk["index"])
        
        tasks = [process_chunk(chunk) for chunk in chunks]
        results = await asyncio.gather(*tasks)
        
        # Sort by chunk index
        results.sort(key=lambda x: x.get("chunk_index", 0))
        return results

def _create_final_report(self, analysis_results: List[Dict[str, Any]]) -> str:
    """Create final report from analysis results."""
    
    # 🔍 SAFE DEBUG: Only runs when method is called, not at import time
    print("=" * 60)
    print("DEBUG: Final report generation starting")
    
    # Check which function we're using
    try:
        import inspect
        function_module = convert_violations_json_to_readable.__module__
        function_file = convert_violations_json_to_readable.__code__.co_filename
        function_source = inspect.getsource(convert_violations_json_to_readable)
        
        print(f"DEBUG: Function module: {function_module}")
        print(f"DEBUG: Function file: {function_file}")
        print(f"DEBUG: Function source contains 'Translation of Fix': {'Translation of Fix' in function_source}")
        
    except Exception as e:
        print(f"DEBUG: Error inspecting function: {e}")
    
    report = f"""# YMYL Compliance Audit Report

**Date:** {datetime.now().strftime("%Y-%m-%d")}

---

"""
    
    for i, result in enumerate(analysis_results, 1):
        if result.get("success"):
            # 🔍 DEBUG: Check each result
            raw_content = result["content"]
            print(f"DEBUG: Raw contains 'rewrite_translation': {'rewrite_translation' in raw_content}")
            
            readable_content = convert_violations_json_to_readable(raw_content)
            print(f"DEBUG: Output contains 'Translation of Fix': {'Translation of Fix' in readable_content}")
            
            report += f"{readable_content}---\n\n"
        else:
            report += f"## Section {i}\n\n❌ **Analysis failed:** {result.get('error', 'Unknown error')}\n\n---\n\n"
    
    return report