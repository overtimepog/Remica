import os
import time
import json
import logging
from typing import List, Tuple, Optional, Dict, Any
from dataclasses import dataclass
from openai import OpenAI
import requests

from ..config import config

logger = logging.getLogger(__name__)

@dataclass
class ModelResponse:
    """Response from OpenRouter model"""
    content: str
    model_used: str
    response_time: float
    cost: float = 0.0
    engine_used: Optional[str] = None

class OpenRouterClient:
    """Client for interacting with OpenRouter API"""
    
    def __init__(self):
        self.config = config.openrouter
        self.client = OpenAI(
            base_url=self.config.base_url,
            api_key=self.config.api_key
        )
        self.usage_count = 0
        self.session_start = time.time()
        
    def generate_response(
        self, 
        messages: List[Dict[str, str]], 
        max_retries: int = None
    ) -> Tuple[str, str]:
        """
        Generate response with fallback model support
        
        Args:
            messages: List of message dictionaries with 'role' and 'content'
            max_retries: Maximum number of retries (defaults to config)
            
        Returns:
            Tuple of (response_content, model_used)
        """
        max_retries = max_retries or config.app.max_retries
        models_to_try = [self.config.default_model] + self.config.fallback_models
        
        for model in models_to_try:
            try:
                logger.info(f"Attempting to use model: {model}")
                start_time = time.time()
                
                # Prepare headers
                headers = {}
                if self.config.http_referer:
                    headers["HTTP-Referer"] = self.config.http_referer
                if self.config.app_title:
                    headers["X-Title"] = self.config.app_title
                
                # Make API call
                response = self.client.chat.completions.create(
                    model=model,
                    messages=messages,
                    extra_headers=headers,
                    timeout=config.app.response_timeout
                )
                
                # Calculate response time
                response_time = time.time() - start_time
                
                # Update usage count
                self.usage_count += 1
                
                # Log success
                logger.info(f"Successfully received response from {model} in {response_time:.2f}s")
                
                return response.choices[0].message.content, model
                
            except Exception as e:
                logger.error(f"Model {model} failed: {str(e)}")
                continue
        
        raise Exception("All models failed to respond")
    
    def generate_structured_response(
        self,
        messages: List[Dict[str, str]],
        query_type: str = "general"
    ) -> ModelResponse:
        """
        Generate a structured response with metadata
        
        Args:
            messages: List of message dictionaries
            query_type: Type of query for logging/metrics
            
        Returns:
            ModelResponse object with content and metadata
        """
        start_time = time.time()
        
        try:
            content, model_used = self.generate_response(messages)
            response_time = time.time() - start_time
            
            # Calculate cost (0 for free models)
            cost = 0.0 if ":free" in model_used else self._calculate_cost(content, model_used)
            
            return ModelResponse(
                content=content,
                model_used=model_used,
                response_time=response_time,
                cost=cost,
                engine_used=query_type
            )
            
        except Exception as e:
            logger.error(f"Failed to generate structured response: {str(e)}")
            raise
    
    def check_rate_limits(self) -> Dict[str, Any]:
        """Check current rate limit status"""
        # Check if account has enhanced limits
        daily_limit = config.app.enhanced_request_limit if self._has_enhanced_limits() else config.app.daily_request_limit
        
        return {
            "daily_limit": daily_limit,
            "current_usage": self.usage_count,
            "remaining_calls": max(0, daily_limit - self.usage_count),
            "usage_percentage": (self.usage_count / daily_limit) * 100
        }
    
    def _has_enhanced_limits(self) -> bool:
        """Check if account has enhanced limits (simplified check)"""
        # In a real implementation, you would check account balance via API
        # For now, we'll assume basic limits
        return False
    
    def _calculate_cost(self, content: str, model: str) -> float:
        """Calculate cost for paid models (simplified)"""
        # Rough estimate: 1000 tokens ~= 750 words
        word_count = len(content.split())
        token_count = word_count * 1.33
        
        # Simplified pricing (would need real pricing data)
        cost_per_1k_tokens = 0.001  # $0.001 per 1K tokens
        return (token_count / 1000) * cost_per_1k_tokens
    
    def get_available_models(self) -> List[str]:
        """Get list of available models"""
        return [self.config.default_model] + self.config.fallback_models
    
    def test_connection(self) -> bool:
        """Test connection to OpenRouter API"""
        try:
            # Simple test message
            test_messages = [
                {"role": "system", "content": "You are a test assistant."},
                {"role": "user", "content": "Say 'Connection successful' if you can read this."}
            ]
            
            response, model = self.generate_response(test_messages, max_retries=1)
            return "Connection successful" in response
            
        except Exception as e:
            logger.error(f"Connection test failed: {str(e)}")
            return False