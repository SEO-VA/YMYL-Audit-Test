#!/usr/bin/env python3
"""
Analysis Engine for YMYL Audit Tool
UPDATED: Single request architecture - sends full content in one API call
"""

import asyncio
import time
import json
from datetime import datetime
from typing import Dict, Any, Optional, Callable
from ai.assistant_client import AssistantClient
from utils.json_utils import parse_json_output, convert_ai_response_to_markdown
from utils.logging_utils import setup_logger

logger = setup_logger(__name__)


class AnalysisEngine:
    """Single-request AI analysis engine."""
    
    def __init__(self, api_key: str, progress_callback: Optional[Callable] = None):
        self.assistant_client = AssistantClient(api_key)
        self.progress_callback = progress_callback
        self.analysis_start_time = None

    async def process_json_content(self, json_output: str) -> Dict[str, Any]:
        """Process JSON through AI analysis in single request."""
        logger.info("Starting single-request analysis")
        self.analysis_start_time = time.time()
        
        try:
            # Parse JSON
            json_data = parse_json_output(json_output)
            if not json_data:
                return {"success": False, "error": "Invalid JSON"}
            
            # Validate chunk structure
            big_chunks = json_data.get('big_chunks', [])
            if not big_chunks:
                return {"success": False, "error": "No chunks found"}
            
            # Update progress
            if self.progress_callback:
                self.progress_callback({
                    'progress': 0.1,
                    'message': f'Sending {len(big_chunks)} chunks for analysis...'
                })
            
            # Single AI request with full content
            ai_result = await self.assistant_client.analyze_full_content(json_output)
            
            if not ai_result.get('success'):
                return {"success": False, "error": ai_result.get('error', 'AI analysis failed')}
            
            # Update progress
            if self.progress_callback:
                self.progress_callback({
                    'progress': 0.8,
                    'message': 'Converting AI response to report...'
                })
            
            # Convert AI response to markdown report
            ai_response_data = ai_result['content']
            report = convert_ai_response_to_markdown(ai_response_data)
            
            # Update progress
            if self.progress_callback:
                self.progress_callback({
                    'progress': 1.0,
                    'message': 'Analysis complete!'
                })
            
            processing_time = time.time() - self.analysis_start_time
            
            return {
                "success": True,
                "report": report,
                "ai_response": ai_response_data,
                "processing_time": processing_time,
                "statistics": {
                    "total_chunks": len(big_chunks),
                    "total_processing_time": processing_time,
                    "successful_analyses": 1,
                    "failed_analyses": 0,
                    "success_rate": 100.0
                }
            }
            
        except Exception as e:
            error_msg = f"Analysis engine error: {str(e)}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}

    async def cleanup(self):
        """Clean up resources."""
        if self.assistant_client:
            await self.assistant_client.cleanup()