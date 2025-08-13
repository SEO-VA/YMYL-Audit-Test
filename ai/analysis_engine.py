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
        """Create final report from analysis results, grouped by sections and ordered by severity."""
        report = f"""# YMYL Compliance Audit Report

    **Date:** {datetime.now().strftime("%Y-%m-%d")}

    ---

    """
        
        # Collect all violations from all chunks
        all_violations = []
        chunk_summaries = []
        
        for i, result in enumerate(analysis_results, 1):
            if result.get("success"):
                # Add chunk summary
                chunk_summaries.append({
                    'chunk_index': i,
                    'status': 'success',
                    'content': result["content"]
                })
                
                # Extract violations for grouping
                try:
                    violations_data = json.loads(result["content"])
                    violations = violations_data.get('violations', [])
                    for violation in violations:
                        violation['source_chunk'] = i
                        all_violations.append(violation)
                except:
                    pass
            else:
                chunk_summaries.append({
                    'chunk_index': i,
                    'status': 'failed',
                    'error': result.get('error', 'Unknown error')
                })
        
        # Group violations by H2 sections
        sections = {}
        ungrouped_violations = []
        
        for violation in all_violations:
            section_found = False
            violation_context = violation.get('context', '').lower()
            violation_location = violation.get('location', '').lower()
            
            # Look for H2 headings in context or location
            for text in [violation_context, violation_location]:
                if 'h2:' in text:
                    h2_start = text.find('h2:') + 3
                    h2_end = text.find('\n', h2_start)
                    if h2_end == -1:
                        h2_end = len(text)
                    h2_text = text[h2_start:h2_end].strip()
                    
                    if h2_text:
                        if h2_text not in sections:
                            sections[h2_text] = []
                        sections[h2_text].append(violation)
                        section_found = True
                        break
            
            if not section_found:
                ungrouped_violations.append(violation)
        
        # Define severity order
        severity_order = {
            'critical': 1,
            'high': 2,
            'medium': 3, 
            'low': 4,
            'info': 5
        }
        
        def get_severity_score(violation):
            severity = violation.get('severity', 'medium').lower()
            return severity_order.get(severity, 3)
        
        # Sort violations within each section
        for section_name in sections:
            sections[section_name].sort(key=get_severity_score)
        
        ungrouped_violations.sort(key=get_severity_score)
        
        # Add executive summary
        total_violations = len(all_violations)
        critical_count = len([v for v in all_violations if v.get('severity', '').lower() == 'critical'])
        high_count = len([v for v in all_violations if v.get('severity', '').lower() == 'high'])
        
        report += f"""## 📊 Executive Summary

    - **Total Violations Found:** {total_violations}
    - **Critical Issues:** {critical_count} 🔴
    - **High Priority Issues:** {high_count} 🟠
    - **Sections Analyzed:** {len(sections) + (1 if ungrouped_violations else 0)}

    ---

    """
        
        # Add grouped sections
        if sections:
            for section_name in sorted(sections.keys()):
                section_violations = sections[section_name]
                report += f"""## 📋 {section_name}

    **Violations in this section:** {len(section_violations)}

    """
                
                for violation in section_violations:
                    severity = violation.get('severity', 'medium').upper()
                    severity_icon = {
                        'CRITICAL': '🔴',
                        'HIGH': '🟠',
                        'MEDIUM': '🟡',
                        'LOW': '🔵', 
                        'INFO': '⚪'
                    }.get(severity, '🟡')
                    
                    issue = violation.get('issue', 'No issue description')
                    location = violation.get('location', 'Unknown location')
                    context = violation.get('context', 'No context provided')
                    fix = violation.get('fix', 'No fix suggestion provided')
                    source_chunk = violation.get('source_chunk', 'Unknown')
                    
                    report += f"""### {severity_icon} {severity}: {issue}

    **📍 Location:** {location}
    **📝 Context:** {context}
    **🔧 Recommended Fix:** {fix}
    **📄 Source Chunk:** {source_chunk}

    ---

    """
        
        # Add ungrouped violations
        if ungrouped_violations:
            report += f"""## 📋 General Issues

    **Violations not tied to specific sections:** {len(ungrouped_violations)}

    """
            
            for violation in ungrouped_violations:
                severity = violation.get('severity', 'medium').upper()
                severity_icon = {
                    'CRITICAL': '🔴',
                    'HIGH': '🟠',
                    'MEDIUM': '🟡',
                    'LOW': '🔵',
                    'INFO': '⚪'
                }.get(severity, '🟡')
                
                issue = violation.get('issue', 'No issue description')
                location = violation.get('location', 'Unknown location')
                context = violation.get('context', 'No context provided')
                fix = violation.get('fix', 'No fix suggestion provided')
                source_chunk = violation.get('source_chunk', 'Unknown')
                
                report += f"""### {severity_icon} {severity}: {issue}

    **📍 Location:** {location}
    **📝 Context:** {context}
    **🔧 Recommended Fix:** {fix}
    **📄 Source Chunk:** {source_chunk}

    ---

    """
        
        # Add processing summary
        successful_chunks = len([s for s in chunk_summaries if s['status'] == 'success'])
        failed_chunks = len([s for s in chunk_summaries if s['status'] == 'failed'])
        
        report += f"""## 📈 Processing Summary

    - **Total Chunks Processed:** {len(chunk_summaries)}
    - **Successful Analyses:** {successful_chunks}
    - **Failed Analyses:** {failed_chunks}
    - **Success Rate:** {(successful_chunks / len(chunk_summaries) * 100):.1f}%

    """
        
        if failed_chunks > 0:
            report += "### ❌ Failed Chunk Analysis\n\n"
            for summary in chunk_summaries:
                if summary['status'] == 'failed':
                    report += f"- **Chunk {summary['chunk_index']}:** {summary['error']}\n"
            report += "\n"
        
        return report

    async def cleanup(self):
        """Clean up resources."""
        if self.assistant_client:
            await self.assistant_client.cleanup()