import re
import logging
from typing import Dict, Any, Optional, List, Tuple
from enum import Enum
from dataclasses import dataclass

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
    """Routes queries to appropriate handlers"""
    
    def __init__(self):
        self.ai_client = OpenRouterClient()
        self.db = RealEstateDatabase()
        
        # Define query patterns
        self.patterns = {
            QueryType.MARKET_YIELD: [
                r"(?:what(?:'s| is) the )?(?:average )?yield.*(?:for|in|of)",
                r"rental yield",
                r"return on investment",
                r"roi.*(?:for|in|of)"
            ],
            QueryType.MARKET_TRENDS: [
                r"market trend",
                r"price (?:trend|movement|history)",
                r"how (?:has|have).*(?:changed|moved|evolved)",
                r"historical (?:data|prices|rents)"
            ],
            QueryType.LOCATION_COMPARISON: [
                r"compare.*(?:between|among)",
                r"(?:which|what).*better.*(?:between|among)",
                r"versus|vs\.?",
                r"difference.*between"
            ],
            QueryType.INVESTMENT_OPPORTUNITIES: [
                r"investment opportunit",
                r"best (?:investments?|properties|deals)",
                r"properties? (?:with|yielding|above)",
                r"find.*(?:investment|properties)"
            ],
            QueryType.MARKET_SUMMARY: [
                r"market (?:summary|overview|analysis)",
                r"tell me about.*market",
                r"how is the.*market",
                r"market condition"
            ]
        }
        
        # Common property types
        self.property_types = [
            "apartment", "house", "condo", "townhouse", 
            "studio", "duplex", "villa", "penthouse"
        ]
        
        # Common locations (would be loaded from database in production)
        self.known_locations = [
            "seattle", "portland", "san francisco", "los angeles",
            "new york", "boston", "chicago", "austin", "denver",
            "downtown", "suburbs", "waterfront", "city center"
        ]
    
    def parse_query(self, query: str) -> ParsedQuery:
        """Parse user query to extract intent and entities"""
        query_lower = query.lower()
        
        # Determine query type
        query_type = self._identify_query_type(query_lower)
        
        # Extract entities
        locations = self._extract_locations(query_lower)
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
        """Route query to appropriate handler"""
        parsed = self.parse_query(query)
        
        logger.info(f"Routing query of type: {parsed.query_type}")
        
        try:
            if parsed.query_type == QueryType.MARKET_YIELD:
                return self._handle_market_yield(parsed)
            elif parsed.query_type == QueryType.MARKET_TRENDS:
                return self._handle_market_trends(parsed)
            elif parsed.query_type == QueryType.LOCATION_COMPARISON:
                return self._handle_location_comparison(parsed)
            elif parsed.query_type == QueryType.INVESTMENT_OPPORTUNITIES:
                return self._handle_investment_opportunities(parsed)
            elif parsed.query_type == QueryType.MARKET_SUMMARY:
                return self._handle_market_summary(parsed)
            else:
                return self._handle_general_question(parsed)
                
        except Exception as e:
            logger.error(f"Error routing query: {str(e)}")
            return self._handle_error(str(e), parsed)
    
    def _identify_query_type(self, query: str) -> QueryType:
        """Identify the type of query"""
        for query_type, patterns in self.patterns.items():
            for pattern in patterns:
                if re.search(pattern, query, re.IGNORECASE):
                    return query_type
        return QueryType.GENERAL_QUESTION
    
    def _extract_locations(self, query: str) -> List[str]:
        """Extract location mentions from query"""
        locations = []
        for location in self.known_locations:
            if location in query:
                locations.append(location)
        return locations
    
    def _extract_property_type(self, query: str) -> Optional[str]:
        """Extract property type from query"""
        for prop_type in self.property_types:
            if prop_type in query:
                return prop_type
        
        # Check for bedroom-based descriptions
        if "1-bedroom" in query or "one bedroom" in query:
            return "apartment"
        elif "2-bedroom" in query or "two bedroom" in query:
            return "apartment"
        
        return None
    
    def _extract_bedrooms(self, query: str) -> Optional[int]:
        """Extract number of bedrooms from query"""
        patterns = [
            (r"(\d+)[\s-]?bedroom", 1),
            (r"(\d+)[\s-]?br", 1),
            (r"(one|two|three|four|five)[\s-]?bedroom", None)
        ]
        
        for pattern, group in patterns:
            match = re.search(pattern, query, re.IGNORECASE)
            if match:
                if group:
                    return int(match.group(group))
                else:
                    # Convert word to number
                    word = match.group(1).lower()
                    word_to_num = {
                        "one": 1, "two": 2, "three": 3, 
                        "four": 4, "five": 5
                    }
                    return word_to_num.get(word)
        
        return None
    
    def _extract_price_range(self, query: str) -> Optional[Tuple[float, float]]:
        """Extract price range from query"""
        # Pattern for "under $X"
        under_match = re.search(r"under\s*\$?([\d,]+)(?:k|K)?", query)
        if under_match:
            value = float(under_match.group(1).replace(",", ""))
            if "k" in query.lower():
                value *= 1000
            return (0, value)
        
        # Pattern for "between $X and $Y"
        between_match = re.search(
            r"between\s*\$?([\d,]+)(?:k|K)?\s*and\s*\$?([\d,]+)(?:k|K)?", 
            query, 
            re.IGNORECASE
        )
        if between_match:
            min_val = float(between_match.group(1).replace(",", ""))
            max_val = float(between_match.group(2).replace(",", ""))
            if "k" in query.lower():
                min_val *= 1000
                max_val *= 1000
            return (min_val, max_val)
        
        return None
    
    def _extract_yield_threshold(self, query: str) -> Optional[float]:
        """Extract yield threshold from query"""
        patterns = [
            r"(?:yield|return|roi).*?(\d+(?:\.\d+)?)\s*%",
            r"(\d+(?:\.\d+)?)\s*%.*(?:yield|return|roi)",
            r"above\s*(\d+(?:\.\d+)?)\s*%"
        ]
        
        for pattern in patterns:
            match = re.search(pattern, query, re.IGNORECASE)
            if match:
                return float(match.group(1))
        
        return None
    
    def _extract_time_period(self, query: str) -> Optional[int]:
        """Extract time period in months from query"""
        patterns = [
            (r"past\s*(\d+)\s*month", 1),
            (r"last\s*(\d+)\s*month", 1),
            (r"past\s*(\d+)\s*year", 12),
            (r"last\s*(\d+)\s*year", 12),
            (r"(\d+)\s*month", 1),
            (r"(\d+)\s*year", 12)
        ]
        
        for pattern, multiplier in patterns:
            match = re.search(pattern, query, re.IGNORECASE)
            if match:
                return int(match.group(1)) * multiplier
        
        return None
    
    def _handle_market_yield(self, parsed: ParsedQuery) -> ModelResponse:
        """Handle market yield queries"""
        if not parsed.locations:
            return self._handle_general_question(parsed)
        
        location = parsed.locations[0]
        property_type = parsed.property_type or "apartment"
        
        # Get data from database
        data = self.db.get_market_yield(location, property_type, parsed.bedrooms)
        
        # Format response
        if "error" not in data:
            messages = [
                {"role": "system", "content": "You are a real estate market analyst. Provide concise, data-driven insights."},
                {"role": "user", "content": f"Based on this market data: {data}, provide a brief analysis of the rental yield for {property_type}s in {location}."}
            ]
            
            response = self.ai_client.generate_structured_response(messages, "market_yield")
            response.engine_used = "database_query"
            return response
        else:
            return self._handle_general_question(parsed)
    
    def _handle_market_trends(self, parsed: ParsedQuery) -> ModelResponse:
        """Handle market trends queries"""
        if not parsed.locations:
            return self._handle_general_question(parsed)
        
        location = parsed.locations[0]
        months = parsed.time_period or 12
        
        # Get trend data
        df = self.db.get_market_trends(location, months)
        
        if not df.empty:
            # Prepare trend summary
            trend_summary = df.groupby('property_type').agg({
                'avg_price': ['mean', 'std'],
                'avg_rent': ['mean', 'std'],
                'transaction_count': 'sum'
            }).to_dict()
            
            messages = [
                {"role": "system", "content": "You are a real estate market analyst. Analyze market trends and provide insights."},
                {"role": "user", "content": f"Analyze these market trends for {location} over the past {months} months: {trend_summary}"}
            ]
            
            response = self.ai_client.generate_structured_response(messages, "market_trends")
            response.engine_used = "database_query"
            return response
        else:
            return self._handle_general_question(parsed)
    
    def _handle_location_comparison(self, parsed: ParsedQuery) -> ModelResponse:
        """Handle location comparison queries"""
        if len(parsed.locations) < 2:
            return self._handle_general_question(parsed)
        
        property_type = parsed.property_type or "apartment"
        comparison_data = self.db.compare_locations(parsed.locations, property_type)
        
        if comparison_data:
            messages = [
                {"role": "system", "content": "You are a real estate market analyst. Compare markets objectively using data."},
                {"role": "user", "content": f"Compare the real estate markets for {property_type}s across these locations: {comparison_data}"}
            ]
            
            response = self.ai_client.generate_structured_response(messages, "location_comparison")
            response.engine_used = "database_query"
            return response
        else:
            return self._handle_general_question(parsed)
    
    def _handle_investment_opportunities(self, parsed: ParsedQuery) -> ModelResponse:
        """Handle investment opportunity queries"""
        min_yield = parsed.yield_threshold or 4.0
        max_price = parsed.price_range[1] if parsed.price_range else 1000000
        location = parsed.locations[0] if parsed.locations else None
        
        opportunities = self.db.get_investment_opportunities(min_yield, max_price, location)
        
        if opportunities:
            messages = [
                {"role": "system", "content": "You are a real estate investment advisor. Highlight the best opportunities based on yield and value."},
                {"role": "user", "content": f"Analyze these investment opportunities and recommend the top options: {opportunities[:5]}"}
            ]
            
            response = self.ai_client.generate_structured_response(messages, "investment_opportunities")
            response.engine_used = "database_query"
            return response
        else:
            return self._handle_general_question(parsed)
    
    def _handle_market_summary(self, parsed: ParsedQuery) -> ModelResponse:
        """Handle market summary queries"""
        if not parsed.locations:
            return self._handle_general_question(parsed)
        
        location = parsed.locations[0]
        summary = self.db.get_market_summary(location)
        
        if summary:
            messages = [
                {"role": "system", "content": "You are a real estate market analyst. Provide a comprehensive yet concise market overview."},
                {"role": "user", "content": f"Provide a market summary for {location} based on this data: {summary}"}
            ]
            
            response = self.ai_client.generate_structured_response(messages, "market_summary")
            response.engine_used = "database_query"
            return response
        else:
            return self._handle_general_question(parsed)
    
    def _handle_general_question(self, parsed: ParsedQuery) -> ModelResponse:
        """Handle general questions using AI"""
        messages = [
            {"role": "system", "content": "You are a knowledgeable real estate market analyst. Provide helpful insights about real estate markets, investment strategies, and property analysis."},
            {"role": "user", "content": parsed.raw_query}
        ]
        
        response = self.ai_client.generate_structured_response(messages, "general_question")
        response.engine_used = "ai_generated"
        return response
    
    def _handle_error(self, error_msg: str, parsed: ParsedQuery) -> ModelResponse:
        """Handle errors gracefully"""
        messages = [
            {"role": "system", "content": "You are a helpful real estate assistant. Acknowledge the error and provide alternative suggestions."},
            {"role": "user", "content": f"There was an error processing the query: '{parsed.raw_query}'. Error: {error_msg}. Please provide helpful alternatives or suggestions."}
        ]
        
        response = self.ai_client.generate_structured_response(messages, "error_handling")
        response.engine_used = "error_handler"
        return response