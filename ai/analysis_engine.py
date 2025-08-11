#!/usr/bin/env python3
"""
Analysis Engine for YMYL Audit Tool - REDESIGNED FOR HUMAN READABILITY

Orchestrates the complete AI analysis workflow with focus on:
- Clean, executive-level reporting
- Visual hierarchy and quick scanning
- Actionable insights over technical details
- Professional presentation for stakeholders

MAJOR CHANGES:
- Complete report structure overhaul
- Issue aggregation and prioritization
- Visual improvements with tables and status indicators
- Technical details moved to appendix
- Executive summary with key metrics
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
    Orchestrates AI-powered YMYL compliance analysis with human-readable reporting.
    """
    
    def __init__(self, api_key: str, progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None):
        """Initialize the AnalysisEngine."""
        self.assistant_client = AssistantClient(api_key)
        self.progress_callback = progress_callback
        self.analysis_start_time = None
        self.analysis_stats = {}
        self._completed_count = 0
        self._total_chunks = 0
        logger.info("AnalysisEngine initialized")

    async def process_json_content(self, json_output: str) -> Dict[str, Any]:
        """Process JSON output through complete AI analysis workflow."""
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
            
            # Initialize completion tracking
            self._completed_count = 0
            self._total_chunks = len(chunks)
            
            # Step 3: Process chunks in parallel
            self._update_progress(f"Analyzing {len(chunks)} chunks in parallel", 0.3)
            analysis_results = await self._process_chunks_parallel(chunks)
            
            # Step 4: Generate human-readable report
            self._update_progress("Generating executive report", 0.9)
            final_report = self._create_human_readable_report(analysis_results, chunks)
            
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
        """Process multiple chunks in parallel with controlled concurrency."""
        logger.info(f"Starting parallel analysis of {len(chunks)} chunks")
        
        semaphore = asyncio.Semaphore(MAX_PARALLEL_REQUESTS)
        
        async def process_single_chunk(chunk):
            async with semaphore:
                return await self.assistant_client.analyze_chunk(
                    chunk["text"], 
                    chunk["index"]
                )
        
        # Create tasks for all chunks
        tasks = [process_single_chunk(chunk) for chunk in chunks]
        results = []
        completed = 0
        
        # Process tasks as they complete
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
        
        # Sort results by chunk index to maintain order
        results.sort(key=lambda x: x.get("chunk_index", 0))
        
        successful = len([r for r in results if r.get("success")])
        failed = len(results) - successful
        
        logger.info(f"Parallel processing completed: {successful} successful, {failed} failed")
        return results

    def _create_human_readable_report(self, analysis_results: List[Dict[str, Any]], chunks: List[Dict[str, Any]]) -> str:
        """Create a clean, executive-level compliance report."""
        logger.info("Creating human-readable compliance report")
        
        # Aggregate and process findings
        all_issues = self._aggregate_issues(analysis_results)
        section_summaries = self._create_section_summaries(analysis_results)
        
        # Build report components
        report_parts = [
            self._create_executive_summary(all_issues, section_summaries),
            self._create_priority_findings(all_issues),
            self._create_section_overview(section_summaries),
            self._create_detailed_findings(analysis_results),
            self._create_technical_appendix(analysis_results)
        ]
        
        final_report = '\n\n'.join(filter(None, report_parts))
        logger.info(f"Human-readable report generated: {len(final_report):,} characters")
        
        return final_report

    def _aggregate_issues(self, analysis_results: List[Dict[str, Any]]) -> Dict[str, List[Dict]]:
        """Aggregate and categorize all issues for summary views."""
        issues_by_priority = {"critical": [], "high": [], "medium": [], "low": []}
        issues_by_category = {}
        
        for result in analysis_results:
            if not result.get("success"):
                continue
                
            # Parse the content to extract issues (this would need to be adapted based on your AI response format)
            section_name = self._extract_section_name(result.get("content", ""))
            issues = self._parse_issues_from_content(result.get("content", ""))
            
            for issue in issues:
                priority = issue.get("severity", "low").lower()
                if priority in issues_by_priority:
                    enhanced_issue = {
                        **issue,
                        "section": section_name,
                        "section_index": result.get("chunk_index", 0)
                    }
                    issues_by_priority[priority].append(enhanced_issue)
                    
                    # Also categorize by type
                    category = issue.get("category", "Other")
                    if category not in issues_by_category:
                        issues_by_category[category] = []
                    issues_by_category[category].append(enhanced_issue)
        
        return issues_by_priority

    def _create_section_summaries(self, analysis_results: List[Dict[str, Any]]) -> List[Dict]:
        """Create summary data for each section."""
        summaries = []
        
        for result in analysis_results:
            if result.get("success"):
                section_name = self._extract_section_name(result.get("content", ""))
                issues = self._parse_issues_from_content(result.get("content", ""))
                
                # Determine section status
                critical_count = len([i for i in issues if i.get("severity", "").lower() == "critical"])
                high_count = len([i for i in issues if i.get("severity", "").lower() == "high"])
                
                if critical_count > 0:
                    status = "❌ Critical Issues"
                    priority = "🔴 High"
                elif high_count > 0:
                    status = "⚠️ Needs Review"
                    priority = "🟠 Medium"
                elif len(issues) > 0:
                    status = "🔵 Minor Issues"
                    priority = "🟡 Low"
                else:
                    status = "✅ Compliant"
                    priority = "✅ None"
                
                summaries.append({
                    "section": section_name,
                    "status": status,
                    "issue_count": len(issues),
                    "priority": priority,
                    "critical_count": critical_count,
                    "high_count": high_count
                })
            else:
                # Handle failed analyses
                summaries.append({
                    "section": f"Section {result.get('chunk_index', 'Unknown')}",
                    "status": "🔧 Analysis Failed",
                    "issue_count": 0,
                    "priority": "⚠️ Manual Review",
                    "critical_count": 0,
                    "high_count": 0,
                    "error": result.get("error", "Unknown error")
                })
        
        return summaries

    def _create_executive_summary(self, all_issues: Dict, section_summaries: List[Dict]) -> str:
        """Create clean executive summary with key metrics."""
        total_critical = len(all_issues["critical"])
        total_high = len(all_issues["high"])
        total_medium = len(all_issues["medium"])
        total_low = len(all_issues["low"])
        total_sections = len(section_summaries)
        
        # Determine overall status
        if total_critical > 0:
            overall_status = "❌ CRITICAL ISSUES FOUND"
            risk_level = "🔴 CRITICAL"
            action_required = "Immediate action required before publication"
        elif total_high > 0:
            overall_status = "⚠️ REVIEW REQUIRED"
            risk_level = "🟠 HIGH"
            action_required = "Address high-priority issues within 24 hours"
        elif total_medium > 0:
            overall_status = "🔵 MINOR ISSUES DETECTED"
            risk_level = "🟡 MEDIUM"
            action_required = "Address in next content update cycle"
        else:
            overall_status = "✅ COMPLIANT"
            risk_level = "🟢 LOW"
            action_required = "No immediate action required"
        
        # Calculate compliance score
        total_issues = total_critical + total_high + total_medium + total_low
        if total_issues == 0:
            compliance_score = "100%"
        else:
            # Weight critical and high issues more heavily
            weighted_score = max(0, 100 - (total_critical * 25) - (total_high * 10) - (total_medium * 3) - total_low)
            compliance_score = f"{weighted_score:.0f}%"
        
        return f"""# 🎯 YMYL Compliance Audit Report

## 📊 Executive Summary

**Overall Status:** {overall_status}  
**Risk Level:** {risk_level}  
**Compliance Score:** {compliance_score}  
**Audit Date:** {datetime.now().strftime("%B %d, %Y")}  
**Content Type:** Online Casino/Gambling Content

**Action Required:** {action_required}

### 📈 Issue Breakdown

| Priority Level | Count | Impact | Timeline |
|---------------|-------|--------|----------|
| 🔴 Critical | {total_critical} | User safety risk | Fix immediately |
| 🟠 High | {total_high} | E-E-A-T violation | Within 24 hours |
| 🟡 Medium | {total_medium} | Content quality | Next update |
| 🔵 Low | {total_low} | Minor improvement | Optional |

**Total Issues Found:** {total_issues} across {total_sections} sections"""

    def _create_priority_findings(self, all_issues: Dict) -> str:
        """Create actionable priority sections."""
        sections = []
        
        if all_issues["critical"]:
            sections.append("## 🚨 Critical Issues - Immediate Action Required")
            sections.append("\n> These issues pose direct risks to user safety or legal compliance\n")
            
            for i, issue in enumerate(all_issues["critical"][:5], 1):  # Top 5 critical
                sections.append(f"**{i}. {issue.get('section', 'Unknown Section')}**")
                sections.append(f"   - **Issue:** {issue.get('summary', 'Critical compliance violation')}")
                sections.append(f"   - **Risk:** {issue.get('risk_description', 'User safety or legal risk')}")
                sections.append(f"   - **Quick Fix:** {issue.get('quick_fix', 'See detailed recommendations')}")
                sections.append("")
            
            if len(all_issues["critical"]) > 5:
                sections.append(f"*... and {len(all_issues['critical']) - 5} more critical issues (see detailed findings below)*\n")
        
        if all_issues["high"]:
            sections.append("## ⚠️ High Priority Issues - Address Within 24 Hours")
            sections.append("\n> These issues significantly impact content trustworthiness and E-E-A-T\n")
            
            for i, issue in enumerate(all_issues["high"][:8], 1):  # Top 8 high
                sections.append(f"**{i}. {issue.get('section', 'Unknown Section')}:** {issue.get('summary', 'E-E-A-T violation')}")
            
            if len(all_issues["high"]) > 8:
                sections.append(f"\n*... and {len(all_issues['high']) - 8} more high priority issues*")
        
        return '\n'.join(sections) if sections else ""

    def _create_section_overview(self, section_summaries: List[Dict]) -> str:
        """Create visual section status overview."""
        if not section_summaries:
            return ""
        
        sections = ["## 📋 Section Status Overview\n"]
        
        # Create status table
        sections.append("| Section | Status | Issues | Priority |")
        sections.append("|---------|--------|--------|----------|")
        
        for summary in section_summaries:
            section_name = summary["section"]
            status = summary["status"]
            issue_count = summary["issue_count"]
            priority = summary["priority"]
            
            # Truncate long section names
            if len(section_name) > 25:
                section_name = section_name[:22] + "..."
            
            sections.append(f"| {section_name} | {status} | {issue_count} | {priority} |")
        
        # Add summary stats
        total_sections = len(section_summaries)
        compliant_sections = len([s for s in section_summaries if "✅" in s["status"]])
        critical_sections = len([s for s in section_summaries if "❌" in s["status"]])
        
        sections.append(f"\n**Section Summary:** {compliant_sections}/{total_sections} compliant • {critical_sections} with critical issues")
        
        return '\n'.join(sections)

    def _create_detailed_findings(self, analysis_results: List[Dict[str, Any]]) -> str:
        """Create detailed findings section with clean formatting."""
        sections = ["## 📝 Detailed Section Analysis\n"]
        
        for result in analysis_results:
            if result.get("success"):
                # Clean up the AI response content
                content = result.get("content", "")
                cleaned_content = self._clean_ai_response(content)
                sections.append(cleaned_content)
                sections.append("")  # Add spacing between sections
            else:
                # Handle failed analyses cleanly
                chunk_idx = result.get('chunk_index', 'Unknown')
                sections.append(f"### ⚠️ Analysis Error - Section {chunk_idx}")
                sections.append(f"**Status:** Processing failed")
                sections.append(f"**Error:** {result.get('error', 'Unknown error')}")
                sections.append("**Action:** Manual review required")
                sections.append("")
        
        return '\n'.join(sections)

    def _create_technical_appendix(self, analysis_results: List[Dict[str, Any]]) -> str:
        """Create collapsible technical details section."""
        successful_count = len([r for r in analysis_results if r.get("success")])
        failed_count = len(analysis_results) - successful_count
        processing_time = getattr(self, 'analysis_stats', {}).get('processing_time', 0)
        
        return f"""## 🔧 Technical Information

<details>
<summary><strong>Processing Details</strong> (Click to expand)</summary>

### Analysis Metrics
- **Total Sections Processed:** {len(analysis_results)}
- **Successfully Analyzed:** {successful_count}
- **Analysis Failures:** {failed_count}
- **Success Rate:** {(successful_count / len(analysis_results) * 100):.1f}%
- **Total Processing Time:** {processing_time:.2f} seconds
- **Average Time per Section:** {(processing_time / len(analysis_results)):.2f} seconds

### System Information
- **Analysis Engine:** AI-powered YMYL compliance analysis
- **Assistant ID:** {getattr(self.assistant_client, 'assistant_id', 'N/A')}
- **Analysis Date:** {datetime.now().isoformat()}
- **Parallel Processing:** {MAX_PARALLEL_REQUESTS} concurrent requests

### Quality Assurance
- **Guidelines:** Google Search Quality Rater Guidelines (SQRG)
- **Focus Areas:** E-E-A-T compliance for YMYL content
- **Content Type:** Online gambling/casino industry
- **Audit Scope:** Section-by-section comprehensive review

</details>

---

*Report generated by AI-powered YMYL compliance analysis system*"""

    # Helper methods for content parsing and cleaning
    def _extract_section_name(self, content: str) -> str:
        """Extract section name from AI response."""
        lines = content.split('\n')
        for line in lines[:5]:  # Check first 5 lines
            if line.startswith('#') and not line.startswith('# 🎯'):
                return line.strip('# ').strip()
        return "Unknown Section"

    def _parse_issues_from_content(self, content: str) -> List[Dict]:
        """Parse issues from AI response content."""
        # This would need to be implemented based on your AI response format
        # For now, returning empty list - you'd parse the actual issues here
        issues = []
        
        # Example parsing logic (adapt to your format):
        if "🔴 CRITICAL" in content:
            issues.append({"severity": "critical", "summary": "Critical issue detected"})
        if "🟠 HIGH" in content:
            issues.append({"severity": "high", "summary": "High priority issue detected"})
        if "🟡 MEDIUM" in content:
            issues.append({"severity": "medium", "summary": "Medium priority issue detected"})
        if "🔵 LOW" in content:
            issues.append({"severity": "low", "summary": "Low priority issue detected"})
        
        return issues

    def _clean_ai_response(self, content: str) -> str:
        """Clean up AI response for better readability."""
        # Remove excessive technical markers
        content = content.replace("---", "")
        
        # Ensure proper section headers
        lines = content.split('\n')
        cleaned_lines = []
        
        for line in lines:
            # Skip empty lines at start
            if not cleaned_lines and not line.strip():
                continue
            
            # Clean up headers
            if line.startswith('#') and not line.startswith('##'):
                if not line.startswith('# 🎯'):  # Keep our main header
                    line = '### ' + line.strip('# ').strip()
            
            cleaned_lines.append(line)
        
        return '\n'.join(cleaned_lines).strip()

    def _calculate_final_stats(self, analysis_results: List[Dict[str, Any]], processing_time: float) -> Dict[str, Any]:
        """Calculate final statistics for the analysis."""
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
        
        # Store stats for use in report
        self.analysis_stats = stats
        
        logger.info(f"Final statistics calculated: {format_metrics(stats)}")
        return stats

    def _create_error_result(self, error_message: str) -> Dict[str, Any]:
        """Create a standardized error result."""
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
        """Update progress and notify callback if available."""
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
        """Validate that the analysis engine is properly configured."""
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