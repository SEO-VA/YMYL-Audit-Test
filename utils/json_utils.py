#!/usr/bin/env python3
"""
JSON processing utilities for YMYL Audit Tool

Helper functions for parsing and manipulating JSON data.
"""

import json
from typing import List, Dict, Any, Optional
from utils.logging_utils import setup_logger

logger = setup_logger(__name__)


def extract_big_chunks(json_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Extract and format big chunks for AI processing.
    
    Args:
        json_data (dict): Parsed JSON data from chunk processor
        
    Returns:
        list: List of chunk dictionaries with index, text, and count
    """
    try:
        big_chunks = json_data.get('big_chunks', [])
        chunks = []
        
        for chunk in big_chunks:
            chunk_index = chunk.get('big_chunk_index', len(chunks) + 1)
            small_chunks = chunk.get('small_chunks', [])
            
            # Join small chunks with newlines
            joined_text = '\n'.join(small_chunks)
            
            chunks.append({
                "index": chunk_index,
                "text": joined_text,
                "count": len(small_chunks)
            })
        
        logger.info(f"Extracted {len(chunks)} big chunks from JSON data")
        return chunks
        
    except Exception as e:
        logger.error(f"Error extracting big chunks: {e}")
        return []


def parse_json_output(json_string: str) -> Optional[Dict[str, Any]]:
    """
    Safely parse JSON string with error handling.
    
    Args:
        json_string (str): JSON string to parse
        
    Returns:
        dict or None: Parsed JSON data or None if parsing fails
    """
    try:
        return json.loads(json_string)
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON format: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error parsing JSON: {e}")
        return None


def validate_chunk_structure(json_data: Dict[str, Any]) -> bool:
    """
    Validate that JSON data has the expected chunk structure.
    
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
        
        # Validate each chunk structure
        for i, chunk in enumerate(big_chunks):
            if not isinstance(chunk, dict):
                logger.warning(f"Chunk {i} is not a dictionary")
                return False
            
            if 'small_chunks' not in chunk:
                logger.warning(f"Chunk {i} missing 'small_chunks'")
                return False
            
            if not isinstance(chunk['small_chunks'], list):
                logger.warning(f"Chunk {i} 'small_chunks' is not a list")
                return False
        
        logger.info(f"JSON structure validation passed for {len(big_chunks)} chunks")
        return True
        
    except Exception as e:
        logger.error(f"Error validating chunk structure: {e}")
        return False


def get_chunk_statistics(json_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Calculate statistics about the chunks.
    
    Args:
        json_data (dict): Parsed JSON data
        
    Returns:
        dict: Statistics about the chunks
    """
    try:
        big_chunks = json_data.get('big_chunks', [])
        
        total_big_chunks = len(big_chunks)
        total_small_chunks = sum(len(chunk.get('small_chunks', [])) for chunk in big_chunks)
        
        # Calculate text statistics
        total_text_length = 0
        chunk_sizes = []
        
        for chunk in big_chunks:
            small_chunks = chunk.get('small_chunks', [])
            chunk_text = '\n'.join(small_chunks)
            chunk_length = len(chunk_text)
            
            total_text_length += chunk_length
            chunk_sizes.append(chunk_length)
        
        # Calculate averages
        avg_small_chunks_per_big = total_small_chunks / total_big_chunks if total_big_chunks > 0 else 0
        avg_chunk_size = total_text_length / total_big_chunks if total_big_chunks > 0 else 0
        
        stats = {
            'total_big_chunks': total_big_chunks,
            'total_small_chunks': total_small_chunks,
            'total_text_length': total_text_length,
            'avg_small_chunks_per_big': round(avg_small_chunks_per_big, 2),
            'avg_chunk_size': round(avg_chunk_size, 2),
            'min_chunk_size': min(chunk_sizes) if chunk_sizes else 0,
            'max_chunk_size': max(chunk_sizes) if chunk_sizes else 0
        }
        
        logger.info(f"Calculated chunk statistics: {stats}")
        return stats
        
    except Exception as e:
        logger.error(f"Error calculating chunk statistics: {e}")
        return {
            'total_big_chunks': 0,
            'total_small_chunks': 0,
            'total_text_length': 0,
            'avg_small_chunks_per_big': 0,
            'avg_chunk_size': 0,
            'min_chunk_size': 0,
            'max_chunk_size': 0
        }


def format_json_for_display(json_data: Dict[str, Any], max_length: int = 1000) -> str:
    """
    Format JSON data for display with truncation if needed.
    
    Args:
        json_data (dict): JSON data to format
        max_length (int): Maximum length of formatted string
        
    Returns:
        str: Formatted JSON string
    """
    try:
        formatted = json.dumps(json_data, indent=2, ensure_ascii=False)
        
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
