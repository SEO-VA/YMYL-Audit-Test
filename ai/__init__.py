#!/usr/bin/env python3
"""
AI module for YMYL Audit Tool
Optimized Assistant API client for performance and reliability
"""

from .assistant_client import (
    OptimizedAssistantClient,
    process_chunks_async,
    cancel_current_processing,
    process_chunks_with_cancellation,
    ChunkAnalysis
)

__all__ = [
    'OptimizedAssistantClient',
    'process_chunks_async',
    'cancel_current_processing', 
    'process_chunks_with_cancellation',
    'ChunkAnalysis'
]
