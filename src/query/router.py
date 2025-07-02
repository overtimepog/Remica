import re
import time
import logging
from typing import Dict, Any, Optional, List, Tuple
from enum import Enum
from dataclasses import dataclass
from functools import lru_cache
import hashlib
import json

from ..ai.openrouter_client import OpenRouterClient, ModelResponse
from ..database.database import RealEstateDatabase

logger = logging.getLogger(__name__)

class QueryType(Enum):
    """Types of queries the system can handle"""
    MARKET_YIELD = "market_yield"
    MARKET_TRENDS = "market_trends"
    LOCATION_COMPARISON = "location_comparison"
    INVESTMENT_OPPORTUNITIES = "investment_opportunities"
    MARKET_SUMMARY = "market_summary"
    GENERAL_QUESTION = "general_question"
    UNKNOWN = "unknown"

@dataclass
class ParsedQuery:
    """Parsed query with extracted entities"""
    query_type: QueryType
    locations: List[str]
    property_type: Optional[str]
    bedrooms: Optional[int]
    price_range: Optional[Tuple[float, float]]
    yield_threshold: Optional[float]
    time_period: Optional[int]  # in months
    raw_query: str

class QueryRouter:
    """Optimized router with caching and no double API calls"""
    
    def __init__(self):
        self.ai_client = OpenRouterClient()
        self.db = RealEstateDatabase()
        self._response_cache = {}  # In-memory cache
        self._cache_ttl = 3600  # 1 hour cache TTL
        self._cache_hits = 0
        self._cache_misses = 0
        
        # Optimized patterns with higher specificity
        self.patterns = {
            QueryType.MARKET_YIELD: [
                r"(?:what(?:'s| is) the )?(?:average |gross |rental )?yield",
                r"(?:rental |investment )?return",
                r"roi\b",
                r"cap(?:italization)? rate"
            ],
            QueryType.MARKET_TRENDS: [
                r"(?:market |price |rental )?trends?",
                r"(?:price |rent )(?:movement|history|change)",
                r"how (?:has|have).*(?:market|price|rent)",
                r"historical (?:data|price|rent)"
            ],
            QueryType.LOCATION_COMPARISON: [
                r"compare.*(?:to|with|vs|versus|between|and)",
                r"(?:which|what).*better",
                r"versus|vs\.?",
                r"difference.*between"
            ],
            QueryType.INVESTMENT_OPPORTUNITIES: [
                r"investment opportunit",
                r"best (?:investment|propert|deal)",
                r"(?:find|show|list).*(?:investment|propert)",
                r"properties.*(?:yield|return).*(?:above|over|more than)"
            ],
            QueryType.MARKET_SUMMARY: [
                r"market (?:summary|overview|analysis|report)",
                r"tell me about.*market",
                r"how is.*market",
                r"market condition"
            ]
        }
        
        # Common locations with aliases
        self.location_aliases = {
            "sf": "san francisco",
            "la": "los angeles",
            "nyc": "new york",
            "ny": "new york",
            "chi": "chicago",
            "dc": "washington"
        }
        
        # Compile patterns for performance
        self.compiled_patterns = {}
        for query_type, patterns in self.patterns.items():
            self.compiled_patterns[query_type] = [
                re.compile(pattern, re.IGNORECASE) for pattern in patterns
            ]
    
    def _get_cache_key(self, query: str) -> str:
        """Generate cache key for query"""
        normalized = query.lower().strip()
        return hashlib.md5(normalized.encode()).hexdigest()
    
    def _get_cached_response(self, query: str) -> Optional[ModelResponse]:
        """Get cached response if available and not expired"""
        cache_key = self._get_cache_key(query)
        if cache_key in self._response_cache:
            cached_data = self._response_cache[cache_key]
            if time.time() - cached_data['timestamp'] < self._cache_ttl:
                logger.info(f"Cache hit for query: {query[:50]}...")
                self._cache_hits += 1
                return cached_data['response']
        self._cache_misses += 1
        return None
    
    def _cache_response(self, query: str, response: ModelResponse):
        """Cache response with timestamp"""
        cache_key = self._get_cache_key(query)
        self._response_cache[cache_key] = {
            'response': response,
            'timestamp': time.time()
        }
        
        # Clean old cache entries if cache gets too large
        if len(self._response_cache) > 1000:
            self._clean_cache()
    
    def _clean_cache(self):
        """Remove expired cache entries"""
        current_time = time.time()
        expired_keys = [
            key for key, data in self._response_cache.items()
            if current_time - data['timestamp'] > self._cache_ttl
        ]
        for key in expired_keys:
            del self._response_cache[key]
    
    @lru_cache(maxsize=1000)
    def parse_query(self, query: str) -> ParsedQuery:
        """Parse user query to extract intent and entities (cached)"""
        query_lower = query.lower()
        
        # Determine query type using compiled patterns
        query_type = self._identify_query_type_fast(query_lower)
        
        # Extract entities
        locations = self._extract_locations_fast(query_lower)
        property_type = self._extract_property_type(query_lower)
        bedrooms = self._extract_bedrooms(query_lower)
        price_range = self._extract_price_range(query_lower)
        yield_threshold = self._extract_yield_threshold(query_lower)
        time_period = self._extract_time_period(query_lower)
        
        return ParsedQuery(
            query_type=query_type,
            locations=locations,
            property_type=property_type,
            bedrooms=bedrooms,
            price_range=price_range,
            yield_threshold=yield_threshold,
            time_period=time_period,
            raw_query=query
        )
    
    def route_query(self, query: str) -> ModelResponse:
        """Route query to appropriate handler with caching"""
        # Check cache first
        cached_response = self._get_cached_response(query)
        if cached_response:
            return cached_response
        
        parsed = self.parse_query(query)
        logger.info(f"Routing query of type: {parsed.query_type}")
        
        try:
            # Route to appropriate handler
            if parsed.query_type == QueryType.MARKET_YIELD:
                response = self._handle_market_yield_optimized(parsed)
            elif parsed.query_type == QueryType.MARKET_TRENDS:
                response = self._handle_market_trends_optimized(parsed)
            elif parsed.query_type == QueryType.LOCATION_COMPARISON:
                response = self._handle_location_comparison_optimized(parsed)
            elif parsed.query_type == QueryType.INVESTMENT_OPPORTUNITIES:
                response = self._handle_investment_opportunities_optimized(parsed)
            elif parsed.query_type == QueryType.MARKET_SUMMARY:
                response = self._handle_market_summary_optimized(parsed)
            else:
                response = self._handle_general_question_optimized(parsed)
            
            # Cache the response
            self._cache_response(query, response)
            return response
            
        except Exception as e:
            logger.error(f"Error routing query: {str(e)}")
            return self._handle_error(str(e), parsed)
    
    def _identify_query_type_fast(self, query: str) -> QueryType:
        """Identify query type using compiled patterns (faster)"""
        for query_type, patterns in self.compiled_patterns.items():
            for pattern in patterns:
                if pattern.search(query):
                    return query_type
        return QueryType.GENERAL_QUESTION
    
    def _extract_locations_fast(self, query: str) -> List[str]:
        """Extract locations with alias support"""
        locations = []
        words = query.split()
        
        # Check for aliases first
        for word in words:
            if word in self.location_aliases:
                locations.append(self.location_aliases[word])
        
        # Common locations
        known_locations = [
            "seattle", "portland", "san francisco", "los angeles",
            "new york", "boston", "chicago", "austin", "denver",
            "miami", "atlanta", "dallas", "houston", "phoenix"
        ]
        
        for location in known_locations:
            if location in query and location not in locations:
                locations.append(location)
        
        return locations
    
    def _extract_property_type(self, query: str) -> Optional[str]:
        """Extract property type from query"""
        # Check studio first since it's more specific than apartment
        property_types = {
            "studio": ["studio"],
            "apartment": ["apartment", "apt", "flat"],
            "house": ["house", "home", "single-family", "single family"],
            "condo": ["condo", "condominium"],
            "townhouse": ["townhouse", "townhome"],
            "duplex": ["duplex"],
            "villa": ["villa"],
            "penthouse": ["penthouse"]
        }
        
        for prop_type, keywords in property_types.items():
            for keyword in keywords:
                if keyword in query:
                    return prop_type
        
        # Default based on bedroom count or generic "units"
        if re.search(r"\d+[\s-]?(?:bedroom|br)", query) or \
           re.search(r"(?:one|two|three|four|five)[\s-]?(?:bedroom|br)", query) or \
           "units" in query:
            return "apartment"
        
        return None
    
    def _extract_bedrooms(self, query: str) -> Optional[int]:
        """Extract number of bedrooms"""
        # Numeric patterns
        match = re.search(r"(\d+)[\s-]?(?:bedroom|br|bed)", query)
        if match:
            return int(match.group(1))
        
        # Word patterns
        word_to_num = {
            "studio": 0, "one": 1, "two": 2, "three": 3,
            "four": 4, "five": 5, "six": 6
        }
        
        for word, num in word_to_num.items():
            if word in query and ("bedroom" in query or "br" in query):
                return num
        
        return None
    
    def _extract_price_range(self, query: str) -> Optional[Tuple[float, float]]:
        """Extract price range from query"""
        # Under pattern
        under_match = re.search(r"under\s*\$?([\d,]+)(?:k|m)?", query, re.IGNORECASE)
        if under_match:
            value = float(under_match.group(1).replace(",", ""))
            if "k" in query.lower():
                value *= 1000
            elif "m" in query.lower():
                value *= 1000000
            return (0, value)
        
        # Between pattern
        between_match = re.search(
            r"between\s*\$?([\d,]+)(?:k|m)?\s*(?:and|to)\s*\$?([\d,]+)(?:k|m)?",
            query, re.IGNORECASE
        )
        if between_match:
            min_val = float(between_match.group(1).replace(",", ""))
            max_val = float(between_match.group(2).replace(",", ""))
            
            # Handle k/m suffixes
            if "k" in between_match.group(0).lower():
                min_val *= 1000
                max_val *= 1000
            elif "m" in between_match.group(0).lower():
                min_val *= 1000000
                max_val *= 1000000
                
            return (min_val, max_val)
        
        return None
    
    def _extract_yield_threshold(self, query: str) -> Optional[float]:
        """Extract yield threshold"""
        patterns = [
            r"(?:yield|return|roi).*?(\d+(?:\.\d+)?)\s*%",
            r"(\d+(?:\.\d+)?)\s*%.*(?:yield|return|roi)",
            r"(?:above|over|more than)\s*(\d+(?:\.\d+)?)\s*%"
        ]
        
        for pattern in patterns:
            match = re.search(pattern, query, re.IGNORECASE)
            if match:
                return float(match.group(1))
        
        return None
    
    def _extract_time_period(self, query: str) -> Optional[int]:
        """Extract time period in months"""
        patterns = [
            (r"(?:past|last)\s*(\d+)\s*months?", 1),
            (r"(?:past|last)\s*(\d+)\s*years?", 12),
            (r"(?:past|last)\s*quarter", 3),
            (r"(?:past|last)\s*year", 12)
        ]
        
        for pattern, multiplier in patterns:
            match = re.search(pattern, query, re.IGNORECASE)
            if match:
                # If pattern has groups (contains parentheses for capture)
                if match.groups():
                    return int(match.group(1)) * multiplier
                else:
                    return multiplier
        
        return None
    
    def _handle_market_yield_optimized(self, parsed: ParsedQuery) -> ModelResponse:
        """Handle market yield queries with optimized prompts"""
        if not parsed.locations:
            return self._handle_general_question_optimized(parsed)
        
        location = parsed.locations[0]
        property_type = parsed.property_type or "apartment"
        
        # Get data from database
        data = self.db.get_market_yield(location, property_type, parsed.bedrooms)
        
        if "error" not in data:
            # Optimized prompt for concise response
            messages = [
                {"role": "system", "content": "You are a concise real estate analyst. Provide brief, data-driven insights in 2-3 sentences max."},
                {"role": "user", "content": f"Market data for {property_type}s in {location}: {data}. Give a brief yield analysis."}
            ]
            
            response = self.ai_client.generate_structured_response(messages, "market_yield")
            response.engine_used = "database_query"
            return response
        else:
            return self._handle_general_question_optimized(parsed)
    
    def _handle_market_trends_optimized(self, parsed: ParsedQuery) -> ModelResponse:
        """Handle market trends with optimized prompts"""
        if not parsed.locations:
            return self._handle_general_question_optimized(parsed)
        
        location = parsed.locations[0]
        months = parsed.time_period or 12
        
        # Get trend data
        df = self.db.get_market_trends(location, months)
        
        if not df.empty:
            # Calculate key metrics
            avg_price_change = df['avg_price'].pct_change().mean() * 100
            avg_rent_change = df['avg_rent'].pct_change().mean() * 100
            
            trend_data = {
                "location": location,
                "period": f"{months} months",
                "price_change": f"{avg_price_change:+.1f}%",
                "rent_change": f"{avg_rent_change:+.1f}%",
                "transactions": len(df)
            }
            
            messages = [
                {"role": "system", "content": "You are a concise market analyst. Summarize trends in 2-3 sentences."},
                {"role": "user", "content": f"Market trends: {trend_data}. Brief analysis please."}
            ]
            
            response = self.ai_client.generate_structured_response(messages, "market_trends")
            response.engine_used = "database_query"
            return response
        else:
            return self._handle_general_question_optimized(parsed)
    
    def _handle_location_comparison_optimized(self, parsed: ParsedQuery) -> ModelResponse:
        """Handle location comparison with optimized prompts"""
        if len(parsed.locations) < 2:
            return self._handle_general_question_optimized(parsed)
        
        property_type = parsed.property_type or "apartment"
        comparison_data = self.db.compare_locations(parsed.locations[:2], property_type)
        
        if comparison_data:
            messages = [
                {"role": "system", "content": "You are a concise real estate analyst. Compare markets in 2-3 sentences focusing on key differences."},
                {"role": "user", "content": f"Compare {property_type}s: {comparison_data}. Brief comparison please."}
            ]
            
            response = self.ai_client.generate_structured_response(messages, "location_comparison")
            response.engine_used = "database_query"
            return response
        else:
            return self._handle_general_question_optimized(parsed)
    
    def _handle_investment_opportunities_optimized(self, parsed: ParsedQuery) -> ModelResponse:
        """Handle investment queries with optimized prompts"""
        min_yield = parsed.yield_threshold or 4.0
        max_price = parsed.price_range[1] if parsed.price_range else 1000000
        location = parsed.locations[0] if parsed.locations else None
        
        opportunities = self.db.get_investment_opportunities(min_yield, max_price, location)
        
        if opportunities:
            # Take top 3 opportunities
            top_opportunities = opportunities[:3]
            
            messages = [
                {"role": "system", "content": "You are a concise investment advisor. Recommend top 3 properties in 3-4 sentences total."},
                {"role": "user", "content": f"Top opportunities (yield>{min_yield}%): {top_opportunities}. Brief recommendation."}
            ]
            
            response = self.ai_client.generate_structured_response(messages, "investment_opportunities")
            response.engine_used = "database_query"
            return response
        else:
            return self._handle_general_question_optimized(parsed)
    
    def _handle_market_summary_optimized(self, parsed: ParsedQuery) -> ModelResponse:
        """Handle market summary with optimized prompts"""
        if not parsed.locations:
            return self._handle_general_question_optimized(parsed)
        
        location = parsed.locations[0]
        summary = self.db.get_market_summary(location)
        
        if summary:
            messages = [
                {"role": "system", "content": "You are a concise market analyst. Provide a brief market overview in 3-4 sentences max."},
                {"role": "user", "content": f"{location} market data: {summary}. Brief summary please."}
            ]
            
            response = self.ai_client.generate_structured_response(messages, "market_summary")
            response.engine_used = "database_query"
            return response
        else:
            return self._handle_general_question_optimized(parsed)
    
    def _handle_general_question_optimized(self, parsed: ParsedQuery) -> ModelResponse:
        """Handle general questions with optimized prompts"""
        messages = [
            {"role": "system", "content": "You are a concise real estate expert. Answer in 2-3 sentences max. Be direct and specific."},
            {"role": "user", "content": parsed.raw_query}
        ]
        
        response = self.ai_client.generate_structured_response(messages, "general_question")
        response.engine_used = "ai_generated"
        return response
    
    def _handle_error(self, error_msg: str, parsed: ParsedQuery) -> ModelResponse:
        """Handle errors gracefully"""
        return ModelResponse(
            content=f"I encountered an issue processing your query. Please try rephrasing or ask a different question.",
            model_used="error_handler",
            response_time=0.0,
            cost=0.0,
            engine_used="error_handler"
        )