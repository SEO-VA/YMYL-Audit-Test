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

logger = setup_logger(__name__)


def convert_violations_json_to_readable(json_content: str) -> str:
    """Convert JSON violations to readable markdown."""
    try:
        data = json.loads(json_content)
        violations = data.get("violations", [])
        
        if not violations:
            return "✅ **No violations found.**\n\n"
        
        result = ""
        for i, v in enumerate(violations, 1):
            emoji = {"critical": "🔴", "medium": "🟡", "low": "🔵"}.get(v.get("severity", "medium"), "🟡")
            result += f"""**{emoji} Violation {i}**
- **Issue:** {v.get('violation_type', 'Unknown')}
- **Text:** "{v.get('problematic_text', 'N/A')}"
- **Translation:** "{v.get('translation', 'N/A')}"
- **Reference:** Section {v.get('guideline_section', 'N/A')} (Page {v.get('page_number', 'N/A')})
- **Severity:** {v.get('severity', 'medium').title()}
- **Fix:** "{v.get('suggested_rewrite', 'No suggestion')}"

"""
        return result
    except:
        return json_content + "\n\n"


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
        report = f"""# YMYL Compliance Audit Report

    **Date:** {datetime.now().strftime("%Y-%m-%d")}

    ---

    """
        
        for i, result in enumerate(analysis_results, 1):
            if result.get("success"):
                readable_content = convert_violations_json_to_readable(result["content"], f"Section {i}")
                report += f"{readable_content}---\n\n"
            else:
                report += f"## Section {i}\n\n❌ **Analysis failed:** {result.get('error', 'Unknown error')}\n\n---\n\n"
        
        return report

    async def cleanup(self):
        """Clean up resources."""
        if self.assistant_client:
            await self.assistant_client.cleanup()