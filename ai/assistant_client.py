#!/usr/bin/env python3
"""
OpenAI Assistant Client for YMYL Audit Tool

Handles direct interaction with OpenAI's Assistant API for content analysis.
Manages thread creation, message handling, and response extraction.
"""

import asyncio
import time
from typing import Dict, Any, Optional
from openai import OpenAI
from config.settings import ANALYZER_ASSISTANT_ID, MAX_PARALLEL_REQUESTS
from utils.logging_utils import setup_logger

logger = setup_logger(__name__)


class AssistantClient:
    """
    Client for interacting with OpenAI Assistant API.
    
    Handles:
    - Thread creation and management
    - Message sending and response retrieval
    - Error handling and retries
    - Response parsing and validation
    """
    
    def __init__(self, api_key: str, assistant_id: str = ANALYZER_ASSISTANT_ID):
        """
        Initialize the AssistantClient.
        
        Args:
            api_key (str): OpenAI API key
            assistant_id (str): Assistant ID to use for analysis
        """
        self.client = OpenAI(api_key=api_key)
        self.assistant_id = assistant_id
        logger.info(f"AssistantClient initialized with assistant: {assistant_id}")

    async def analyze_chunk(self, content: str, chunk_index: int, max_retries: int = 3) -> Dict[str, Any]:
        """
        Analyze a single content chunk using the OpenAI Assistant.
        
        Args:
            content (str): Content to analyze
            chunk_index (int): Index of the chunk for tracking
            max_retries (int): Maximum number of retry attempts
            
        Returns:
            dict: Analysis result with success status and content/error
        """
        logger.info(f"Starting analysis of chunk {chunk_index} ({len(content):,} characters)")
        
        for attempt in range(max_retries + 1):
            try:
                result = await self._single_analysis_attempt(content, chunk_index)
                
                if result["success"]:
                    logger.info(f"Analysis successful for chunk {chunk_index} on attempt {attempt + 1}")
                    return result
                else:
                    logger.warning(f"Analysis failed for chunk {chunk_index} on attempt {attempt + 1}: {result.get('error')}")
                    
            except Exception as e:
                logger.error(f"Exception during analysis of chunk {chunk_index}, attempt {attempt + 1}: {str(e)}")
                
                if attempt == max_retries:
                    return {
                        "success": False,
                        "error": f"Failed after {max_retries + 1} attempts. Last error: {str(e)}",
                        "chunk_index": chunk_index,
                        "attempts": attempt + 1
                    }
                
                # Wait before retry (exponential backoff)
                wait_time = 2 ** attempt
                logger.info(f"Waiting {wait_time} seconds before retry...")
                await asyncio.sleep(wait_time)
        
        return {
            "success": False,
            "error": f"Failed after {max_retries + 1} attempts",
            "chunk_index": chunk_index,
            "attempts": max_retries + 1
        }

    async def _single_analysis_attempt(self, content: str, chunk_index: int) -> Dict[str, Any]:
        """
        Perform a single analysis attempt.
        
        Args:
            content (str): Content to analyze
            chunk_index (int): Index of the chunk
            
        Returns:
            dict: Analysis result
        """
        try:
            # Create thread
            thread = self.client.beta.threads.create()
            thread_id = thread.id
            logger.debug(f"Created thread {thread_id} for chunk {chunk_index}")
            
            # Add message to thread
            self.client.beta.threads.messages.create(
                thread_id=thread_id,
                role="user",
                content=content
            )
            logger.debug(f"Added message to thread {thread_id}")
            
            # Create and run the assistant
            run = self.client.beta.threads.runs.create(
                thread_id=thread_id,
                assistant_id=self.assistant_id
            )
            run_id = run.id
            logger.debug(f"Started run {run_id} for thread {thread_id}")
            
            # Poll for completion
            start_time = time.time()
            max_wait_time = 300  # 5 minutes maximum
            
            while run.status in ['queued', 'in_progress']:
                if time.time() - start_time > max_wait_time:
                    logger.error(f"Analysis timeout for chunk {chunk_index} after {max_wait_time} seconds")
                    return {
                        "success": False,
                        "error": f"Analysis timeout after {max_wait_time} seconds",
                        "chunk_index": chunk_index
                    }
                
                await asyncio.sleep(1)
                run = self.client.beta.threads.runs.retrieve(
                    thread_id=thread_id,
                    run_id=run_id
                )
            
            processing_time = time.time() - start_time
            logger.debug(f"Run completed for chunk {chunk_index} in {processing_time:.2f} seconds with status: {run.status}")
            
            # Handle different completion statuses
            if run.status == 'completed':
                return await self._extract_response(thread_id, chunk_index, processing_time)
            
            elif run.status == 'failed':
                error_msg = f"Assistant run failed: {getattr(run, 'last_error', 'Unknown error')}"
                logger.error(f"Run failed for chunk {chunk_index}: {error_msg}")
                return {
                    "success": False,
                    "error": error_msg,
                    "chunk_index": chunk_index
                }
            
            elif run.status == 'requires_action':
                # Handle function calls if needed in the future
                error_msg = "Assistant requires action - not implemented"
                logger.error(f"Unexpected status for chunk {chunk_index}: {error_msg}")
                return {
                    "success": False,
                    "error": error_msg,
                    "chunk_index": chunk_index
                }
            
            else:
                error_msg = f"Unexpected run status: {run.status}"
                logger.error(f"Unexpected status for chunk {chunk_index}: {error_msg}")
                return {
                    "success": False,
                    "error": error_msg,
                    "chunk_index": chunk_index
                }
                
        except Exception as e:
            logger.error(f"Exception in single analysis attempt for chunk {chunk_index}: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "chunk_index": chunk_index
            }

    async def _extract_response(self, thread_id: str, chunk_index: int, processing_time: float) -> Dict[str, Any]:
        """
        Extract the assistant's response from the thread.
        
        Args:
            thread_id (str): Thread ID to extract from
            chunk_index (int): Chunk index for tracking
            processing_time (float): Time taken for processing
            
        Returns:
            dict: Extracted response data
        """
        try:
            # Get messages from thread
            messages = self.client.beta.threads.messages.list(thread_id=thread_id)
            
            if not messages.data:
                return {
                    "success": False,
                    "error": "No messages found in thread",
                    "chunk_index": chunk_index
                }
            
            # Get the assistant's response (first message is the most recent)
            assistant_message = messages.data[0]
            
            if not assistant_message.content:
                return {
                    "success": False,
                    "error": "Empty response from assistant",
                    "chunk_index": chunk_index
                }
            
            # Extract text content
            response_content = assistant_message.content[0].text.value
            
            if not response_content or not response_content.strip():
                return {
                    "success": False,
                    "error": "Assistant returned empty content",
                    "chunk_index": chunk_index
                }
            
            logger.info(f"Successfully extracted response for chunk {chunk_index} ({len(response_content):,} characters)")
            
            return {
                "success": True,
                "content": response_content,
                "chunk_index": chunk_index,
                "processing_time": processing_time,
                "response_length": len(response_content),
                "thread_id": thread_id
            }
            
        except Exception as e:
            logger.error(f"Error extracting response for chunk {chunk_index}: {str(e)}")
            return {
                "success": False,
                "error": f"Error extracting response: {str(e)}",
                "chunk_index": chunk_index
            }

    def validate_api_key(self) -> bool:
        """
        Validate that the API key works by making a simple request.
        
        Returns:
            bool: True if API key is valid, False otherwise
        """
        try:
            # Simple test request
            models = self.client.models.list()
            logger.info("API key validation successful")
            return True
        except Exception as e:
            logger.error(f"API key validation failed: {str(e)}")
            return False

    def get_assistant_info(self) -> Optional[Dict[str, Any]]:
        """
        Get information about the configured assistant.
        
        Returns:
            dict or None: Assistant information or None if error
        """
        try:
            assistant = self.client.beta.assistants.retrieve(self.assistant_id)
            return {
                "id": assistant.id,
                "name": assistant.name,
                "model": assistant.model,
                "description": assistant.description,
                "instructions": assistant.instructions[:200] + "..." if len(assistant.instructions) > 200 else assistant.instructions
            }
        except Exception as e:
            logger.error(f"Error retrieving assistant info: {str(e)}")
            return None

    async def cleanup(self):
        """Clean up any resources."""
        # Currently no persistent resources to clean up
        # But this method exists for future extensibility
        logger.info("AssistantClient cleanup completed")

    def __del__(self):
        """Destructor to ensure cleanup."""
        try:
            # Note: Can't call async cleanup in __del__, so we just log
            logger.debug("AssistantClient destructor called")
        except Exception:
            pass  # Ignore errors in destructor
