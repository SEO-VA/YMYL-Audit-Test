"""
AI Analysis using OpenAI Responses API
Replaces the complex Assistant + Thread + Run architecture
"""
import asyncio
import aiohttp
from typing import List, Dict, Any, Tuple, Callable, Optional
import json
import time
from dataclasses import dataclass

from config.settings import OPENAI_API_KEY, MAX_PARALLEL_REQUESTS


@dataclass
class ChunkAnalysis:
    """Result of analyzing a single chunk"""
    chunk_index: int
    content: str
    analysis: str
    success: bool
    error: Optional[str] = None
    processing_time: float = 0.0


class ResponsesClient:
    """
    Simplified AI client using OpenAI's Responses API
    Replaces the complex Assistant/Thread/Run architecture
    """
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or OPENAI_API_KEY
        self.base_url = "https://api.openai.com/v1"
        self.session = None
        
        # YMYL Analysis Instructions
        self.instructions = """You are to adopt the persona of a world-class SEO and content compliance auditor. You have 15 years of specialized experience in high-stakes YMYL (Your Money or Your Life) topics, with a primary focus on the global online gambling and casino industry. Your analysis is rooted in a deep, practical understanding of Google's Search Quality Rater Guidelines (SQRG) and its public documentation on E-E-A-T (Experience, Expertise, Authoritativeness, Trustworthiness).

Your core mission is to protect end-users and ensure content is responsible, helpful, and compliant. You are meticulous, evidence-based, and your feedback is always actionable.

//-- MASTER INSTRUCTIONS --//

Task: Conduct a comprehensive audit of the provided content section, basing your analysis strictly and exclusively on the provided Google guidelines PDF. You will analyze the text section thoroughly, identifying all violations related to E-E-A-T and YMYL principles specific to the casino niche. For every issue found, you must provide a detailed breakdown. If a section is compliant, you will acknowledge it.

IMPORTANT: You must also provide a relevant, descriptive name for this content section at the beginning of your analysis (e.g., "Welcome Bonus Section", "Payment Methods Section", "Responsible Gambling Section", etc.)

Guiding Principles for Your Analysis:

Be Exhaustive: Review every sentence. Do not skim. Assume the content is for a live, regulated market where user safety and regulatory compliance are paramount.

Evidence is Mandatory: You must always quote the exact text that is problematic. No exceptions.

Go Beyond Identification: Do not just name the guideline being violated. You must provide a brief rationale explaining why the specific text violates that guideline in the context of online gambling.

Severity Assessment: For each issue, you must assign a severity level:

Critical: Poses a direct risk to user safety, is potentially illegal, or is a major violation of trust (e.g., promoting gambling as a financial solution, targeting minors, missing responsible gambling info).

High: Seriously misleads the user or severely damages E-E-A-T (e.g., inaccurate RTPs, unsubstantiated claims of "guaranteed wins," hiding affiliate links).

Medium: A clear E-E-A-T issue that needs correction but is less severe (e.g., slightly outdated bonus info, overly casual language that downplays risk).

Low: A minor issue or an opportunity for improvement (e.g., could add more author info, could cite sources better).

Solutions-Oriented: Your suggestions must be concrete and practical. Your rewritten examples must be ready to be copied and pasted.

//-- OUTPUT STRUCTURE & FORMATTING --//

You will generate a single, structured analysis in English. Your output must be meticulously formatted using markdown to be as clear, scannable, and comfortable to read as possible for a human reviewer.

Start with:
# [Descriptive Section Name]

Then provide your analysis:

(If no issues are found)
✅ **No issues were identified**

(If issues are found)
Create a distinct "Issue Card" for each violation identified in the section. Use a horizontal rule --- to separate multiple issue cards.

Issue Card Template:

[Severity Emoji] **[SEVERITY LEVEL] ISSUE**

"[Quote the exact problematic text here]"

Guideline Violated: [Name the specific Google guideline from the provided PDF]

Reason: [Explain *why* this text violates the guideline in 1-2 clear, concise sentences.]

Violation Type: [E-E-A-T: Experience / Expertise / Authoritativeness / Trustworthiness OR YMYL: Downplaying Risk / Financial Solution Claim / etc.]

Recommendation: [Describe the strategic fix. E.g., "Rephrase the claim to be factually accurate and add a disclaimer about the inherent risks of gambling."]

"[Provide the fully rewritten, compliant version of the text. This should be ready to copy and paste.]"

Severity Emojis:
🔴 CRITICAL
🟠 HIGH  
🟡 MEDIUM
🔵 LOW

Your entire audit must be based exclusively on the guidelines within the provided PDF. Do not use any outside knowledge or other versions of Google's guidelines."""

    async def __aenter__(self):
        """Async context manager entry"""
        self.session = aiohttp.ClientSession(
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            },
            timeout=aiohttp.ClientTimeout(total=120)
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()

    async def analyze_chunk(self, chunk_content: str, chunk_index: int) -> ChunkAnalysis:
        """
        Analyze a single chunk using the Responses API
        No threading, no polling - just direct response
        """
        start_time = time.time()
        
        try:
            payload = {
                "model": "gpt-4o",
                "instructions": self.instructions,
                "input": f"Analyze this content section for YMYL compliance:\n\n{chunk_content}",
                "max_completion_tokens": 4000  # Prevent runaway costs
            }
            
            async with self.session.post(f"{self.base_url}/responses", json=payload) as response:
                if response.status == 200:
                    result = await response.json()
                    analysis_text = result.get("output", [{}])[0].get("content", [{}])[0].get("text", "")
                    
                    return ChunkAnalysis(
                        chunk_index=chunk_index,
                        content=chunk_content,
                        analysis=analysis_text,
                        success=True,
                        processing_time=time.time() - start_time
                    )
                else:
                    error_text = await response.text()
                    return ChunkAnalysis(
                        chunk_index=chunk_index,
                        content=chunk_content,
                        analysis="",
                        success=False,
                        error=f"API Error {response.status}: {error_text}",
                        processing_time=time.time() - start_time
                    )
                    
        except Exception as e:
            return ChunkAnalysis(
                chunk_index=chunk_index,
                content=chunk_content,
                analysis="",
                success=False,
                error=f"Request failed: {str(e)}",
                processing_time=time.time() - start_time
            )

    async def process_chunks_parallel(
        self, 
        chunks: List[Dict[str, Any]], 
        progress_callback: Optional[Callable] = None
    ) -> Tuple[List[ChunkAnalysis], Dict[str, Any]]:
        """
        Process multiple chunks in parallel with controlled concurrency
        Much simpler than the previous Assistant-based approach
        """
        if not chunks:
            return [], {"total_chunks": 0, "successful": 0, "failed": 0}
        
        # Create semaphore to limit concurrent requests
        semaphore = asyncio.Semaphore(min(MAX_PARALLEL_REQUESTS, len(chunks)))
        
        async def process_single_chunk(chunk_data: Dict[str, Any], index: int) -> ChunkAnalysis:
            async with semaphore:
                result = await self.analyze_chunk(chunk_data.get("content", ""), index)
                if progress_callback:
                    progress_callback(index + 1, len(chunks), result.success)
                return result
        
        # Process all chunks concurrently
        tasks = [
            process_single_chunk(chunk, i) 
            for i, chunk in enumerate(chunks)
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Handle any exceptions that occurred
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
            else:
                analysis_results.append(result)
        
        # Calculate statistics
        successful = sum(1 for r in analysis_results if r.success)
        failed = len(analysis_results) - successful
        total_time = sum(r.processing_time for r in analysis_results)
        
        stats = {
            "total_chunks": len(chunks),
            "successful": successful,
            "failed": failed,
            "total_processing_time": total_time,
            "average_time_per_chunk": total_time / len(chunks) if chunks else 0
        }
        
        return analysis_results, stats

    def generate_report(self, analysis_results: List[ChunkAnalysis]) -> str:
        """
        Generate a comprehensive markdown report from analysis results
        """
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
            ""
        ]
        
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


# Async wrapper function for Streamlit integration
async def process_chunks_async(chunks: List[Dict[str, Any]], progress_callback=None) -> Tuple[str, Dict[str, Any]]:
    """
    Process chunks and return markdown report + statistics
    This replaces the entire AnalysisEngine class
    """
    async with ResponsesClient() as client:
        results, stats = await client.process_chunks_parallel(chunks, progress_callback)
        report = client.generate_report(results)
        return report, stats
