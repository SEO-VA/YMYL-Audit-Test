#!/usr/bin/env python3
"""
Analysis Engine for YMYL Audit Tool

Orchestrates the complete AI analysis workflow including:
- Parallel processing of content chunks
- Result aggregation and report generation
- Progress tracking and error handling

FIXED: Progress calculation bug - now uses actual completion count instead of chunk indices
"""

import asyncio
import time
from datetime import datetime
from typing import List, Dict, Any, Optional, Callable
from ai.assistant_client import AssistantClient
from utils.json_utils import extract_big_chunks, parse_json_output, validate_chunk_structure
from utils.logging_utils import setup_logger, format_metrics
from config.settings import MAX_PARALLEL_REQUESTS

logger = setup_logger(__name__)


class AnalysisEngine:
    """
    Orchestrates AI-powered YMYL compliance analysis.
    
    Handles:
    - Parallel processing of content chunks
    - Progress tracking and reporting
    - Result aggregation and report generation
    - Error handling and recovery
    """
    
    def __init__(self, api_key: str, progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None):
        """
        Initialize the AnalysisEngine.
        
        Args:
            api_key (str): OpenAI API key
            progress_callback: Optional callback for progress updates
        """
        self.assistant_client = AssistantClient(api_key)
        self.progress_callback = progress_callback
        self.analysis_start_time = None
        self.analysis_stats = {}
        # FIXED: Add completion tracking variables
        self._completed_count = 0
        self._total_chunks = 0
        logger.info("AnalysisEngine initialized")

    async def process_json_content(self, json_output: str) -> Dict[str, Any]:
        """
        Process JSON output through complete AI analysis workflow.
        
        Args:
            json_output (str): JSON string from chunk processor
            
        Returns:
            dict: Complete analysis results with success status and report
        """
        logger.info("Starting JSON content analysis workflow")
        self.analysis_start_time = time.time()
        
        try:
            # Step 1: Parse and validate JSON
            self._update_progress("Parsing JSON content", 0.1)
            json_data = parse_json_output(json_output)
            
            if not json_data:
                return self._create_error_result("Failed to parse JSON content")
            
            if not validate_chunk_structure(json_data):
                return self._create_error_result("Invalid chunk structure in JSON data")
            
            # Step 2: Extract chunks
            self._update_progress("Extracting content chunks", 0.2)
            chunks = extract_big_chunks(json_data)
            
            if not chunks:
                return self._create_error_result("No chunks found in JSON data")
            
            logger.info(f"Extracted {len(chunks)} chunks for analysis")
            
            # FIXED: Initialize completion tracking
            self._completed_count = 0
            self._total_chunks = len(chunks)
            
            # Step 3: Process chunks in parallel
            self._update_progress(f"Analyzing {len(chunks)} chunks in parallel", 0.3)
            analysis_results = await self._process_chunks_parallel(chunks)
            
            # Step 4: Generate final report
            self._update_progress("Generating final report", 0.9)
            final_report = self._create_final_report(analysis_results, chunks)
            
            # Step 5: Calculate final statistics
            processing_time = time.time() - self.analysis_start_time
            stats = self._calculate_final_stats(analysis_results, processing_time)
            
            self._update_progress("Analysis complete", 1.0)
            logger.info(f"Analysis workflow completed successfully in {processing_time:.2f} seconds")
            
            return {
                "success": True,
                "report": final_report,
                "analysis_results": analysis_results,
                "statistics": stats,
                "processing_time": processing_time
            }
            
        except Exception as e:
            error_msg = f"Analysis workflow error: {str(e)}"
            logger.error(error_msg)
            return self._create_error_result(error_msg)

    async def _process_chunks_parallel(self, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Process multiple chunks in parallel with controlled concurrency.
        
        FIXED: Now uses asyncio.as_completed() for accurate progress tracking
        
        Args:
            chunks (list): List of chunk dictionaries
            
        Returns:
            list: List of analysis results
        """
        logger.info(f"Starting parallel analysis of {len(chunks)} chunks")
        
        # Create semaphore to limit concurrent requests
        semaphore = asyncio.Semaphore(MAX_PARALLEL_REQUESTS)
        
        async def process_single_chunk(chunk):
            async with semaphore:
                return await self.assistant_client.analyze_chunk(
                    chunk["text"], 
                    chunk["index"]
                )
        
        # Create tasks for all chunks
        tasks = [process_single_chunk(chunk) for chunk in chunks]
        
        # FIXED: Use asyncio.as_completed() for proper progress tracking
        results = []
        completed = 0
        
        # Process tasks as they complete (not in original order)
        for coro in asyncio.as_completed(tasks):
            result = await coro
            results.append(result)
            completed += 1
            
            # FIXED: Update progress based on actual completion count
            progress = 0.3 + (0.55 * completed / len(chunks))
            self._update_progress(f"Completed {completed}/{len(chunks)} chunk analyses", progress)
            
            # Log individual chunk completion with better info
            chunk_idx = result.get("chunk_index", "unknown")
            if result.get("success"):
                logger.info(f"Chunk {chunk_idx} analysis completed successfully ({completed}/{len(chunks)})")
            else:
                logger.warning(f"Chunk {chunk_idx} analysis failed: {result.get('error')} ({completed}/{len(chunks)})")
        
        # Sort results by chunk index to maintain order for final report
        results.sort(key=lambda x: x.get("chunk_index", 0))
        
        successful = len([r for r in results if r.get("success")])
        failed = len(results) - successful
        
        logger.info(f"Parallel processing completed: {successful} successful, {failed} failed")
        
        return results

    def _create_final_report(self, analysis_results: List[Dict[str, Any]], chunks: List[Dict[str, Any]]) -> str:
        """Create the final YMYL compliance report with proper section formatting."""
        
        # Keep your existing header exactly the same
        header = f"""# YMYL Compliance Audit Report
    **Audit Date:** {audit_date}
    ...
    ---
    """
        
        report_parts = [header]
        
        for result in analysis_results:
            if result.get("success"):
                content = result["content"]
                
                # SIMPLE: Just add ## before the first line if it's not already there
                lines = content.strip().split('\n')
                if lines and not lines[0].startswith('#'):
                    # Make first line a proper section header
                    section_header = f"## {lines[0]}"
                    content = '\n'.join([section_header] + lines[1:])
                
                report_parts.append(content)
                report_parts.append("\n---\n")  # Keep your existing separator
            else:
                # Keep your existing error handling
                report_parts.append(error_section)
        
        # Keep your existing summary
        report_parts.append(summary)
        return ''.join(report_parts)

    def _calculate_final_stats(self, analysis_results: List[Dict[str, Any]], processing_time: float) -> Dict[str, Any]:
        """
        Calculate final statistics for the analysis.
        
        Args:
            analysis_results (list): Analysis results
            processing_time (float): Total processing time
            
        Returns:
            dict: Statistics dictionary
        """
        successful_results = [r for r in analysis_results if r.get("success")]
        failed_results = [r for r in analysis_results if not r.get("success")]
        
        # Calculate timing statistics
        individual_times = [r.get("processing_time", 0) for r in successful_results if "processing_time" in r]
        avg_individual_time = sum(individual_times) / len(individual_times) if individual_times else 0
        
        # Calculate content statistics
        total_response_length = sum(r.get("response_length", 0) for r in successful_results)
        avg_response_length = total_response_length / len(successful_results) if successful_results else 0
        
        stats = {
            "total_chunks": len(analysis_results),
            "successful_analyses": len(successful_results),
            "failed_analyses": len(failed_results),
            "success_rate": len(successful_results) / len(analysis_results) * 100 if analysis_results else 0,
            "total_processing_time": processing_time,
            "average_time_per_chunk": processing_time / len(analysis_results) if analysis_results else 0,
            "average_individual_time": avg_individual_time,
            "total_response_length": total_response_length,
            "average_response_length": avg_response_length,
            "parallel_efficiency": processing_time < (len(analysis_results) * avg_individual_time * 0.5) if avg_individual_time > 0 else True
        }
        
        logger.info(f"Final statistics calculated: {format_metrics(stats)}")
        return stats

    def _create_error_result(self, error_message: str) -> Dict[str, Any]:
        """
        Create a standardized error result.
        
        Args:
            error_message (str): Error description
            
        Returns:
            dict: Error result structure
        """
        processing_time = time.time() - self.analysis_start_time if self.analysis_start_time else 0
        
        return {
            "success": False,
            "error": error_message,
            "report": None,
            "analysis_results": [],
            "statistics": {"error": error_message},
            "processing_time": processing_time
        }

    def _update_progress(self, message: str, progress: float):
        """
        Update progress and notify callback if available.
        
        Args:
            message (str): Progress message
            progress (float): Progress value (0.0 to 1.0)
        """
        progress_data = {
            "message": message,
            "progress": progress,
            "timestamp": datetime.now().isoformat()
        }
        
        logger.info(f"Progress update: {message} ({progress*100:.1f}%)")
        
        if self.progress_callback:
            try:
                self.progress_callback(progress_data)
            except Exception as e:
                logger.warning(f"Progress callback error: {str(e)}")

    async def validate_setup(self) -> Dict[str, Any]:
        """
        Validate that the analysis engine is properly configured.
        
        Returns:
            dict: Validation results
        """
        logger.info("Validating analysis engine setup")
        
        validation_results = {
            "api_key_valid": False,
            "assistant_accessible": False,
            "assistant_info": None,
            "errors": []
        }
        
        try:
            # Validate API key
            if self.assistant_client.validate_api_key():
                validation_results["api_key_valid"] = True
                logger.info("API key validation passed")
            else:
                validation_results["errors"].append("Invalid API key")
                logger.error("API key validation failed")
            
            # Get assistant info
            assistant_info = self.assistant_client.get_assistant_info()
            if assistant_info:
                validation_results["assistant_accessible"] = True
                validation_results["assistant_info"] = assistant_info
                logger.info(f"Assistant accessible: {assistant_info['name']}")
            else:
                validation_results["errors"].append("Assistant not accessible")
                logger.error("Assistant not accessible")
            
        except Exception as e:
            error_msg = f"Validation error: {str(e)}"
            validation_results["errors"].append(error_msg)
            logger.error(error_msg)
        
        return validation_results

    async def cleanup(self):
        """Clean up resources."""
        if self.assistant_client:
            await self.assistant_client.cleanup()
        logger.info("AnalysisEngine cleanup completed")