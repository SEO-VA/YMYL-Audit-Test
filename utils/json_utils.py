#!/usr/bin/env python3
"""
JSON processing utilities for YMYL Audit Tool

Helper functions for parsing and manipulating JSON data.

FIXED: Enhanced Unicode handling to prevent surrogate pair errors
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
    ENHANCED: Decode Unicode escape sequences while handling surrogate pairs safely.
    This is the single source of truth for Unicode decoding.
    
    Args:
        text (str): Text with potential Unicode escapes
        
    Returns:
        str: Text with decoded Unicode characters, surrogates safely handled
    """
    try:
        def safe_decode_match(match):
            try:
                unicode_code = match.group(1)
                code_point = int(unicode_code, 16)
                
                # Check for surrogate pairs (0xD800-0xDFFF range)
                if 0xD800 <= code_point <= 0xDFFF:
                    # This is a surrogate - replace with safe replacement character
                    logger.warning(f"Replacing surrogate Unicode \\u{unicode_code} with replacement character")
                    return '\uFFFD'  # Unicode replacement character
                
                # Normal Unicode character
                return chr(code_point)
                
            except (ValueError, OverflowError) as e:
                logger.warning(f"Invalid Unicode escape \\u{match.group(1)}: {e}")
                return '\uFFFD'  # Unicode replacement character
        
        # First pass: handle \\u sequences
        decoded = re.sub(r'\\u([0-9a-fA-F]{4})', safe_decode_match, text)
        
        # Second pass: clean any remaining problematic characters
        decoded = clean_surrogate_pairs(decoded)
        
        # Log if decoding actually changed something
        if decoded != text:
            original_unicode_count = text.count('\\u')
            remaining_unicode_count = decoded.count('\\u')
            logger.debug(f"Unicode decoding: {original_unicode_count} sequences found, {remaining_unicode_count} remaining")
        
        return decoded
        
    except Exception as e:
        logger.error(f"Unicode decoding failed: {e}")
        # Return cleaned version as fallback
        return clean_surrogate_pairs(text)


def clean_surrogate_pairs(text: str) -> str:
    """
    Clean surrogate pairs and other problematic Unicode characters from text.
    
    Args:
        text (str): Text that may contain surrogate pairs
        
    Returns:
        str: Cleaned text safe for UTF-8 encoding
    """
    try:
        # Method 1: Use encode with 'replace' error handling
        # This will replace problematic characters with '?'
        cleaned = text.encode('utf-8', errors='replace').decode('utf-8')
        
        # Method 2: More aggressive cleaning - replace surrogates with Unicode replacement character
        import unicodedata
        
        def replace_problematic_char(char):
            try:
                # Test if character can be encoded safely
                char.encode('utf-8')
                return char
            except UnicodeEncodeError:
                # Replace with Unicode replacement character
                return '\uFFFD'
        
        # Apply character-by-character cleaning
        final_cleaned = ''.join(replace_problematic_char(char) for char in cleaned)
        
        if final_cleaned != text:
            problem_chars = len(text) - len([c for c in text if c == replace_problematic_char(c)])
            logger.info(f"Cleaned {problem_chars} problematic Unicode characters")
        
        return final_cleaned
        
    except Exception as e:
        logger.error(f"Error cleaning surrogate pairs: {e}")
        # Last resort: use ASCII-safe encoding
        return text.encode('ascii', errors='replace').decode('ascii')


def safe_json_dumps(data: Any, **kwargs) -> str:
    """
    Safely serialize data to JSON with Unicode handling.
    
    Args:
        data: Data to serialize
        **kwargs: Additional arguments for json.dumps
        
    Returns:
        str: JSON string safe for UTF-8 encoding
    """
    try:
        # Set safe defaults
        safe_kwargs = {
            'ensure_ascii': False,  # Allow Unicode characters
            'separators': (',', ': '),
            'indent': kwargs.get('indent', 2)
        }
        safe_kwargs.update(kwargs)
        
        # First attempt: normal JSON serialization
        json_str = json.dumps(data, **safe_kwargs)
        
        # Clean any problematic characters
        cleaned_json = clean_surrogate_pairs(json_str)
        
        # Verify the result is valid JSON
        json.loads(cleaned_json)  # This will raise if invalid
        
        return cleaned_json
        
    except (UnicodeEncodeError, json.JSONDecodeError) as e:
        logger.warning(f"JSON serialization had Unicode issues, using ASCII-safe mode: {e}")
        
        # Fallback: use ensure_ascii=True
        safe_kwargs['ensure_ascii'] = True
        try:
            return json.dumps(data, **safe_kwargs)
        except Exception as fallback_error:
            logger.error(f"Even ASCII-safe JSON serialization failed: {fallback_error}")
            return '{"error": "JSON serialization failed due to Unicode issues"}'


def safe_json_loads(json_str: str) -> Any:
    """
    Safely parse JSON string with Unicode handling.
    
    Args:
        json_str (str): JSON string to parse
        
    Returns:
        Any: Parsed data or None if parsing fails
    """
    try:
        # Clean the input first
        cleaned_json = clean_surrogate_pairs(json_str)
        
        # Attempt to parse
        return json.loads(cleaned_json)
        
    except json.JSONDecodeError as e:
        logger.error(f"JSON parsing failed even after cleaning: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error in safe JSON parsing: {e}")
        return None


def extract_big_chunks(json_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Extract and format big chunks for AI processing.
    
    ENHANCED: Now with safe Unicode handling
    
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
            
            # Join small chunks with newlines and clean Unicode
            raw_text = '\n'.join(str(sc) for sc in small_chunks)
            cleaned_text = clean_surrogate_pairs(raw_text)
            
            # Add content validation and metadata
            chunk_data = {
                "index": chunk_index,
                "text": cleaned_text,
                "count": len(small_chunks),
                "text_length": len(cleaned_text),
                "text_hash": _generate_content_hash(cleaned_text),
                "extracted_at": datetime.now().isoformat(),
                "unicode_cleaned": cleaned_text != raw_text
            }
            
            # Validate chunk has meaningful content
            if cleaned_text.strip() and len(cleaned_text.strip()) > 10:
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
    
    ENHANCED: Now uses safe Unicode handling
    
    Args:
        json_string (str): JSON string to parse
        
    Returns:
        dict or None: Parsed JSON data with metadata or None if parsing fails
    """
    try:
        if not json_string or not json_string.strip():
            logger.error("Empty JSON string provided")
            return None
        
        # Use safe JSON parsing
        parsed_data = safe_json_loads(json_string)
        if parsed_data is None:
            return None
        
        # Add metadata for tracking
        if isinstance(parsed_data, dict):
            parsed_data['_metadata'] = {
                'parsed_at': datetime.now().isoformat(),
                'content_hash': _generate_content_hash(json_string),
                'content_length': len(json_string),
                'parser_version': '1.3.0',  # Updated version
                'unicode_cleaned': True
            }
        
        logger.info(f"Successfully parsed JSON ({len(json_string):,} characters)")
        return parsed_data
        
    except Exception as e:
        logger.error(f"Unexpected error parsing JSON: {e}")
        return None


def format_json_for_display(json_data: Union[Dict[str, Any], str], max_length: int = 1000) -> str:
    """
    Format JSON data for display with proper Unicode handling.
    
    ENHANCED: Now uses safe JSON serialization
    
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
            formatted = safe_json_dumps(display_data, indent=2)
        elif isinstance(json_data, str):
            # If it's already a string, try to parse and reformat for consistency
            parsed = safe_json_loads(json_data)
            if parsed is not None:
                display_data = _create_display_version(parsed) if isinstance(parsed, dict) else parsed
                formatted = safe_json_dumps(display_data, indent=2)
            else:
                # If parsing fails, clean the string
                formatted = clean_surrogate_pairs(json_data)
        else:
            # Fallback to string representation
            formatted = clean_surrogate_pairs(str(json_data))
        
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
        error_msg = f"Error formatting JSON: {str(e)}"
        return clean_surrogate_pairs(error_msg)


def get_display_json_string(json_data: Union[Dict[str, Any], str]) -> str:
    """
    Get a clean JSON string for UI display with proper Unicode handling.
    
    ENHANCED: Now uses safe JSON serialization
    
    Args:
        json_data: JSON data (dict or string)
        
    Returns:
        str: Clean, readable JSON string
    """
    try:
        if isinstance(json_data, dict):
            # Convert dict to formatted JSON string
            display_data = _create_display_version(json_data)
            return safe_json_dumps(display_data, indent=2)
        elif isinstance(json_data, str):
            # If it's a string, ensure it's properly formatted JSON
            parsed = safe_json_loads(json_data)
            if parsed is not None:
                if isinstance(parsed, dict):
                    display_data = _create_display_version(parsed)
                    return safe_json_dumps(display_data, indent=2)
                else:
                    return safe_json_dumps(parsed, indent=2)
            else:
                # If it's not valid JSON, return cleaned string
                return clean_surrogate_pairs(json_data)
        else:
            # Convert other types to JSON
            return safe_json_dumps(json_data, indent=2)
            
    except Exception as e:
        logger.error(f"Error creating display JSON string: {e}")
        return clean_surrogate_pairs(str(json_data))


def validate_chunk_structure(json_data: Dict[str, Any]) -> bool:
    """
    Validate that JSON data has the expected chunk structure.
    
    ENHANCED: Better validation with Unicode safety
    
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
            
            # Validate chunk content quality with Unicode safety
            if len(small_chunks) == 0:
                logger.warning(f"Chunk {i} has empty 'small_chunks'")
                continue
            
            # Check if chunks have meaningful content (with Unicode cleaning)
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


def get_chunk_statistics(json_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Calculate comprehensive statistics about the chunks.
    
    ENHANCED: Now includes Unicode cleaning statistics
    
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
        unicode_issues_fixed = 0
        
        # Calculate text statistics
        total_text_length = 0
        chunk_sizes = []
        content_hashes = []
        
        for chunk in big_chunks:
            small_chunks = chunk.get('small_chunks', [])
            raw_text = '\n'.join(str(sc) for sc in small_chunks)
            cleaned_text = clean_surrogate_pairs(raw_text)
            
            # Track Unicode issues
            if cleaned_text != raw_text:
                unicode_issues_fixed += 1
            
            chunk_length = len(cleaned_text)
            
            total_small_chunks += len(small_chunks)
            total_text_length += chunk_length
            chunk_sizes.append(chunk_length)
            
            # Track content quality
            if cleaned_text.strip() and len(cleaned_text.strip()) > 10:
                valid_chunks += 1
                content_hashes.append(_generate_content_hash(cleaned_text))
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
            'unicode_issues_fixed': unicode_issues_fixed,  # NEW
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
        
        logger.info(f"Calculated comprehensive chunk statistics: {stats['total_big_chunks']} chunks, {stats['quality_score']} quality score, {unicode_issues_fixed} Unicode issues fixed")
        return stats
        
    except Exception as e:
        logger.error(f"Error calculating chunk statistics: {e}")
        return {
            'total_big_chunks': 0,
            'total_small_chunks': 0,
            'valid_chunks': 0,
            'empty_chunks': 0,
            'unicode_issues_fixed': 0,
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
    
    ENHANCED: Safe Unicode handling
    
    Args:
        json_content (str): JSON string with violations
        
    Returns:
        str: Human-readable markdown format
    """
    try:
        # Use safe JSON parsing
        violations_data = safe_json_loads(json_content)
        if violations_data is None:
            return "❌ **Could not parse violations data.**\n\n"
        
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
            
            # Safely extract and clean all text fields
            violation_type = clean_surrogate_pairs(str(violation.get('violation_type', 'Unknown violation')))
            problematic_text = clean_surrogate_pairs(str(violation.get('problematic_text', 'N/A')))
            translation = clean_surrogate_pairs(str(violation.get('translation', 'N/A')))
            suggested_rewrite = clean_surrogate_pairs(str(violation.get('suggested_rewrite', 'No suggestion provided')))
            rewrite_translation = clean_surrogate_pairs(str(violation.get('rewrite_translation', 'N/A')))
            
            violation_text = f"""**{severity_emoji} Violation {i}**
- **Issue:** {violation_type}
- **Problematic Text:** "{problematic_text}"
- **Translation:** "{translation}"
- **Guideline Reference:** Section {violation.get('guideline_section', 'N/A')} (Page {violation.get('page_number', 'N/A')})
- **Severity:** {violation.get('severity', 'medium').title()}
- **Suggested Fix:** "{suggested_rewrite}"
- **Translation of Fix:** "{rewrite_translation}"

"""
            readable_parts.append(violation_text)
        
        return ''.join(readable_parts)
        
    except Exception as e:
        logger.error(f"Error converting JSON to readable format: {e}")
        # Return the original content cleaned
        return clean_surrogate_pairs(str(json_content)) + "\n\n"


def create_grouped_violations_report(analysis_results: list) -> str:
    """
    Create a violations report grouped by content sections using content_name.
    
    ENHANCED: Safe Unicode handling throughout
    
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
                ai_response = safe_json_loads(result['content'])
                if ai_response is None:
                    continue
                
                content_name = clean_surrogate_pairs(str(ai_response.get('content_name', f'Content Section {chunk_idx}')))
                violations = ai_response.get('violations', [])
                
                # Only add section if it has violations
                if violations:
                    readable_parts.append(f"## {content_name}\n\n")
                    
                    # Convert violations for this section
                    violations_content = convert_violations_json_to_readable(result['content'])
                    readable_parts.append(violations_content)
                    
            except Exception as e:
                # Fallback if AI response processing fails
                logger.warning(f"Error processing AI response for chunk {chunk_idx}: {e}")
                continue
        
        if not readable_parts:
            return "✅ **No violations found across all content sections.**\n\n"
        
        # Join and clean the final result
        final_result = ''.join(readable_parts)
        return clean_surrogate_pairs(final_result)
        
    except Exception as e:
        logger.error(f"Error creating grouped report: {e}")
        error_msg = f"Error creating grouped report: {str(e)}\n\n"
        return clean_surrogate_pairs(error_msg)


def compare_json_content(json1: str, json2: str) -> Dict[str, Any]:
    """
    Compare two JSON content strings for differences.
    
    ENHANCED: Safe Unicode handling for comparison
    
    Args:
        json1 (str): First JSON string
        json2 (str): Second JSON string
        
    Returns:
        dict: Comparison results
    """
    try:
        # Clean both inputs first
        clean_json1 = clean_surrogate_pairs(json1)
        clean_json2 = clean_surrogate_pairs(json2)
        
        hash1 = _generate_content_hash(clean_json1)
        hash2 = _generate_content_hash(clean_json2)
        
        data1 = safe_json_loads(clean_json1)
        data2 = safe_json_loads(clean_json2)
        
        if not data1 or not data2:
            return {
                'identical': False,
                'error': 'Failed to parse one or both JSON strings',
                'hash1': hash1,
                'hash2': hash2,
                'unicode_cleaned': clean_json1 != json1 or clean_json2 != json2
            }
        
        stats1 = get_chunk_statistics(data1)
        stats2 = get_chunk_statistics(data2)
        
        return {
            'identical': hash1 == hash2,
            'hash1': hash1,
            'hash2': hash2,
            'chunks1': stats1.get('total_big_chunks', 0),
            'chunks2': stats2.get('total_big_chunks', 0),
            'length1': len(clean_json1),
            'length2': len(clean_json2),
            'content_diversity1': stats1.get('content_diversity', 0),
            'content_diversity2': stats2.get('content_diversity', 0),
            'unicode_cleaned': clean_json1 != json1 or clean_json2 != json2,
            'compared_at': datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error comparing JSON content: {e}")
        return {
            'identical': False,
            'error': str(e),
            'unicode_cleaned': False,
            'compared_at': datetime.now().isoformat()
        }


def validate_content_freshness(content_data: Dict[str, Any], ai_result: Dict[str, Any]) -> Dict[str, bool]:
    """
    Validate that AI results correspond to the given content data.
    
    ENHANCED: Safe Unicode handling for validation
    
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
        
        # Check source URLs (with Unicode cleaning)
        content_url = clean_surrogate_pairs(str(content_data.get('url', '')))
        ai_url = clean_surrogate_pairs(str(ai_result.get('source_url', '')))
        
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
                # Convert back to string for hashing (with safe serialization)
                json_string = safe_json_dumps(content_json, sort_keys=True)
                current_hash = _generate_content_hash(json_string)
            else:
                cleaned_content = clean_surrogate_pairs(str(content_json))
                current_hash = _generate_content_hash(cleaned_content)
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
    
    ENHANCED: Safe Unicode handling for hashing
    
    Args:
        content (str): Content to hash
        
    Returns:
        str: SHA-256 hash of the content
    """
    try:
        # Clean the content first
        cleaned_content = clean_surrogate_pairs(content)
        return hashlib.sha256(cleaned_content.encode('utf-8')).hexdigest()[:16]  # Short hash for display
    except Exception as e:
        logger.warning(f"Error generating content hash: {e}")
        # Fallback to ASCII-safe hashing
        ascii_content = content.encode('ascii', errors='replace').decode('ascii')
        return hashlib.sha256(ascii_content.encode('ascii')).hexdigest()[:16]


def _create_display_version(json_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create a version of JSON data suitable for display (removing internal metadata).
    
    ENHANCED: Safe Unicode handling
    
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
        
        # Clean Unicode in string values
        if isinstance(value, str):
            display_data[key] = clean_surrogate_pairs(value)
        elif isinstance(value, list):
            # Clean Unicode in list items
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


def get_content_summary(json_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Get a quick summary of JSON content for UI display.
    
    ENHANCED: Safe Unicode handling for summary
    
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
            'unicode_issues_fixed': stats.get('unicode_issues_fixed', 0),  # NEW
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
            'unicode_issues_fixed': 0,
            'content_hash': 'error',
            'parsed_at': 'error',
            'avg_chunk_size': 0,
            'error': str(e)
        }


# Test function to validate Unicode handling
def test_unicode_handling():
    """
    Test function to validate Unicode handling improvements.
    """
    test_cases = [
        # Normal Unicode
        "Hello 世界",
        # Unicode escapes
        "Hello \\u4e16\\u754c",
        # Surrogate pairs (problematic)
        "Hello \\ud83d\\ude00",  # Emoji
        # Mixed content
        "Normal text with \\u4e16\\u754c and \\ud83d\\ude00",
        # JSON with Unicode
        '{"text": "Hello \\u4e16\\u754c", "emoji": "\\ud83d\\ude00"}'
    ]
    
    logger.info("Testing Unicode handling...")
    
    for i, test_case in enumerate(test_cases, 1):
        logger.info(f"Test {i}: {test_case[:50]}...")
        
        try:
            # Test decode_unicode_escapes
            decoded = decode_unicode_escapes(test_case)
            logger.info(f"  Decoded: {decoded[:50]}...")
            
            # Test clean_surrogate_pairs
            cleaned = clean_surrogate_pairs(decoded)
            logger.info(f"  Cleaned: {cleaned[:50]}...")
            
            # Test UTF-8 encoding
            encoded = cleaned.encode('utf-8')
            logger.info(f"  UTF-8 encoding: SUCCESS ({len(encoded)} bytes)")
            
        except Exception as e:
            logger.error(f"  Test {i} FAILED: {e}")
    
    logger.info("Unicode handling tests completed")


# ENHANCED: Enhanced exports for better module interface
__all__ = [
    'convert_violations_json_to_readable',
    'create_grouped_violations_report',
    'decode_unicode_escapes',
    'clean_surrogate_pairs',  # NEW
    'safe_json_dumps',  # NEW
    'safe_json_loads',  # NEW
    'extract_big_chunks',
    'parse_json_output',
    'format_json_for_display',
    'get_display_json_string',
    'validate_chunk_structure',
    'get_chunk_statistics',
    'compare_json_content',
    'validate_content_freshness',
    'get_content_summary',
    'test_unicode_handling'  # NEW
]