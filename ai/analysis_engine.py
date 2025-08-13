#!/usr/bin/env python3
"""
Minimal Analysis Engine for YMYL Audit Tool
Updated to support content_name from AI prompt
"""

import asyncio
import time
import json
from datetime import datetime
from typing import List, Dict, Any, Optional, Callable
from ai.assistant_client import AssistantClient
from utils.json_utils import extract_big_chunks, parse_json_output
from utils.json_utils import create_grouped_violations_report  # NEW IMPORT
from utils.logging_utils import setup_logger

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
            
            # Create report using new grouped format
            report = self._create_final_report_with_content_names(analysis_results)
            
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

    def _create_final_report_with_content_names(self, analysis_results: List[Dict[str, Any]]) -> str:
        """
        Create final report using content_name from AI responses.
        Much simpler than the old complex grouping logic.
        """
        report = f"""# YMYL Compliance Audit Report

**Date:** {datetime.now().strftime("%Y-%m-%d")}

---

"""
        
        # Create summary statistics
        total_violations = 0
        critical_count = 0
        sections_with_violations = 0
        successful_analyses = 0
        failed_analyses = 0
        
        for result in analysis_results:
            if result.get('success'):
                successful_analyses += 1
                try:
                    ai_response = json.loads(result['content'])
                    violations = ai_response.get('violations', [])
                    if violations:
                        sections_with_violations += 1
                        total_violations += len(violations)
                        critical_count += len([v for v in violations if v.get('severity') == 'critical'])
                except:
                    pass
            else:
                failed_analyses += 1
        

        
        # Add grouped violations using the new function
        grouped_violations = create_grouped_violations_report(analysis_results)
        report += grouped_violations
        
        # Add processing summary
        if failed_analyses > 0:
            report += f"""## 📈 Processing Summary

**Failed Analyses:** {failed_analyses}

"""
            for i, result in enumerate(analysis_results, 1):
                if not result.get('success'):
                    error = result.get('error', 'Unknown error')
                    report += f"- **Chunk {i}:** {error}\n"
            
            report += "\n"
        
        return report

    async def cleanup(self):
        """Clean up resources."""
        if self.assistant_client:
            await self.assistant_client.cleanup()