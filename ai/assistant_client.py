#!/usr/bin/env python3
"""
Optimized Assistant Client for YMYL Audit Tool
Fixed version that addresses performance and hanging request issues
"""

import asyncio
import aiohttp
import json
import time
from typing import List, Dict, Any, Tuple, Optional, Callable
from dataclasses import dataclass
import streamlit as st
from openai import AsyncOpenAI

# Import from config
try:
    from config.settings import ANALYZER_ASSISTANT_ID, MAX_PARALLEL_REQUESTS
except ImportError:
    ANALYZER_ASSISTANT_ID = "asst_WzODK9EapCaZoYkshT6x9xEH"
    MAX_PARALLEL_REQUESTS = 10


@dataclass
class ChunkAnalysis:
    """Result of analyzing a single chunk"""
    chunk_index: int
    content: str
    analysis: str
    success: bool
    error: Optional[str] = None
    processing_time: float = 0.0
    thread_id: Optional[str] = None
    run_id: Optional[str] = None


class OptimizedAssistantClient:
    """
    Optimized OpenAI Assistant client with fixed performance issues:
    - Proper async/await patterns
    - Controlled concurrency
    - Request cancellation support
    - Efficient polling with exponential backoff
    - Resource cleanup
    """
    
    def __init__(self, api_key: str = None):
        # Get API key from Streamlit secrets or parameter
        if api_key:
            self.api_key = api_key
        elif hasattr(st, 'secrets') and 'openai_api_key' in st.secrets:
            self.api_key = st.secrets['openai_api_key']
        else:
            raise ValueError("OpenAI API key not found. Please set it in Streamlit secrets as 'openai_api_key'")
        
        self.assistant_id = ANALYZER_ASSISTANT_ID
        self.client = None
        self.active_tasks = set()
        self.cancelled = False
        
        # Polling configuration
        self.max_polling_time = 180  # 3 minutes max per request
        self.initial_poll_delay = 0.5  # Start with 500ms
        self.max_poll_delay = 5.0  # Cap at 5 seconds
        self.backoff_multiplier = 1.5  # Gradual backoff

    async def __aenter__(self):
        """Async context manager entry"""
        self.client = AsyncOpenAI(api_key=self.api_key)
        self.cancelled = False
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit with proper cleanup"""
        # Cancel all active tasks
        self.cancelled = True
        
        # Cancel and wait for all active tasks
        if self.active_tasks:
            for task in self.active_tasks:
                if not task.done():
                    task.cancel()
            
            # Wait for cancellations to complete (with timeout)
            try:
                await asyncio.wait_for(
                    asyncio.gather(*self.active_tasks, return_exceptions=True),
                    timeout=10.0
                )
            except asyncio.TimeoutError:
                pass  # Some tasks didn't cancel gracefully
        
        # Close the client
        if self.client:
            await self.client.close()

    def cancel_processing(self):
        """Cancel all ongoing processing"""
        self.cancelled = True

    async def analyze_chunk(self, chunk_content: str, chunk_index: int) -> ChunkAnalysis:
        """
        Analyze a single chunk with proper error handling and cancellation support
        """
        if self.cancelled:
            return ChunkAnalysis(
                chunk_index=chunk_index,
                content=chunk_content,
                analysis="",
                success=False,
                error="Processing cancelled"
            )
        
        start_time = time.time()
        thread_id = None
        run_id = None
        
        try:
            # Step 1: Create thread
            thread = await self.client.beta.threads.create()
            thread_id = thread.id
            
            if self.cancelled:
                return self._create_cancelled_result(chunk_index, chunk_content)
            
            # Step 2: Add message to thread
            await self.client.beta.threads.messages.create(
                thread_id=thread_id,
                role="user",
                content=f"Analyze this content section for YMYL compliance:\n\n{chunk_content}"
            )
            
            if self.cancelled:
                return self._create_cancelled_result(chunk_index, chunk_content)
            
            # Step 3: Create and run with assistant
            run = await self.client.beta.threads.runs.create(
                thread_id=thread_id,
                assistant_id=self.assistant_id
            )
            run_id = run.id
            
            if self.cancelled:
                return self._create_cancelled_result(chunk_index, chunk_content)
            
            # Step 4: Optimized polling with exponential backoff
            analysis_text = await self._poll_for_completion(thread_id, run_id)
            
            if analysis_text is None:
                return ChunkAnalysis(
                    chunk_index=chunk_index,
                    content=chunk_content,
                    analysis="",
                    success=False,
                    error="Analysis timed out or was cancelled",
                    processing_time=time.time() - start_time,
                    thread_id=thread_id,
                    run_id=run_id
                )
            
            return ChunkAnalysis(
                chunk_index=chunk_index,
                content=chunk_content,
                analysis=analysis_text,
                success=True,
                processing_time=time.time() - start_time,
                thread_id=thread_id,
                run_id=run_id
            )
            
        except Exception as e:
            return ChunkAnalysis(
                chunk_index=chunk_index,
                content=chunk_content,
                analysis="",
                success=False,
                error=f"Request failed: {str(e)}",
                processing_time=time.time() - start_time,
                thread_id=thread_id,
                run_id=run_id
            )

    async def _poll_for_completion(self, thread_id: str, run_id: str) -> Optional[str]:
        """
        Poll for run completion with optimized exponential backoff
        """
        poll_delay = self.initial_poll_delay
        polling_start = time.time()
        
        while time.time() - polling_start < self.max_polling_time:
            if self.cancelled:
                # Try to cancel the run
                try:
                    await self.client.beta.threads.runs.cancel(
                        thread_id=thread_id,
                        run_id=run_id
                    )
                except Exception:
                    pass  # Ignore cancellation errors
                return None
            
            try:
                # Check run status
                run = await self.client.beta.threads.runs.retrieve(
                    thread_id=thread_id,
                    run_id=run_id
                )
                
                if run.status == "completed":
                    # Get the assistant's response
                    messages = await self.client.beta.threads.messages.list(
                        thread_id=thread_id,
                        order="desc",
                        limit=1
                    )
                    
                    if messages.data and messages.data[0].role == "assistant":
                        content = messages.data[0].content
                        if content and hasattr(content[0], 'text'):
                            return content[0].text.value
                    
                    return "Analysis completed but no content found"
                
                elif run.status in ["failed", "cancelled", "expired"]:
                    return None
                
                elif run.status in ["queued", "in_progress", "requires_action"]:
                    # Handle requires_action status (shouldn't happen with file search only)
                    if run.status == "requires_action":
                        return None
                    
                    # Wait before next poll with exponential backoff
                    await asyncio.sleep(poll_delay)
                    poll_delay = min(poll_delay * self.backoff_multiplier, self.max_poll_delay)
                else:
                    # Unknown status
                    await asyncio.sleep(poll_delay)
                    
            except Exception as e:
                # On polling error, wait and retry
                await asyncio.sleep(poll_delay)
                poll_delay = min(poll_delay * self.backoff_multiplier, self.max_poll_delay)
        
        # Timed out
        return None

    async def process_chunks_parallel(
        self, 
        chunks: List[Dict[str, Any]], 
        progress_callback: Optional[Callable] = None
    ) -> Tuple[List[ChunkAnalysis], Dict[str, Any]]:
        """
        Process multiple chunks with controlled concurrency and proper cancellation
        """
        if not chunks:
            return [], {"total_chunks": 0, "successful": 0, "failed": 0}
        
        # Create semaphore to limit concurrent requests
        semaphore = asyncio.Semaphore(min(MAX_PARALLEL_REQUESTS, len(chunks)))
        
        async def process_single_chunk(chunk_data: Dict[str, Any], index: int) -> ChunkAnalysis:
            """Process single chunk with semaphore control"""
            async with semaphore:
                if self.cancelled:
                    return self._create_cancelled_result(index, chunk_data.get("content", ""))
                
                # Create task and register it
                task = asyncio.current_task()
                if task:
                    self.active_tasks.add(task)
                
                try:
                    result = await self.analyze_chunk(chunk_data.get("content", ""), index)
                    if progress_callback and not self.cancelled:
                        progress_callback(index + 1, len(chunks), result.success)
                    return result
                finally:
                    # Unregister task
                    if task and task in self.active_tasks:
                        self.active_tasks.discard(task)
        
        # Create all tasks
        tasks = [
            process_single_chunk(chunk, i) 
            for i, chunk in enumerate(chunks)
        ]
        
        # Process with proper cancellation handling
        try:
            results = await asyncio.gather(*tasks, return_exceptions=True)
        except Exception as e:
            # Handle any unexpected errors
            results = [ChunkAnalysis(
                chunk_index=i,
                content=chunks[i].get("content", ""),
                analysis="",
                success=False,
                error=f"Processing interrupted: {str(e)}"
            ) for i in range(len(chunks))]
        
        # Process results and handle exceptions
        analysis_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                analysis_results.append(ChunkAnalysis(
                    chunk_index=i,
                    content=chunks[i].get("content", ""),
                    analysis="",
                    success=False,
                    error=f"Processing exception: {str(result)}"
                ))
            elif isinstance(result, ChunkAnalysis):
                analysis_results.append(result)
            else:
                # Unexpected result type
                analysis_results.append(ChunkAnalysis(
                    chunk_index=i,
                    content=chunks[i].get("content", ""),
                    analysis="",
                    success=False,
                    error="Unexpected result type"
                ))
        
        # Calculate statistics
        successful = sum(1 for r in analysis_results if r.success)
        failed = len(analysis_results) - successful
        total_time = sum(r.processing_time for r in analysis_results)
        
        stats = {
            "total_chunks": len(chunks),
            "successful": successful,
            "failed": failed,
            "total_processing_time": total_time,
            "average_time_per_chunk": total_time / len(chunks) if chunks else 0,
            "cancelled": self.cancelled
        }
        
        return analysis_results, stats

    def generate_report(self, analysis_results: List[ChunkAnalysis]) -> str:
        """Generate comprehensive markdown report from analysis results"""
        if not analysis_results:
            return "# YMYL Audit Report\n\nNo content was analyzed."
        
        successful_analyses = [r for r in analysis_results if r.success]
        failed_analyses = [r for r in analysis_results if not r.success]
        
        report_lines = [
            "# YMYL Audit Report",
            "",
            "## Executive Summary",
            "",
            f"- **Total Sections Analyzed**: {len(analysis_results)}",
            f"- **Successfully Processed**: {len(successful_analyses)}",
            f"- **Failed to Process**: {len(failed_analyses)}",
        ]
        
        # Add cancellation notice if applicable
        if self.cancelled:
            report_lines.extend([
                f"- **Status**: Processing was cancelled",
                ""
            ])
        
        report_lines.append("")
        
        if failed_analyses:
            report_lines.extend([
                "## Processing Errors",
                ""
            ])
            for failed in failed_analyses:
                report_lines.extend([
                    f"### Section {failed.chunk_index + 1}",
                    f"**Error**: {failed.error}",
                    ""
                ])
        
        if successful_analyses:
            report_lines.extend([
                "## Content Analysis Results",
                ""
            ])
            for i, analysis in enumerate(successful_analyses):
                report_lines.extend([
                    f"## Section {analysis.chunk_index + 1}",
                    "",
                    analysis.analysis,
                    "",
                    "---",
                    ""
                ])
        
        return "\n".join(report_lines)

    def _create_cancelled_result(self, chunk_index: int, content: str) -> ChunkAnalysis:
        """Create result for cancelled processing"""
        return ChunkAnalysis(
            chunk_index=chunk_index,
            content=content,
            analysis="",
            success=False,
            error="Processing was cancelled"
        )

    def get_processing_status(self) -> Dict[str, Any]:
        """Get current processing status"""
        return {
            "assistant_id": self.assistant_id,
            "active_tasks": len(self.active_tasks),
            "cancelled": self.cancelled,
            "client_ready": self.client is not None
        }


# Async wrapper function for Streamlit integration
async def process_chunks_async(chunks: List[Dict[str, Any]], progress_callback=None) -> Tuple[str, Dict[str, Any]]:
    """
    Process chunks and return markdown report + statistics
    This replaces the problematic polling-based approach
    """
    async with OptimizedAssistantClient() as client:
        results, stats = await client.process_chunks_parallel(chunks, progress_callback)
        report = client.generate_report(results)
        return report, stats


# Cancellation support for Streamlit
_current_client = None

def cancel_current_processing():
    """Cancel any ongoing processing"""
    global _current_client
    if _current_client:
        _current_client.cancel_processing()

async def process_chunks_with_cancellation(chunks: List[Dict[str, Any]], progress_callback=None) -> Tuple[str, Dict[str, Any]]:
    """Process chunks with global cancellation support"""
    global _current_client
    
    async with OptimizedAssistantClient() as client:
        _current_client = client
        try:
            results, stats = await client.process_chunks_parallel(chunks, progress_callback)
            report = client.generate_report(results)
            return report, stats
        finally:
            _current_client = None
