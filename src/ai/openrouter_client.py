import os
import time
import json
import logging
import threading
from typing import List, Tuple, Optional, Dict, Any
from dataclasses import dataclass
from openai import OpenAI
import httpx
from httpx import AsyncClient, Limits

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
    """Optimized client with connection pooling and better performance"""
    
    def __init__(self):
        self.config = config.openrouter
        
        # Create client with connection pooling
        self.client = OpenAI(
            base_url=self.config.base_url,
            api_key=self.config.api_key,
            http_client=httpx.Client(
                limits=Limits(max_connections=100, max_keepalive_connections=20),
                timeout=httpx.Timeout(30.0, connect=5.0),
                transport=httpx.HTTPTransport(retries=3)
            )
        )
        
        self.usage_count = 0
        self.session_start = time.time()
        self._usage_lock = threading.Lock()  # Thread safety for usage_count
        
        # Pre-compiled headers
        self._headers = {}
        if self.config.http_referer:
            self._headers["HTTP-Referer"] = self.config.http_referer
        if self.config.app_title:
            self._headers["X-Title"] = self.config.app_title
    
    def generate_response(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int = 150,  # Limit response length
        temperature: float = 0.3,  # Lower temperature for consistent responses
        model: Optional[str] = None
    ) -> Tuple[str, str]:
        """
        Generate response with optimized settings
        
        Args:
            messages: List of message dictionaries
            max_tokens: Maximum tokens in response (default: 150 for conciseness)
            temperature: Response creativity (default: 0.3 for consistency)
            model: Model to use (optional, defaults to config)
            
        Returns:
            Tuple of (response_content, model_used)
        """
        model = model or self.config.default_model
        
        try:
            logger.info(f"Using model: {model}")
            start_time = time.time()
            
            # Make API call with optimized parameters
            response = self.client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                extra_headers=self._headers,
                timeout=15.0  # Shorter timeout
            )
            
            response_time = time.time() - start_time
            with self._usage_lock:
                self.usage_count += 1
            
            logger.info(f"Response received in {response_time:.2f}s")
            
            return response.choices[0].message.content, model
            
        except Exception as e:
            logger.error(f"Model {model} failed: {str(e)}")
            
            # Try fallback models
            for fallback_model in self.config.fallback_models[:2]:  # Only try first 2 fallbacks
                try:
                    logger.info(f"Trying fallback model: {fallback_model}")
                    
                    response = self.client.chat.completions.create(
                        model=fallback_model,
                        messages=messages,
                        max_tokens=max_tokens,
                        temperature=temperature,
                        extra_headers=self._headers,
                        timeout=15.0
                    )
                    
                    with self._usage_lock:
                        self.usage_count += 1
                    return response.choices[0].message.content, fallback_model
                    
                except Exception as fallback_error:
                    logger.error(f"Fallback model {fallback_model} failed: {str(fallback_error)}")
                    continue
            
            raise Exception("All models failed to respond")
    
    def generate_structured_response(
        self,
        messages: List[Dict[str, str]],
        query_type: str = "general",
        max_tokens: int = None
    ) -> ModelResponse:
        """
        Generate structured response with optimized settings
        
        Args:
            messages: List of message dictionaries
            query_type: Type of query for metrics
            max_tokens: Override max tokens if needed
            
        Returns:
            ModelResponse object
        """
        # Adjust max tokens based on query type
        if max_tokens is None:
            max_tokens_map = {
                "market_yield": 100,
                "market_trends": 120,
                "location_comparison": 150,
                "investment_opportunities": 150,
                "market_summary": 120,
                "general_question": 100,
                "error_handling": 50
            }
            max_tokens = max_tokens_map.get(query_type, 100)
        
        start_time = time.time()
        
        try:
            content, model_used = self.generate_response(
                messages,
                max_tokens=max_tokens,
                temperature=0.3
            )
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
            logger.error(f"Failed to generate response: {str(e)}")
            # Return error response instead of raising
            return ModelResponse(
                content="I'm having trouble processing your request. Please try again.",
                model_used="error",
                response_time=time.time() - start_time,
                cost=0.0,
                engine_used="error"
            )
    
    def check_rate_limits(self) -> Dict[str, Any]:
        """Check current rate limit status"""
        daily_limit = config.app.enhanced_request_limit if self._has_enhanced_limits() else config.app.daily_request_limit
        
        return {
            "daily_limit": daily_limit,
            "current_usage": self.usage_count,
            "remaining_calls": max(0, daily_limit - self.usage_count),
            "usage_percentage": (self.usage_count / daily_limit) * 100
        }
    
    def _has_enhanced_limits(self) -> bool:
        """Check if account has enhanced limits"""
        return False
    
    def _calculate_cost(self, content: str, model: str) -> float:
        """Calculate cost for paid models"""
        word_count = len(content.split())
        token_count = word_count * 1.33
        cost_per_1k_tokens = 0.001
        return (token_count / 1000) * cost_per_1k_tokens
    
    def get_available_models(self) -> List[str]:
        """Get list of available models"""
        return [self.config.default_model] + self.config.fallback_models
    
    def test_connection(self) -> bool:
        """Test connection to OpenRouter API"""
        try:
            test_messages = [
                {"role": "system", "content": "Reply with 'OK' only."},
                {"role": "user", "content": "Test"}
            ]
            
            response, _ = self.generate_response(test_messages, max_tokens=10)
            return "OK" in response.upper()
            
        except Exception as e:
            logger.error(f"Connection test failed: {str(e)}")
            return False
    
    def close(self):
        """Close the HTTP client connections"""
        if hasattr(self.client._client, 'close'):
            self.client._client.close()