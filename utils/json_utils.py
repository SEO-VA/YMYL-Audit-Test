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

def _generate_content_hash(content: str) -> str:
    """Generate a hash for content to enable quick comparison."""
    try:
        return hashlib.sha256(str(content).encode('utf-8')).hexdigest()[:16]
    except Exception:
        return "unknown_hash"


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
    Keeps all current violation details, no grouping (original function).
    
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
        return json_content
    except Exception as e:
        return f"Error processing violations: {str(e)}\n\n"


def create_grouped_violations_report(analysis_results: list, chunks_data: list = None) -> str:
    """
    Create a violations report grouped by content sections with meaningful headers.
    
    Args:
        analysis_results (list): List of chunk analysis results from AI
        chunks_data (list): Original chunk data with content text
        
    Returns:
        str: Complete grouped violations report
    """
    try:
        readable_parts = []
        
        for result in analysis_results:
            if not result.get('success'):
                continue
                
            chunk_idx = result.get('chunk_index', 'Unknown')
            
            # Get section name from chunk content
            section_name = extract_section_name_from_chunk(chunk_idx, chunks_data)
            
            # Convert violations for this chunk
            violations_content = convert_violations_json_to_readable(result['content'])
            
            # Only add section if it has violations
            if "No violations found" not in violations_content:
                readable_parts.append(f"## {section_name}\n\n")
                readable_parts.append(violations_content)
        
        if not readable_parts:
            return "✅ **No violations found across all content sections.**\n\n"
        
        return ''.join(readable_parts)
        
    except Exception as e:
        return f"Error creating grouped report: {str(e)}\n\n"


def extract_section_name_from_chunk(chunk_index: int, chunks_data: list = None) -> str:
    """
    Extract a meaningful section name from chunk content.
    
    Args:
        chunk_index (int): Index of the chunk
        chunks_data (list): Original chunk data with text content
        
    Returns:
        str: Meaningful section name based on content
    """
    try:
        if not chunks_data:
            return f"Content Section {chunk_index}"
        
        # Find the matching chunk
        chunk_content = None
        for chunk in chunks_data:
            if chunk.get('index') == chunk_index:
                chunk_content = chunk.get('text', '')
                break
        
        if not chunk_content:
            return f"Content Section {chunk_index}"
        
        # Extract meaningful name from content
        lines = chunk_content.split('\n')
        
        # Look for H1, H2, or first meaningful content line
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Check for headings
            if line.startswith('H1:'):
                title = line[3:].strip()
                return clean_section_title(title)
            elif line.startswith('H2:'):
                title = line[3:].strip()
                return clean_section_title(title)
            elif line.startswith('SUBTITLE:'):
                title = line[9:].strip()
                return clean_section_title(title)
            elif line.startswith('CONTENT:') and len(line) > 20:
                # Use first part of content as title
                content = line[8:].strip()
                title = content.split('.')[0]  # First sentence
                return clean_section_title(title)
        
        # Fallback: use first non-empty line
        for line in lines:
            if line.strip() and len(line.strip()) > 10:
                # Remove content type prefixes
                clean_line = line.strip()
                for prefix in ['H1:', 'H2:', 'H3:', 'CONTENT:', 'LEAD:', 'SUBTITLE:']:
                    if clean_line.startswith(prefix):
                        clean_line = clean_line[len(prefix):].strip()
                        break
                
                if clean_line:
                    title = clean_line.split('.')[0]  # First sentence
                    return clean_section_title(title)
        
        return f"Content Section {chunk_index}"
        
    except Exception as e:
        return f"Content Section {chunk_index}"


def clean_section_title(title: str, max_length: int = 60) -> str:
    """
    Clean and format section title for header use.
    
    Args:
        title (str): Raw title text
        max_length (int): Maximum length for title
        
    Returns:
        str: Cleaned title
    """
    try:
        # Remove quotes and extra whitespace
        title = title.strip(' "\'')
        
        # Truncate if too long
        if len(title) > max_length:
            title = title[:max_length].strip()
            # Try to end at word boundary
            last_space = title.rfind(' ')
            if last_space > max_length * 0.7:
                title = title[:last_space]
            title += "..."
        
        # Capitalize appropriately
        if title.isupper():
            title = title.title()
        elif title.islower():
            title = title.capitalize()
        
        return title if title else "Content Section"
        
    except Exception:
        return "Content Section"


# Add to __all__ list at the bottom of utils/json_utils.py:
__all__ = [
    'convert_violations_json_to_readable',
    'create_grouped_violations_report',  # NEW
    'extract_section_name_from_chunk',    # NEW
    'clean_section_title',                # NEW
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