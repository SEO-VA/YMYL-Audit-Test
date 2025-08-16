#!/usr/bin/env python3
"""
OpenAI Assistant Client for YMYL Audit Tool
UPDATED: Single request architecture - analyzes full content in one call
"""

import asyncio
import time
import json
from typing import Dict, Any, Optional
from openai import OpenAI
from config.settings import ANALYZER_ASSISTANT_ID, SINGLE_REQUEST_TIMEOUT
from utils.logging_utils import setup_logger

logger = setup_logger(__name__)


class AssistantClient:
    """Client for single-request AI analysis using OpenAI Assistant API."""
    
    def __init__(self, api_key: str, assistant_id: str = ANALYZER_ASSISTANT_ID):
        self.client = OpenAI(api_key=api_key)
        self.assistant_id = assistant_id
        logger.info(f"AssistantClient initialized for single-request analysis")

    async def analyze_full_content(self, json_content: str, max_retries: int = 3) -> Dict[str, Any]:
        """
        Analyze full content in single request.
        
        Args:
            json_content (str): Complete chunked JSON content
            max_retries (int): Maximum retry attempts
            
        Returns:
            dict: Analysis result with success status and AI response
        """
        logger.info(f"Starting full content analysis ({len(json_content):,} characters)")
        
        for attempt in range(max_retries + 1):
            try:
                result = await self._single_analysis_attempt(json_content)
                
                if result["success"]:
                    logger.info(f"Analysis successful on attempt {attempt + 1}")
                    return result
                else:
                    logger.warning(f"Analysis failed on attempt {attempt + 1}: {result.get('error')}")
                    
            except Exception as e:
                logger.error(f"Exception during analysis attempt {attempt + 1}: {str(e)}")
                
                if attempt == max_retries:
                    return {
                        "success": False,
                        "error": f"Failed after {max_retries + 1} attempts. Last error: {str(e)}",
                        "attempts": attempt + 1
                    }
                
                # Wait before retry
                wait_time = 2 ** attempt
                logger.info(f"Waiting {wait_time} seconds before retry...")
                await asyncio.sleep(wait_time)
        
        return {
            "success": False,
            "error": f"Failed after {max_retries + 1} attempts",
            "attempts": max_retries + 1
        }

    async def _single_analysis_attempt(self, json_content: str) -> Dict[str, Any]:
        """Perform single analysis attempt with full content."""
        try:
            # Create thread
            thread = self.client.beta.threads.create()
            thread_id = thread.id
            logger.debug(f"Created thread {thread_id}")
            
            # Add message with full content
            self.client.beta.threads.messages.create(
                thread_id=thread_id,
                role="user",
                content=json_content
            )
            logger.debug(f"Added full content to thread {thread_id}")
            
            # Create and run assistant
            run = self.client.beta.threads.runs.create(
                thread_id=thread_id,
                assistant_id=self.assistant_id
            )
            run_id = run.id
            logger.debug(f"Started run {run_id}")
            
            # Poll for completion with extended timeout
            start_time = time.time()
            max_wait_time = getattr(self, 'timeout', SINGLE_REQUEST_TIMEOUT)
            
            while run.status in ['queued', 'in_progress']:
                if time.time() - start_time > max_wait_time:
                    logger.error(f"Analysis timeout after {max_wait_time} seconds")
                    return {
                        "success": False,
                        "error": f"Analysis timeout after {max_wait_time} seconds"
                    }
                
                await asyncio.sleep(2)  # Longer polling interval for large requests
                run = self.client.beta.threads.runs.retrieve(
                    thread_id=thread_id,
                    run_id=run_id
                )
            
            processing_time = time.time() - start_time
            logger.debug(f"Analysis completed in {processing_time:.2f} seconds with status: {run.status}")
            
            # Handle completion status
            if run.status == 'completed':
                return await self._extract_response(thread_id, processing_time)
            
            elif run.status == 'failed':
                error_msg = f"Assistant run failed: {getattr(run, 'last_error', 'Unknown error')}"
                logger.error(error_msg)
                return {
                    "success": False,
                    "error": error_msg
                }
            
            else:
                error_msg = f"Unexpected run status: {run.status}"
                logger.error(error_msg)
                return {
                    "success": False,
                    "error": error_msg
                }
                
        except Exception as e:
            logger.error(f"Exception in analysis attempt: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

    async def _extract_response(self, thread_id: str, processing_time: float) -> Dict[str, Any]:
        """Extract and validate AI response."""
        try:
            # Get messages from thread
            messages = self.client.beta.threads.messages.list(thread_id=thread_id)
            
            if not messages.data:
                return {
                    "success": False,
                    "error": "No messages found in thread"
                }
            
            # Get assistant's response
            assistant_message = messages.data[0]
            
            if not assistant_message.content:
                return {
                    "success": False,
                    "error": "Empty response from assistant"
                }
            
            # Extract text content
            response_content = assistant_message.content[0].text.value
            
            if not response_content or not response_content.strip():
                return {
                    "success": False,
                    "error": "Assistant returned empty content"
                }
            
            # Validate JSON response format
            try:
                ai_data = json.loads(response_content)
                if not isinstance(ai_data, list):
                    return {
                        "success": False,
                        "error": "AI response is not a JSON array as expected"
                    }
            except json.JSONDecodeError as e:
                return {
                    "success": False,
                    "error": f"AI response is not valid JSON: {str(e)}"
                }
            
            logger.info(f"Successfully extracted AI response ({len(response_content):,} characters)")
            
            return {
                "success": True,
                "content": ai_data,
                "processing_time": processing_time,
                "response_length": len(response_content),
                "thread_id": thread_id
            }
            
        except Exception as e:
            logger.error(f"Error extracting response: {str(e)}")
            return {
                "success": False,
                "error": f"Error extracting response: {str(e)}"
            }

    def validate_api_key(self) -> bool:
        """Validate API key."""
        try:
            models = self.client.models.list()
            logger.info("API key validation successful")
            return True
        except Exception as e:
            logger.error(f"API key validation failed: {str(e)}")
            return False

    def get_assistant_info(self) -> Optional[Dict[str, Any]]:
        """Get assistant information."""
        try:
            assistant = self.client.beta.assistants.retrieve(self.assistant_id)
            return {
                "id": assistant.id,
                "name": assistant.name,
                "model": assistant.model,
                "description": assistant.description
            }
        except Exception as e:
            logger.error(f"Error retrieving assistant info: {str(e)}")
            return None

    async def cleanup(self):
        """Clean up resources."""
        logger.info("AssistantClient cleanup completed")

    def __del__(self):
        """Destructor."""
        try:
            logger.debug("AssistantClient destructor called")
        except Exception:
            pass