#!/usr/bin/env python3
"""
JSON processing utilities for YMYL Audit Tool
UPDATED: Single request architecture - process AI JSON array response
"""

import json
import hashlib
import re
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple, Union
from utils.logging_utils import setup_logger

logger = setup_logger(__name__)


def decode_unicode_escapes(text: str) -> str:
    """Decode Unicode escape sequences safely."""
    try:
        def safe_decode_match(match):
            try:
                unicode_code = match.group(1)
                code_point = int(unicode_code, 16)
                
                if 0xD800 <= code_point <= 0xDFFF:
                    logger.warning(f"Replacing surrogate Unicode \\u{unicode_code} with replacement character")
                    return '\uFFFD'
                
                return chr(code_point)
                
            except (ValueError, OverflowError) as e:
                logger.warning(f"Invalid Unicode escape \\u{match.group(1)}: {e}")
                return '\uFFFD'
        
        decoded = re.sub(r'\\u([0-9a-fA-F]{4})', safe_decode_match, text)
        decoded = clean_surrogate_pairs(decoded)
        
        if decoded != text:
            original_unicode_count = text.count('\\u')
            remaining_unicode_count = decoded.count('\\u')
            logger.debug(f"Unicode decoding: {original_unicode_count} sequences found, {remaining_unicode_count} remaining")
        
        return decoded
        
    except Exception as e:
        logger.error(f"Unicode decoding failed: {e}")
        return clean_surrogate_pairs(text)


def clean_surrogate_pairs(text: str) -> str:
    """Clean surrogate pairs from text."""
    try:
        cleaned = text.encode('utf-8', errors='replace').decode('utf-8')
        
        def replace_problematic_char(char):
            try:
                char.encode('utf-8')
                return char
            except UnicodeEncodeError:
                return '\uFFFD'
        
        final_cleaned = ''.join(replace_problematic_char(char) for char in cleaned)
        
        if final_cleaned != text:
            problem_chars = len(text) - len([c for c in text if c == replace_problematic_char(c)])
            logger.info(f"Cleaned {problem_chars} problematic Unicode characters")
        
        return final_cleaned
        
    except Exception as e:
        logger.error(f"Error cleaning surrogate pairs: {e}")
        return text.encode('ascii', errors='replace').decode('ascii')


def safe_json_dumps(data: Any, **kwargs) -> str:
    """Safely serialize data to JSON."""
    try:
        safe_kwargs = {
            'ensure_ascii': False,
            'separators': (',', ': '),
            'indent': kwargs.get('indent', 2)
        }
        safe_kwargs.update(kwargs)
        
        json_str = json.dumps(data, **safe_kwargs)
        cleaned_json = clean_surrogate_pairs(json_str)
        json.loads(cleaned_json)  # Validate
        
        return cleaned_json
        
    except (UnicodeEncodeError, json.JSONDecodeError) as e:
        logger.warning(f"JSON serialization had Unicode issues, using ASCII-safe mode: {e}")
        
        safe_kwargs['ensure_ascii'] = True
        try:
            return json.dumps(data, **safe_kwargs)
        except Exception as fallback_error:
            logger.error(f"Even ASCII-safe JSON serialization failed: {fallback_error}")
            return '{"error": "JSON serialization failed due to Unicode issues"}'


def safe_json_loads(json_str: str) -> Any:
    """Safely parse JSON string."""
    try:
        cleaned_json = clean_surrogate_pairs(json_str)
        return json.loads(cleaned_json)
        
    except json.JSONDecodeError as e:
        logger.error(f"JSON parsing failed even after cleaning: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error in safe JSON parsing: {e}")
        return None


def parse_json_output(json_string: str) -> Optional[Dict[str, Any]]:
    """Parse JSON string with validation."""
    try:
        if not json_string or not json_string.strip():
            logger.error("Empty JSON string provided")
            return None
        
        parsed_data = safe_json_loads(json_string)
        if parsed_data is None:
            return None
        
        if isinstance(parsed_data, dict):
            parsed_data['_metadata'] = {
                'parsed_at': datetime.now().isoformat(),
                'content_hash': _generate_content_hash(json_string),
                'content_length': len(json_string),
                'parser_version': '2.0.0'
            }
        
        logger.info(f"Successfully parsed JSON ({len(json_string):,} characters)")
        return parsed_data
        
    except Exception as e:
        logger.error(f"Unexpected error parsing JSON: {e}")
        return None


def convert_ai_response_to_markdown(ai_response: List[Dict[str, Any]]) -> str:
    """
    Convert AI JSON array response to markdown report.
    NEW: Main function for single-request architecture
    """
    try:
        if not isinstance(ai_response, list):
            logger.error("AI response is not a list")
            return "❌ **Error**: Invalid AI response format"
        
        report_parts = []
        
        # Add report header
        report_parts.append(f"""# YMYL Compliance Audit Report

**Date:** {datetime.now().strftime("%Y-%m-%d")}
**Analysis Type:** Single Request Analysis

---

""")
        
        # Process each chunk response
        sections_with_violations = 0
        total_violations = 0
        
        for chunk_response in ai_response:
            try:
                chunk_index = chunk_response.get('big_chunk_index', 'Unknown')
                content_name = chunk_response.get('content_name', f'Section {chunk_index}')
                violations = chunk_response.get('violations', [])
                
                # Handle "no violation found" case
                if violations == "no violation found" or not violations:
                    continue
                
                # Add section header
                report_parts.append(f"## {content_name}\n\n")
                sections_with_violations += 1
                
                # Process violations
                for i, violation in enumerate(violations, 1):
                    total_violations += 1
                    
                    severity_emoji = {
                        "critical": "🔴",
                        "high": "🟠",
                        "medium": "🟡", 
                        "low": "🔵"
                    }.get(violation.get("severity", "medium"), "🟡")
                    
                    # Clean all text fields
                    violation_type = clean_surrogate_pairs(str(violation.get('violation_type', 'Unknown violation')))
                    problematic_text = clean_surrogate_pairs(str(violation.get('problematic_text', 'N/A')))
                    explanation = clean_surrogate_pairs(str(violation.get('explanation', 'No explanation provided')))
                    suggested_rewrite = clean_surrogate_pairs(str(violation.get('suggested_rewrite', 'No suggestion provided')))
                    
                    # Handle translation fields
                    translation = violation.get('translation', '')
                    rewrite_translation = violation.get('rewrite_translation', '')
                    
                    violation_text = f"""**{severity_emoji} Violation {i}**
- **Issue:** {violation_type}
- **Problematic Text:** "{problematic_text}"
"""
                    
                    # Add translation if present
                    if translation:
                        clean_translation = clean_surrogate_pairs(str(translation))
                        violation_text += f"- **Translation:** \"{clean_translation}\"\n"
                    
                    violation_text += f"""- **Explanation:** {explanation}
- **Guideline Reference:** Section {violation.get('guideline_section', 'N/A')} (Page {violation.get('page_number', 'N/A')})
- **Severity:** {violation.get('severity', 'medium').title()}
- **Suggested Fix:** "{suggested_rewrite}"
"""
                    
                    # Add rewrite translation if present
                    if rewrite_translation:
                        clean_rewrite_translation = clean_surrogate_pairs(str(rewrite_translation))
                        violation_text += f"- **Translation of Fix:** \"{clean_rewrite_translation}\"\n"
                    
                    violation_text += "\n"
                    report_parts.append(violation_text)
                
                report_parts.append("\n")
                
            except Exception as e:
                logger.error(f"Error processing chunk {chunk_response.get('big_chunk_index', 'Unknown')}: {e}")
                continue
        
        # Add summary if no violations found
        if sections_with_violations == 0:
            report_parts.append("✅ **No violations found across all content sections.**\n\n")
        
        # Add processing summary
        report_parts.append(f"""## 📈 Analysis Summary

**Sections with Violations:** {sections_with_violations}
**Total Violations:** {total_violations}
**Analysis Method:** Single Request Processing

""")
        
        final_report = ''.join(report_parts)
        return clean_surrogate_pairs(final_report)
        
    except Exception as e:
        logger.error(f"Error converting AI response to markdown: {e}")
        return f"❌ **Error**: Failed to process AI response - {str(e)}"


def get_display_json_string(json_data: Union[Dict[str, Any], str]) -> str:
    """Get clean JSON string for UI display."""
    try:
        if isinstance(json_data, dict):
            display_data = _create_display_version(json_data)
            return safe_json_dumps(display_data, indent=2)
        elif isinstance(json_data, str):
            parsed = safe_json_loads(json_data)
            if parsed is not None:
                if isinstance(parsed, dict):
                    display_data = _create_display_version(parsed)
                    return safe_json_dumps(display_data, indent=2)
                else:
                    return safe_json_dumps(parsed, indent=2)
            else:
                return clean_surrogate_pairs(json_data)
        else:
            return safe_json_dumps(json_data, indent=2)
            
    except Exception as e:
        logger.error(f"Error creating display JSON string: {e}")
        return clean_surrogate_pairs(str(json_data))


def validate_chunk_structure(json_data: Dict[str, Any]) -> bool:
    """Validate JSON chunk structure."""
    try:
        if not isinstance(json_data, dict):
            logger.warning("JSON data is not a dictionary")
            return False
        
        big_chunks = json_data.get('big_chunks')
        if not isinstance(big_chunks, list):
            logger.warning("Missing or invalid 'big_chunks' array")
            return False
        
        if len(big_chunks) == 0:
            logger.warning("Empty 'big_chunks' array")
            return False
        
        valid_chunks = 0
        for i, chunk in enumerate(big_chunks):
            if not isinstance(chunk, dict):
                logger.warning(f"Chunk {i} is not a dictionary")
                continue
            
            if 'small_chunks' not in chunk:
                logger.warning(f"Chunk {i} missing 'small_chunks'")
                continue
            
            small_chunks = chunk['small_chunks']
            if not isinstance(small_chunks, list):
                logger.warning(f"Chunk {i} 'small_chunks' is not a list")
                continue
            
            if len(small_chunks) == 0:
                logger.warning(f"Chunk {i} has empty 'small_chunks'")
                continue
            
            total_content = '\n'.join(str(sc) for sc in small_chunks)
            cleaned_content = clean_surrogate_pairs(total_content)
            
            if len(cleaned_content.strip()) < 10:
                logger.warning(f"Chunk {i} has insufficient content after Unicode cleaning")
                continue
            
            valid_chunks += 1
        
        success = valid_chunks > 0
        if success:
            logger.info(f"JSON structure validation passed for {valid_chunks}/{len(big_chunks)} chunks")
        else:
            logger.error("No valid chunks found in JSON structure")
        
        return success
        
    except Exception as e:
        logger.error(f"Error validating chunk structure: {e}")
        return False


def _generate_content_hash(content: str) -> str:
    """Generate hash for content comparison."""
    try:
        cleaned_content = clean_surrogate_pairs(content)
        return hashlib.sha256(cleaned_content.encode('utf-8')).hexdigest()[:16]
    except Exception as e:
        logger.warning(f"Error generating content hash: {e}")
        ascii_content = content.encode('ascii', errors='replace').decode('ascii')
        return hashlib.sha256(ascii_content.encode('ascii')).hexdigest()[:16]


def _create_display_version(json_data: Dict[str, Any]) -> Dict[str, Any]:
    """Create display version of JSON data."""
    if not isinstance(json_data, dict):
        return json_data
    
    display_data = {}
    for key, value in json_data.items():
        if key.startswith('_'):
            continue
        
        if isinstance(value, str):
            display_data[key] = clean_surrogate_pairs(value)
        elif isinstance(value, list):
            cleaned_list = []
            for item in value:
                if isinstance(item, str):
                    cleaned_list.append(clean_surrogate_pairs(item))
                elif isinstance(item, dict):
                    cleaned_list.append(_create_display_version(item))
                else:
                    cleaned_list.append(item)
            display_data[key] = cleaned_list
        elif isinstance(value, dict):
            display_data[key] = _create_display_version(value)
        else:
            display_data[key] = value
    
    return display_data


# REMOVED FUNCTIONS (no longer needed):
# - extract_big_chunks() - AI processes full content
# - convert_violations_json_to_readable() - replaced by convert_ai_response_to_markdown()
# - create_grouped_violations_report() - AI handles organization

def convert_violations_json_to_readable(json_content: str) -> str:
    """
    Convert JSON violations format to human-readable markdown.
    COMPATIBILITY: For UI components that still expect this function
    """
    try:
        violations_data = safe_json_loads(json_content)
        if violations_data is None:
            return "❌ **Could not parse violations data.**\n\n"
        
        # Handle both old format (single chunk) and new format (array)
        if isinstance(violations_data, list):
            # New format - convert first item only for compatibility
            if violations_data and len(violations_data) > 0:
                violations = violations_data[0].get("violations", [])
            else:
                violations = []
        else:
            # Old format - single chunk
            violations = violations_data.get("violations", [])
        
        if not violations or violations == "no violation found":
            return "✅ **No violations found in this section.**\n\n"
        
        readable_parts = []
        
        for i, violation in enumerate(violations, 1):
            severity_emoji = {
                "critical": "🔴",
                "high": "🟠",
                "medium": "🟡", 
                "low": "🔵"
            }.get(violation.get("severity", "medium"), "🟡")
            
            # Clean all text fields
            violation_type = clean_surrogate_pairs(str(violation.get('violation_type', 'Unknown violation')))
            problematic_text = clean_surrogate_pairs(str(violation.get('problematic_text', 'N/A')))
            explanation = clean_surrogate_pairs(str(violation.get('explanation', 'No explanation provided')))
            suggested_rewrite = clean_surrogate_pairs(str(violation.get('suggested_rewrite', 'No suggestion provided')))
            
            # Handle translation fields
            translation = violation.get('translation', '')
            rewrite_translation = violation.get('rewrite_translation', '')
            
            violation_text = f"""**{severity_emoji} Violation {i}**
- **Issue:** {violation_type}
- **Problematic Text:** "{problematic_text}"
"""
            
            # Add translation if present
            if translation:
                clean_translation = clean_surrogate_pairs(str(translation))
                violation_text += f"- **Translation:** \"{clean_translation}\"\n"
            
            violation_text += f"""- **Explanation:** {explanation}
- **Guideline Reference:** Section {violation.get('guideline_section', 'N/A')} (Page {violation.get('page_number', 'N/A')})
- **Severity:** {violation.get('severity', 'medium').title()}
- **Suggested Fix:** "{suggested_rewrite}"
"""
            
            # Add rewrite translation if present
            if rewrite_translation:
                clean_rewrite_translation = clean_surrogate_pairs(str(rewrite_translation))
                violation_text += f"- **Translation of Fix:** \"{clean_rewrite_translation}\"\n"
            
            violation_text += "\n"
            readable_parts.append(violation_text)
        
        return ''.join(readable_parts)
        
    except Exception as e:
        logger.error(f"Error converting JSON to readable format: {e}")
        return clean_surrogate_pairs(str(json_content)) + "\n\n"

__all__ = [
    'decode_unicode_escapes',
    'clean_surrogate_pairs',
    'safe_json_dumps',
    'safe_json_loads',
    'parse_json_output',
    'convert_ai_response_to_markdown',
    'convert_violations_json_to_readable',  # ADD THIS LINE
    'get_display_json_string',
    'validate_chunk_structure'
]