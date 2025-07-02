import os
from typing import List, Optional
from dataclasses import dataclass, field
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

@dataclass
class OpenRouterConfig:
    """OpenRouter API configuration"""
    api_key: str
    base_url: str = "https://openrouter.ai/api/v1"
    default_model: str = "meta-llama/llama-3.1-8b-instruct:free"
    fallback_models: List[str] = None
    http_referer: Optional[str] = None
    app_title: str = "Real Estate Market Insights Chat Agent"
    
    def __post_init__(self):
        if self.fallback_models is None:
            self.fallback_models = [
                "deepseek/deepseek-r1:free",
                "qwen/qwen-plus:free",  
                "microsoft/phi-3-medium-128k-instruct:free"
            ]

@dataclass
class DatabaseConfig:
    """Database configuration"""
    host: str
    port: int
    name: str
    user: str
    password: str
    
    @property
    def connection_string(self) -> str:
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.name}"

@dataclass
class AppConfig:
    """Application configuration"""
    env: str = "development"
    debug: bool = True
    log_level: str = "INFO"
    response_timeout: int = 30
    max_retries: int = 3
    cache_ttl: int = 900
    daily_request_limit: int = 50
    enhanced_request_limit: int = 1000

class Config:
    """Main configuration class"""
    
    def __init__(self):
        self.openrouter = OpenRouterConfig(
            api_key=os.getenv("OPENROUTER_API_KEY", ""),
            default_model=os.getenv("DEFAULT_FREE_MODEL", "meta-llama/llama-3.1-8b-instruct:free"),
            http_referer=os.getenv("HTTP_REFERER"),
            app_title=os.getenv("APP_TITLE", "Real Estate Market Insights Chat Agent")
        )
        
        # Parse fallback models from env
        fallback_models_str = os.getenv("FALLBACK_MODELS", "")
        if fallback_models_str:
            self.openrouter.fallback_models = [m.strip() for m in fallback_models_str.split(",")]
        
        self.database = DatabaseConfig(
            host=os.getenv("DATABASE_HOST", "localhost"),
            port=int(os.getenv("DATABASE_PORT", "5432")),
            name=os.getenv("DATABASE_NAME", "real_estate_db"),
            user=os.getenv("DATABASE_USER", "postgres"),
            password=os.getenv("DATABASE_PASSWORD", os.getenv("DATABASE_PASS", "postgres"))
        )
        
        self.app = AppConfig(
            env=os.getenv("APP_ENV", "development"),
            debug=os.getenv("DEBUG", "true").lower() == "true",
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            response_timeout=int(os.getenv("RESPONSE_TIMEOUT", "30")),
            max_retries=int(os.getenv("MAX_RETRIES", "3")),
            cache_ttl=int(os.getenv("CACHE_TTL", "900")),
            daily_request_limit=int(os.getenv("DAILY_REQUEST_LIMIT", "50")),
            enhanced_request_limit=int(os.getenv("ENHANCED_REQUEST_LIMIT", "1000"))
        )
    
    def validate(self) -> bool:
        """Validate configuration"""
        if not self.openrouter.api_key:
            raise ValueError("OPENROUTER_API_KEY is required")
        
        if not all([self.database.host, self.database.name, self.database.user]):
            raise ValueError("Database configuration is incomplete")
        
        return True

# Global config instance
config = Config()