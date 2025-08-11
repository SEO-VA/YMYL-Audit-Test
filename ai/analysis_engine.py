#!/usr/bin/env python3
"""
Analysis Engine for YMYL Audit Tool

Orchestrates the complete AI analysis workflow including:
- Parallel processing of content chunks
- Intelligent result parsing and cleaning
- Clean report generation
"""

import asyncio
import time
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
    Orchestrates AI-powered YMYL compliance analysis with intelligent parsing.
    """
    
    def __init__(self, api_key: str, progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None):
        self.assistant_client = AssistantClient(api_key)
        self.progress_callback = progress_callback
        self.analysis_start_time = None
        self._completed_count = 0
        self._total_chunks = 0
        logger.info("AnalysisEngine initialized")

    async def process_json_content(self, json_output: str) -> Dict[str, Any]:
        logger.info("Starting JSON content analysis workflow")
        self.analysis_start_time = time.time()
        
        try:
            # Parse and validate JSON
            self._update_progress("Parsing JSON content", 0.1)
            json_data = parse_json_output(json_output)
            
            if not json_data:
                return self._create_error_result("Failed to parse JSON content")
            
            if not validate_chunk_structure(json_data):
                return self._create_error_result("Invalid chunk structure in JSON data")
            
            # Extract chunks
            self._update_progress("Extracting content chunks", 0.2)
            chunks = extract_big_chunks(json_data)
            
            if not chunks:
                return self._create_error_result("No chunks found in JSON data")
            
            logger.info(f"Extracted {len(chunks)} chunks for analysis")
            
            self._completed_count = 0
            self._total_chunks = len(chunks)
            
            # Process chunks in parallel
            self._update_progress(f"Analyzing {len(chunks)} chunks in parallel", 0.3)
            analysis_results = await self._process_chunks_parallel(chunks)
            
            # Generate final report
            self._update_progress("Generating final report", 0.9)
            final_report = self._create_final_report(analysis_results, chunks)
            
            # Calculate final statistics
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
        logger.info(f"Starting parallel analysis of {len(chunks)} chunks")
        
        semaphore = asyncio.Semaphore(MAX_PARALLEL_REQUESTS)
        
        async def process_single_chunk(chunk):
            async with semaphore:
                return await self.assistant_client.analyze_chunk(
                    chunk["text"], 
                    chunk["index"]
                )
        
        tasks = [process_single_chunk(chunk) for chunk in chunks]
        
        results = []
        completed = 0
        
        for coro in asyncio.as_completed(tasks):
            result = await coro
            results.append(result)
            completed += 1
            
            progress = 0.3 + (0.55 * completed / len(chunks))
            self._update_progress(f"Completed {completed}/{len(chunks)} chunk analyses", progress)
            
            chunk_idx = result.get("chunk_index", "unknown")
            if result.get("success"):
                logger.info(f"Chunk {chunk_idx} analysis completed successfully ({completed}/{len(chunks)})")
            else:
                logger.warning(f"Chunk {chunk_idx} analysis failed: {result.get('error')} ({completed}/{len(chunks)})")
        
        results.sort(key=lambda x: x.get("chunk_index", 0))
        
        successful = len([r for r in results if r.get("success")])
        failed = len(results) - successful
        
        logger.info(f"Parallel processing completed: {successful} successful, {failed} failed")
        
        return results

    def _extract_section_name(self, content: str) -> str:
        """
        Extract section name using flexible pattern matching.
        """
        # Try multiple patterns
        patterns = [
            r'^\[(.+?)\]',  # [Section Name]
            r'^##\s+(.+?)(?:\n|$)',  # ## Section Name
            r'^([A-Za-z][^(?:\n|$)',  # Section Name at start
        ]
        
        for pattern in patterns:
            match = re.search(pattern, content, re.MULTILINE)
            if match:
                return match.group(1).strip()
        
        return "Unknown Section"

    def _detect_language_flag(self, section_name: str) -> str:
        """
        Detect language and return appropriate flag emoji.
        """
        # Simple language detection based on common patterns
        language_flags = {
            'ja': '🇯🇵',
            'jp': '🇯🇵',
            'japanese': '🇯🇵',
            'es': '🇪🇸',
            'spanish': '🇪🇸',
            'fr': '🇫🇷',
            'french': '🇫🇷',
            'de': '🇩🇪',
            'german': '🇩🇪',
            'ko': '🇰🇷',
            'korean': '🇰🇷',
            'zh': '🇨🇳',
            'chinese': '🇨🇳',
            'en': '🇬🇧',
            'english': '🇬🇧'
        }
        
        section_lower = section_name.lower()
        for lang_key, flag in language_flags.items():
            if lang_key in section_lower:
                return flag
        
        return '🇬🇧'  # Default to English

    def _extract_issues(self, content: str) -> List[Dict[str, str]]:
        """
        Extract all issues from AI response using intelligent parsing.
        """
        issues = []
        
        # Split content into lines for easier processing
        lines = content.split('\n')
        current_issue = None
        collecting_text = False
        collecting_rewrite = False
        
        for line in lines:
            line = line.strip()
            
            # Start of new issue
            if re.match(r'^$$Issue \d+$$', line) or re.match(r'^(?:🔴|🟠|🟡|🔵)', line):
                if current_issue:
                    issues.append(current_issue)
                current_issue = {}
                collecting_text = False
                collecting_rewrite = False
                continue
            
            # Severity line
            severity_match = re.search(r'(?:Severity|Level):\s*(\w+)', line, re.IGNORECASE)
            if severity_match:
                if current_issue is not None:
                    current_issue['severity'] = severity_match.group(1).capitalize()
                continue
            
            # Text line
            if line.startswith('Text:') or line.startswith('Problematic Text:'):
                collecting_text = True
                collecting_rewrite = False
                text_match = re.search(r'["`](.*)["`]', line)
                if text_match and current_issue is not None:
                    current_issue['text'] = text_match.group(1)
                continue
            
            # Translation line
            if line.startswith('Translation:'):
                collecting_text = False
                collecting_rewrite = False
                translation_match = re.search(r'["`](.*)["`]', line)
                if translation_match and current_issue is not None:
                    current_issue['translation'] = translation_match.group(1)
                continue
            
            # Guideline line
            if line.startswith('Guideline:'):
                collecting_text = False
                collecting_rewrite = False
                if current_issue is not None:
                    current_issue['guideline'] = line.replace('Guideline:', '').strip()
                continue
            
            # Why line
            if line.startswith('Why:'):
                collecting_text = False
                collecting_rewrite = False
                if current_issue is not None:
                    current_issue['reason'] = line.replace('Why:', '').strip()
                continue
            
            # Fix line
            if line.startswith('Fix:'):
                collecting_text = False
                collecting_rewrite = False
                if current_issue is not None:
                    current_issue['fix'] = line.replace('Fix:', '').strip()
                continue
            
            # Rewrite line
            if line.startswith('Rewrite:') or line.startswith('Suggested Rewrite:'):
                collecting_text = False
                collecting_rewrite = True
                rewrite_match = re.search(r'["`](.*)["`]', line)
                if rewrite_match and current_issue is not None:
                    current_issue['rewrite'] = rewrite_match.group(1)
                continue
            
            # Rewrite Translation line
            if line.startswith('Rewrite Translation:'):
                collecting_text = False
                collecting_rewrite = False
                translation_match = re.search(r'["`](.*)["`]', line)
                if translation_match and current_issue is not None:
                    current_issue['rewrite_translation'] = translation_match.group(1)
                continue
        
        # Add last issue if exists
        if current_issue:
            issues.append(current_issue)
        
        return issues

    def _count_severities(self, issues: List[Dict[str, str]]) -> Dict[str, int]:
        """
        Count issues by severity level.
        """
        counts = {'Critical': 0, 'High': 0, 'Medium': 0, 'Low': 0}
        
        for issue in issues:
            severity = issue.get('severity', 'Low')
            if severity in counts:
                counts[severity] += 1
        
        return counts

    def _format_severity_summary(self, counts: Dict[str, int]) -> str:
        """
        Format severity counts into compact summary.
        """
        summary_parts = []
        
        if counts['Critical'] > 0:
            summary_parts.append(f"🔴 {counts['Critical']}")
        if counts['High'] > 0:
            summary_parts.append(f"🟠 {counts['High']}")
        if counts['Medium'] > 0:
            summary_parts.append(f"🟡 {counts['Medium']}")
        if counts['Low'] > 0:
            summary_parts.append(f"🔵 {counts['Low']}")
        
        return " | ".join(summary_parts) if summary_parts else "✅ 0"

    def _format_clean_section(self, section_name: str, issues: List[Dict[str, str]]) -> str:
        """
        Format clean section output.
        """
        # Get language flag
        language_flag = self._detect_language_flag(section_name)
        
        # Count severities
        severity_counts = self._count_severities(issues)
        severity_summary = self._format_severity_summary(severity_counts)
        
        # Create header
        header = f"## {section_name}"
        header_line = f"{language_flag} | {severity_summary}"
        
        # Format issues
        issue_lines = []
        for i, issue in enumerate(issues, 1):
            issue_lines.append(f"---")
            issue_lines.append(f"🔴 {issue['severity'].upper()} ISSUE" if issue['severity'] == 'Critical' else
                             f"🟠 {issue['severity'].upper()} ISSUE" if issue['severity'] == 'High' else
                             f"🟡 {issue['severity'].upper()} ISSUE" if issue['severity'] == 'Medium' else
                             f"🔵 {issue['severity'].upper()} ISSUE")
            
            issue_lines.append(f"**Text:** \"{issue['text']}\"")
            issue_lines.append(f"**Translation:** \"{issue['translation']}\"")
            issue_lines.append(f"**Guideline:** {issue['guideline']}")
            issue_lines.append(f"**Why:** {issue['reason']}")
            issue_lines.append(f"**Fix:** {issue['fix']}")
            issue_lines.append(f"**Rewrite:** \"{issue['rewrite']}\"")
            if 'rewrite_translation' in issue:
                issue_lines.append(f"**Rewrite Translation:** \"{issue['rewrite_translation']}\"")
        
        # Compliance status
        compliance_line = "✅ No other issues detected"
        
        # Assemble section
        section_parts = [header, header_line]
        if issue_lines:
            section_parts.extend(issue_lines)
        section_parts.append("")
        section_parts.append(compliance_line)
        
        return "\n".join(section_parts)

    def _extract_clean_section_content(self, ai_response: str) -> Optional[str]:
        """
        Extract and format clean section content from AI response.
        """
        try:
            # Extract section name
            section_name = self._extract_section_name(ai_response)
            
            # Extract issues
            issues = self._extract_issues(ai_response)
            
            # Format clean section
            clean_section = self._format_clean_section(section_name, issues)
            
            return clean_section
            
        except Exception as e:
            logger.warning(f"Failed to extract clean section content: {e}")
            return None

    def _create_clean_error_section(self, chunk_index: Any) -> str:
        """
        Create clean error section.
        """
        return f"""## Section Analysis Failed (Chunk {chunk_index})
❌ Technical Error

Analysis could not be completed for this section.
Manual review recommended."""

    def _create_final_report(self, analysis_results: List[Dict[str, Any]], chunks: List[Dict[str, Any]]) -> str:
        """
        Create clean final report by intelligently parsing AI responses.
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
            final_report = "\n\n---\n\n".join(report_parts)
        else:
            final_report = f"{header}❌ No sections could be analyzed. All chunks failed processing."
        
        logger.info(f"Final clean report generated: {len(final_report):,} characters")
        return final_report

    def _calculate_final_stats(self, analysis_results: List[Dict[str, Any]], processing_time: float) -> Dict[str, Any]:
        successful_results = [r for r in analysis_results if r.get("success")]
        failed_results = [r for r in analysis_results if not r.get("success")]
        
        individual_times = [r.get("processing_time", 0) for r in successful_results if "processing_time" in r]
        avg_individual_time = sum(individual_times) / len(individual_times) if individual_times else 0
        
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
        logger.info("Validating analysis engine setup")
        
        validation_results = {
            "api_key_valid": False,
            "assistant_accessible": False,
            "assistant_info": None,
            "errors": []
        }
        
        try:
            if self.assistant_client.validate_api_key():
                validation_results["api_key_valid"] = True
                logger.info("API key validation passed")
            else:
                validation_results["errors"].append("Invalid API key")
                logger.error("API key validation failed")
            
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
        if self.assistant_client:
            await self.assistant_client.cleanup()
        logger.info("AnalysisEngine cleanup completed")