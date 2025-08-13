#!/usr/bin/env python3
"""
JSON processing utilities for YMYL Audit Tool

Helper functions for parsing and manipulating JSON data.

FIXED: Unicode decoding centralized and properly handled for UI display
"""

import json
import hashlib
import re
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple, Union
from utils.logging_utils import setup_logger

logger = setup_logger(__name__)


def decode_unicode_escapes(text: str) -> str:
    """
    CENTRALIZED: Decode Unicode escape sequences in text to readable characters.
    This is the single source of truth for Unicode decoding.
    
    Args:
        text (str): Text with potential Unicode escapes
        
    Returns:
        str: Text with decoded Unicode characters
    """
    try:
        def decode_match(match):
            unicode_code = match.group(1)
            return chr(int(unicode_code, 16))
        decoded = re.sub(r'\\u([0-9a-fA-F]{4})', decode_match, text)
        
        # Log if decoding actually changed something
        if decoded != text:
            logger.debug(f"Unicode decoding applied: found {text.count('\\u')} escape sequences")
        
        return decoded
    except Exception as e:
        logger.warning(f"Unicode decoding failed: {e}")
        return text


def extract_big_chunks(json_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Extract and format big chunks for AI processing.
    
    FIXED: Enhanced with content validation and metadata tracking
    
    Args:
        json_data (dict): Parsed JSON data from chunk processor
        
    Returns:
        list: List of chunk dictionaries with index, text, count, and metadata
    """
    try:
        big_chunks = json_data.get('big_chunks', [])
        chunks = []
        
        for chunk in big_chunks:
            chunk_index = chunk.get('big_chunk_index', len(chunks) + 1)
            small_chunks = chunk.get('small_chunks', [])
            
            # Join small chunks with newlines - text should already be decoded
            joined_text = '\n'.join(small_chunks)
            
            # FIXED: Add content validation and metadata
            chunk_data = {
                "index": chunk_index,
                "text": joined_text,
                "count": len(small_chunks),
                "text_length": len(joined_text),
                "text_hash": _generate_content_hash(joined_text),
                "extracted_at": datetime.now().isoformat()
            }
            
            # Validate chunk has meaningful content
            if joined_text.strip() and len(joined_text.strip()) > 10:
                chunks.append(chunk_data)
            else:
                logger.warning(f"Skipping empty or too short chunk {chunk_index}")
        
        logger.info(f"Extracted {len(chunks)} valid big chunks from JSON data")
        return chunks
        
    except Exception as e:
        logger.error(f"Error extracting big chunks: {e}")
        return []


def parse_json_output(json_string: str) -> Optional[Dict[str, Any]]:
    """
    Safely parse JSON string with error handling and validation.
    
    FIXED: Enhanced with content validation and metadata addition
    
    Args:
        json_string (str): JSON string to parse
        
    Returns:
        dict or None: Parsed JSON data with metadata or None if parsing fails
    """
    try:
        if not json_string or not json_string.strip():
            logger.error("Empty JSON string provided")
            return None
        
        parsed_data = json.loads(json_string)
        
        # FIXED: Add metadata for tracking
        if isinstance(parsed_data, dict):
            parsed_data['_metadata'] = {
                'parsed_at': datetime.now().isoformat(),
                'content_hash': _generate_content_hash(json_string),
                'content_length': len(json_string),
                'parser_version': '1.2.0'
            }
        
        logger.info(f"Successfully parsed JSON ({len(json_string):,} characters)")
        return parsed_data
        
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON format at line {e.lineno}, column {e.colno}: {e.msg}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error parsing JSON: {e}")
        return None


def format_json_for_display(json_data: Union[Dict[str, Any], str], max_length: int = 1000) -> str:
    """
    Format JSON data for display with proper Unicode handling.
    
    FIXED: Handles both dict and string inputs, ensures Unicode is readable
    
    Args:
        json_data: JSON data to format (dict or string)
        max_length (int): Maximum length of formatted string
        
    Returns:
        str: Formatted JSON string with readable Unicode characters
    """
    try:
        # Handle different input types
        if isinstance(json_data, dict):
            # Create display version without internal metadata
            display_data = _create_display_version(json_data)
            formatted = json.dumps(display_data, indent=2, ensure_ascii=False)
        elif isinstance(json_data, str):
            # If it's already a string, try to parse and reformat for consistency
            try:
                parsed = json.loads(json_data)
                display_data = _create_display_version(parsed) if isinstance(parsed, dict) else parsed
                formatted = json.dumps(display_data, indent=2, ensure_ascii=False)
            except json.JSONDecodeError:
                # If parsing fails, treat as plain text
                formatted = json_data
        else:
            # Fallback to string representation
            formatted = str(json_data)
        
        # Apply truncation if needed
        if len(formatted) > max_length:
            truncated = formatted[:max_length]
            # Try to end at a complete line
            last_newline = truncated.rfind('\n')
            if last_newline > max_length * 0.8:  # If we're close to the end
                truncated = truncated[:last_newline]
            
            truncated += f"\n... (truncated, full length: {len(formatted):,} characters)"
            return truncated
        
        return formatted
        
    except Exception as e:
        logger.error(f"Error formatting JSON for display: {e}")
        return f"Error formatting JSON: {str(e)}"


def get_display_json_string(json_data: Union[Dict[str, Any], str]) -> str:
    """
    NEW: Get a clean JSON string for UI display with proper Unicode handling.
    This is the main function components should use for displaying JSON.
    
    Args:
        json_data: JSON data (dict or string)
        
    Returns:
        str: Clean, readable JSON string
    """
    try:
        if isinstance(json_data, dict):
            # Convert dict to formatted JSON string
            display_data = _create_display_version(json_data)
            return json.dumps(display_data, indent=2, ensure_ascii=False)
        elif isinstance(json_data, str):
            # If it's a string, ensure it's properly formatted JSON
            try:
                # Try to parse and reformat for consistency
                parsed = json.loads(json_data)
                if isinstance(parsed, dict):
                    display_data = _create_display_version(parsed)
                    return json.dumps(display_data, indent=2, ensure_ascii=False)
                else:
                    return json.dumps(parsed, indent=2, ensure_ascii=False)
            except json.JSONDecodeError:
                # If it's not valid JSON, return as-is (might be plain text)
                return json_data
        else:
            # Convert other types to JSON
            return json.dumps(json_data, indent=2, ensure_ascii=False)
            
    except Exception as e:
        logger.error(f"Error creating display JSON string: {e}")
        return str(json_data)


def validate_chunk_structure(json_data: Dict[str, Any]) -> bool:
    """
    Validate that JSON data has the expected chunk structure.
    
    FIXED: Enhanced validation with detailed error reporting
    
    Args:
        json_data (dict): Parsed JSON data to validate
        
    Returns:
        bool: True if structure is valid, False otherwise
    """
    try:
        # Check for required top-level structure
        if not isinstance(json_data, dict):
            logger.warning("JSON data is not a dictionary")
            return False
        
        # Check for big_chunks array
        big_chunks = json_data.get('big_chunks')
        if not isinstance(big_chunks, list):
            logger.warning("Missing or invalid 'big_chunks' array")
            return False
        
        if len(big_chunks) == 0:
            logger.warning("Empty 'big_chunks' array")
            return False
        
        # Validate each chunk structure with detailed checking
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
            
            # FIXED: Validate chunk content quality
            if len(small_chunks) == 0:
                logger.warning(f"Chunk {i} has empty 'small_chunks'")
                continue
            
            # Check if chunks have meaningful content
            total_content = '\n'.join(small_chunks)
            if len(total_content.strip()) < 10:
                logger.warning(f"Chunk {i} has insufficient content")
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


def get_chunk_statistics(json_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Calculate comprehensive statistics about the chunks.
    
    FIXED: Enhanced with content quality metrics and validation
    
    Args:
        json_data (dict): Parsed JSON data
        
    Returns:
        dict: Comprehensive statistics about the chunks
    """
    try:
        big_chunks = json_data.get('big_chunks', [])
        
        total_big_chunks = len(big_chunks)
        total_small_chunks = 0
        valid_chunks = 0
        empty_chunks = 0
        
        # Calculate text statistics
        total_text_length = 0
        chunk_sizes = []
        content_hashes = []
        
        for chunk in big_chunks:
            small_chunks = chunk.get('small_chunks', [])
            chunk_text = '\n'.join(small_chunks)
            chunk_length = len(chunk_text)
            
            total_small_chunks += len(small_chunks)
            total_text_length += chunk_length
            chunk_sizes.append(chunk_length)
            
            # FIXED: Track content quality
            if chunk_text.strip() and len(chunk_text.strip()) > 10:
                valid_chunks += 1
                content_hashes.append(_generate_content_hash(chunk_text))
            else:
                empty_chunks += 1
        
        # Calculate averages and quality metrics
        avg_small_chunks_per_big = total_small_chunks / total_big_chunks if total_big_chunks > 0 else 0
        avg_chunk_size = total_text_length / total_big_chunks if total_big_chunks > 0 else 0
        content_diversity = len(set(content_hashes)) / len(content_hashes) if content_hashes else 0
        
        stats = {
            'total_big_chunks': total_big_chunks,
            'total_small_chunks': total_small_chunks,
            'valid_chunks': valid_chunks,
            'empty_chunks': empty_chunks,
            'total_text_length': total_text_length,
            'avg_small_chunks_per_big': round(avg_small_chunks_per_big, 2),
            'avg_chunk_size': round(avg_chunk_size, 2),
            'min_chunk_size': min(chunk_sizes) if chunk_sizes else 0,
            'max_chunk_size': max(chunk_sizes) if chunk_sizes else 0,
            'content_diversity': round(content_diversity, 3),
            'quality_score': round(valid_chunks / total_big_chunks if total_big_chunks > 0 else 0, 3),
            'metadata': json_data.get('_metadata', {}),
            'calculated_at': datetime.now().isoformat()
        }
        
        logger.info(f"Calculated comprehensive chunk statistics: {stats['total_big_chunks']} chunks, {stats['quality_score']} quality score")
        return stats
        
    except Exception as e:
        logger.error(f"Error calculating chunk statistics: {e}")
        return {
            'total_big_chunks': 0,
            'total_small_chunks': 0,
            'valid_chunks': 0,
            'empty_chunks': 0,
            'total_text_length': 0,
            'avg_small_chunks_per_big': 0,
            'avg_chunk_size': 0,
            'min_chunk_size': 0,
            'max_chunk_size': 0,
            'content_diversity': 0,
            'quality_score': 0,
            'error': str(e),
            'calculated_at': datetime.now().isoformat()
        }


def convert_violations_json_to_readable(json_content: str) -> str:
    """
    Convert JSON violations format to human-readable markdown.
    Now supports the new content_name field from AI prompt.
    
    Args:
        json_content (str): JSON string with violations
        
    Returns:
        str: Human-readable markdown format
    """
    try:
        violations_data = json.loads(json_content)
        violations = violations_data.get("violations", [])
        
        if not violations:
            return "✅ **No violations found in this section.**\n\n"
        
        readable_parts = []
        
        for i, violation in enumerate(violations, 1):
            severity_emoji = {
                "critical": "🔴",
                "medium": "🟡", 
                "low": "🔵"
            }.get(violation.get("severity", "medium"), "🟡")
            
            violation_text = f"""**{severity_emoji} Violation {i}**
- **Issue:** {violation.get('violation_type', 'Unknown violation')}
- **Problematic Text:** "{violation.get('problematic_text', 'N/A')}"
- **Translation:** "{violation.get('translation', 'N/A')}"
- **Guideline Reference:** Section {violation.get('guideline_section', 'N/A')} (Page {violation.get('page_number', 'N/A')})
- **Severity:** {violation.get('severity', 'medium').title()}
- **Suggested Fix:** "{violation.get('suggested_rewrite', 'No suggestion provided')}"
- **Translation of Fix:** "{violation.get('rewrite_translation', 'N/A')}"

"""
            readable_parts.append(violation_text)
        
        return ''.join(readable_parts)
        
    except json.JSONDecodeError:
        # Fallback: return original content if not JSON
        logger.warning("Content is not valid JSON, returning as-is")
        return json_content
    except Exception as e:
        logger.error(f"Error converting JSON to readable format: {e}")
        return f"Error processing violations: {str(e)}\n\n"


def create_grouped_violations_report(analysis_results: list) -> str:
    """
    Create a violations report grouped by content sections using content_name.
    
    Args:
        analysis_results (list): List of chunk analysis results from AI
        
    Returns:
        str: Complete grouped violations report
    """
    try:
        readable_parts = []
        
        for result in analysis_results:
            if not result.get('success'):
                continue
                
            chunk_idx = result.get('chunk_index', 'Unknown')
            
            # Extract content_name and violations from AI response
            try:
                ai_response = json.loads(result['content'])
                content_name = ai_response.get('content_name', f'Content Section {chunk_idx}')
                violations = ai_response.get('violations', [])
                
                # Only add section if it has violations
                if violations:
                    readable_parts.append(f"## {content_name}\n\n")
                    
                    # Convert violations for this section
                    violations_content = convert_violations_json_to_readable(result['content'])
                    readable_parts.append(violations_content)
                    
            except json.JSONDecodeError:
                # Fallback if AI response isn't valid JSON
                logger.warning(f"Invalid JSON response for chunk {chunk_idx}")
                continue
        
        if not readable_parts:
            return "✅ **No violations found across all content sections.**\n\n"
        
        return ''.join(readable_parts)
        
    except Exception as e:
        logger.error(f"Error creating grouped report: {e}")
        return f"Error creating grouped report: {str(e)}\n\n"


def compare_json_content(json1: str, json2: str) -> Dict[str, Any]:
    """
    Compare two JSON content strings for differences.
    
    FIXED: New function to help detect content changes
    
    Args:
        json1 (str): First JSON string
        json2 (str): Second JSON string
        
    Returns:
        dict: Comparison results
    """
    try:
        hash1 = _generate_content_hash(json1)
        hash2 = _generate_content_hash(json2)
        
        data1 = parse_json_output(json1)
        data2 = parse_json_output(json2)
        
        if not data1 or not data2:
            return {
                'identical': False,
                'error': 'Failed to parse one or both JSON strings',
                'hash1': hash1,
                'hash2': hash2
            }
        
        stats1 = get_chunk_statistics(data1)
        stats2 = get_chunk_statistics(data2)
        
        return {
            'identical': hash1 == hash2,
            'hash1': hash1,
            'hash2': hash2,
            'chunks1': stats1.get('total_big_chunks', 0),
            'chunks2': stats2.get('total_big_chunks', 0),
            'length1': len(json1),
            'length2': len(json2),
            'content_diversity1': stats1.get('content_diversity', 0),
            'content_diversity2': stats2.get('content_diversity', 0),
            'compared_at': datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error comparing JSON content: {e}")
        return {
            'identical': False,
            'error': str(e),
            'compared_at': datetime.now().isoformat()
        }


def validate_content_freshness(content_data: Dict[str, Any], ai_result: Dict[str, Any]) -> Dict[str, bool]:
    """
    Validate that AI results correspond to the given content data.
    
    FIXED: New function for comprehensive freshness validation
    
    Args:
        content_data (dict): Content processing result
        ai_result (dict): AI analysis result
        
    Returns:
        dict: Validation results with specific checks
    """
    try:
        validation = {
            'is_fresh': True,
            'timestamp_match': True,
            'url_match': True,
            'content_match': True,
            'errors': []
        }
        
        # Check processing timestamps
        content_timestamp = content_data.get('processing_timestamp')
        ai_timestamp = ai_result.get('processing_timestamp')
        
        if content_timestamp is not None and ai_timestamp is not None:
            validation['timestamp_match'] = (content_timestamp == ai_timestamp)
        else:
            validation['timestamp_match'] = False
            validation['errors'].append('Missing timestamp data')
        
        # Check source URLs
        content_url = content_data.get('url')
        ai_url = ai_result.get('source_url')
        
        if content_url and ai_url:
            validation['url_match'] = (content_url == ai_url)
        else:
            validation['url_match'] = False
            validation['errors'].append('Missing URL data')
        
        # Check content hashes if available
        content_json = content_data.get('json_output')
        ai_content_hash = ai_result.get('content_hash')
        
        if content_json and ai_content_hash:
            if isinstance(content_json, dict):
                # Convert back to string for hashing
                json_string = json.dumps(content_json, sort_keys=True)
                current_hash = _generate_content_hash(json_string)
            else:
                current_hash = _generate_content_hash(str(content_json))
            validation['content_match'] = (current_hash == ai_content_hash)
        else:
            validation['content_match'] = True  # Assume match if no hash data
        
        # Overall freshness determination
        validation['is_fresh'] = (
            validation['timestamp_match'] and 
            validation['url_match'] and 
            validation['content_match']
        )
        
        logger.info(f"Content freshness validation: {'Fresh' if validation['is_fresh'] else 'Stale'}")
        return validation
        
    except Exception as e:
        logger.error(f"Error validating content freshness: {e}")
        return {
            'is_fresh': False,
            'timestamp_match': False,
            'url_match': False,
            'content_match': False,
            'errors': [str(e)]
        }


def _generate_content_hash(content: str) -> str:
    """
    Generate a hash for content to enable quick comparison.
    
    Args:
        content (str): Content to hash
        
    Returns:
        str: SHA-256 hash of the content
    """
    return hashlib.sha256(content.encode('utf-8')).hexdigest()[:16]  # Short hash for display


def _create_display_version(json_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create a version of JSON data suitable for display (removing internal metadata).
    
    Args:
        json_data (dict): Original JSON data
        
    Returns:
        dict: Display version without internal fields
    """
    if not isinstance(json_data, dict):
        return json_data
    
    display_data = {}
    for key, value in json_data.items():
        # Skip internal metadata fields
        if key.startswith('_'):
            continue
        display_data[key] = value
    
    return display_data


def get_content_summary(json_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Get a quick summary of JSON content for UI display.
    
    FIXED: New function for quick content overview
    
    Args:
        json_data (dict): Parsed JSON data
        
    Returns:
        dict: Content summary
    """
    try:
        stats = get_chunk_statistics(json_data)
        metadata = json_data.get('_metadata', {})
        
        return {
            'total_chunks': stats.get('total_big_chunks', 0),
            'valid_chunks': stats.get('valid_chunks', 0),
            'total_length': stats.get('total_text_length', 0),
            'quality_score': stats.get('quality_score', 0),
            'content_hash': metadata.get('content_hash', 'unknown'),
            'parsed_at': metadata.get('parsed_at', 'unknown'),
            'avg_chunk_size': stats.get('avg_chunk_size', 0)
        }
        
    except Exception as e:
        logger.error(f"Error getting content summary: {e}")
        return {
            'total_chunks': 0,
            'valid_chunks': 0,
            'total_length': 0,
            'quality_score': 0,
            'content_hash': 'error',
            'parsed_at': 'error',
            'avg_chunk_size': 0,
            'error': str(e)
        }


# FIXED: Enhanced exports for better module interface
__all__ = [
    'convert_violations_json_to_readable',
    'create_grouped_violations_report',  # NEW
    'decode_unicode_escapes',
    'extract_big_chunks',
    'parse_json_output',
    'format_json_for_display',
    'get_display_json_string',
    'validate_chunk_structure',
    'get_chunk_statistics',
    'compare_json_content',
    'validate_content_freshness',
    'get_content_summary'
]