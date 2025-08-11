#!/usr/bin/env python3
"""
Analysis Engine for YMYL Audit Tool

Orchestrates the complete AI analysis workflow including:
- Parallel processing of content chunks
- Result aggregation and report generation
- Progress tracking and error handling

FIXED: Progress calculation bug - now uses actual completion count instead of chunk indices
IMPROVED: Clean report generation using strict marker-based content extraction
ENHANCED: Aggressive content cleaning to remove any leaked metadata
"""

import asyncio
import time
import json
import re
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

    def _extract_clean_section_content(self, ai_response: str) -> Optional[str]:
        """
        Extract clean section content between SECTION markers with aggressive cleaning.
        
        Args:
            ai_response (str): Full AI response with markers
            
        Returns:
            str: Clean section content or None if not found
        """
        # Find main section markers
        start_marker = "<!-- SECTION_START -->"
        end_marker = "<!-- SECTION_END -->"
        
        start_idx = ai_response.find(start_marker)
        end_idx = ai_response.find(end_marker)
        
        if start_idx == -1 or end_idx == -1:
            logger.warning("Could not find SECTION markers in AI response")
            return None
        
        # Extract content between main markers ONLY
        clean_content = ai_response[start_idx + len(start_marker):end_idx].strip()
        
        # Aggressively remove any metadata-like content that might have leaked
        # Remove common patterns of unwanted content
        patterns_to_remove = [
            r'Language Detection:.*?(?=\n\n|\Z)',  # Language detection blocks
            r'Original Text:.*?(?=\n\n|\Z)',       # Original text blocks
            r'Translation:.*?(?=\n\n|\Z)',         # Translation blocks outside issues
            r'\{.*?"section_name".*?\}',           # JSON metadata blocks
            r'Processing Summary.*?(?=\n\n|\Z)',   # Processing summaries
            r'Report generated by.*?(?=\n\n|\Z)',   # Report footers
            r'Assistant ID:.*?(?=\n\n|\Z)',         # Assistant IDs
            r'Audit Date:.*?(?=\n\n|\Z)',          # Audit dates
            r'Content Type:.*?(?=\n\n|\Z)',        # Content type headers
            r'Analysis Method:.*?(?=\n\n|\Z)',     # Analysis method headers
            r'---+',                               # Excessive horizontal rules
        ]
        
        for pattern in patterns_to_remove:
            clean_content = re.sub(pattern, '', clean_content, flags=re.DOTALL | re.IGNORECASE)
        
        # Clean up excessive whitespace and newlines
        clean_content = re.sub(r'\n{3,}', '\n\n', clean_content)
        clean_content = clean_content.strip()
        
        # Ensure we still have valid content
        if not clean_content or len(clean_content) < 10:
            logger.warning("Extracted content is empty or too short after cleaning")
            return None
            
        return clean_content

    def _create_clean_error_section(self, chunk_index: Any) -> str:
        """
        Create clean error section that matches format.
        
        Args:
            chunk_index: Index of failed chunk
            
        Returns:
            str: Clean error section
        """
        return f"""## Section Analysis Failed (Chunk {chunk_index})
❌ Technical Error

Analysis could not be completed for this section.
Manual review recommended."""

    def _create_final_report(self, analysis_results: List[Dict[str, Any]], chunks: List[Dict[str, Any]]) -> str:
        """
        Create clean final report by assembling only clean section content.
        
        Args:
            analysis_results (list): Results from AI analysis
            chunks (list): Original chunk data
            
        Returns:
            str: Clean final report
        """
        logger.info("Creating final clean compliance report")
        
        # Minimal header only
        header = "# YMYL Compliance Audit Report\n\n"
        
        # Extract clean content from successful analyses
        clean_sections = []
        
        for result in analysis_results:
            if result.get("success"):
                clean_content = self._extract_clean_section_content(result["content"])
                if clean_content:
                    clean_sections.append(clean_content)
                else:
                    # Handle malformed sections with clean error
                    chunk_idx = result.get('chunk_index', 'Unknown')
                    clean_sections.append(self._create_clean_error_section(chunk_idx))
            else:
                # Handle failed analyses with clean error
                chunk_idx = result.get('chunk_index', 'Unknown')
                clean_sections.append(self._create_clean_error_section(chunk_idx))
        
        # Assemble final report
        if clean_sections:
            report_parts = [header]
            report_parts.extend(clean_sections)
            final_report = "\n---\n\n".join(report_parts)
        else:
            final_report = f"{header}❌ No sections could be analyzed. All chunks failed processing."
        
        logger.info(f"Final clean report generated: {len(final_report):,} characters")
        return final_report

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