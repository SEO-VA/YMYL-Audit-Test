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
from utils.json_utils import convert_violations_json_to_readable  # ✅ IMPORT FROM UTILS - NO LOCAL FUNCTION
from utils.logging_utils import setup_logger

logger = setup_logger(__name__)


class AnalysisEngine:
    """Minimal AI analysis engine."""
    
    def __init__(self, api_key: str, progress_callback: Optional[Callable] = None):
        self.assistant_client = AssistantClient(api_key)
        self.progress_callback = progress_callback
        self.analysis_start_time = None
        self.chunks_data = None  # NEW: Store original chunks

    async def process_json_content(self, json_output: str) -> Dict[str, Any]:
        """Process JSON through AI analysis."""
        logger.info("Starting analysis")
        self.analysis_start_time = time.time()
        
        try:
            # Parse JSON
            json_data = parse_json_output(json_output)
            if not json_data:
                return {"success": False, "error": "Invalid JSON"}
            
            # Extract chunks and store for later use
            chunks = extract_big_chunks(json_data)
            if not chunks:
                return {"success": False, "error": "No chunks found"}
            
            self.chunks_data = chunks  # NEW: Store for report generation
            
            # Process chunks
            analysis_results = await self._process_chunks_parallel(chunks)
            
            # Create report with grouping
            report = self._create_final_report_grouped(analysis_results)  # CHANGED
            
            processing_time = time.time() - self.analysis_start_time
            
            return {
                "success": True,
                "report": report,
                "analysis_results": analysis_results,
                "processing_time": processing_time
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _create_final_report_grouped(self, analysis_results: List[Dict[str, Any]]) -> str:
        """Create final report with grouped violations by content sections."""
        from datetime import datetime
        from utils.json_utils import create_grouped_violations_report  # NEW IMPORT
        
        report = f"""# YMYL Compliance Audit Report

**Date:** {datetime.now().strftime("%Y-%m-%d")}

---

"""
        
        # Create grouped violations report
        grouped_violations = create_grouped_violations_report(analysis_results, self.chunks_data)
        report += grouped_violations
        
        return report

    async def cleanup(self):
        """Clean up resources."""
        if self.assistant_client:
            await self.assistant_client.cleanup()