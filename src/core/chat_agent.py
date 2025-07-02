import time
import logging
from typing import Optional, Dict, Any
from dataclasses import dataclass

from ..ai.openrouter_client import OpenRouterClient
from ..database.database import RealEstateDatabase
from ..query.router import QueryRouter
from ..config import config

logger = logging.getLogger(__name__)

@dataclass
class QueryResponse:
    """Response from chat agent"""
    content: str
    model_used: str
    engine_used: str
    processing_time: float
    success: bool = True
    error: Optional[str] = None

class ChatAgent:
    """Core chat agent implementation"""
    
    def __init__(self, config_obj: Any = None, test_mode: bool = False):
        self.config = config_obj or config
        self.test_mode = test_mode
        self.router = QueryRouter()
        self.ai_client = OpenRouterClient()
        self.db = RealEstateDatabase()
        
    def process_query(self, query: str) -> QueryResponse:
        """Process a user query and return response"""
        start_time = time.time()
        
        try:
            # Use the router to process the query
            response = self.router.route_query(query)
            
            processing_time = time.time() - start_time
            
            return QueryResponse(
                content=response.content,
                model_used=response.model_used,
                engine_used=response.engine_used,
                processing_time=processing_time,
                success=True
            )
            
        except Exception as e:
            logger.error(f"Error processing query: {str(e)}")
            processing_time = time.time() - start_time
            
            # Fallback to general AI response on error
            try:
                fallback_response = self._get_fallback_response(query, str(e))
                return QueryResponse(
                    content=fallback_response,
                    model_used=self.ai_client.config.default_model,
                    engine_used="error_fallback",
                    processing_time=processing_time,
                    success=False,
                    error=str(e)
                )
            except Exception as fallback_error:
                logger.error(f"Fallback also failed: {str(fallback_error)}")
                return QueryResponse(
                    content="I apologize, but I'm having trouble processing your request. Please try again later.",
                    model_used="none",
                    engine_used="error",
                    processing_time=processing_time,
                    success=False,
                    error=str(fallback_error)
                )
    
    def _get_fallback_response(self, query: str, error: str) -> str:
        """Get fallback response using AI when primary processing fails"""
        messages = [
            {
                "role": "system",
                "content": "You are a helpful real estate market assistant. The primary analysis system encountered an error. Provide a helpful response based on general knowledge."
            },
            {
                "role": "user",
                "content": f"Query: {query}\n\nNote: The system encountered an error: {error}. Please provide a helpful response based on available information."
            }
        ]
        
        response, _ = self.ai_client.generate_response(messages)
        return response