"""
Optimized database wrapper with caching for improved performance
"""

import time
import hashlib
import json
import logging
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
import psycopg2
from psycopg2.extras import RealDictCursor
from typing import List, Dict, Any, Optional, Tuple
from contextlib import contextmanager
from datetime import datetime, timedelta
from functools import lru_cache
import pandas as pd

try:
    from ..config import config
except ImportError:
    from config import config

logger = logging.getLogger(__name__)

class RealEstateDatabase:
    """Database interface with caching for improved performance"""
    
    def __init__(self):
        self.config = config.database
        self._connection = None
        self._cache = {}
        self._cache_ttl = 3600  # 1 hour TTL
        self._cache_lock = threading.Lock()  # Thread safety for cache operations
        
    @contextmanager
    def get_connection(self):
        """Get database connection with context manager"""
        conn = None
        try:
            conn = psycopg2.connect(
                host=self.config.host,
                port=self.config.port,
                database=self.config.name,
                user=self.config.user,
                password=self.config.password
            )
            yield conn
        except psycopg2.Error as e:
            logger.error(f"Database connection error: {str(e)}")
            raise
        finally:
            if conn:
                conn.close()
    
    def _get_cache_key(self, method_name: str, *args, **kwargs) -> str:
        """Generate cache key for method call"""
        key_data = {
            'method': method_name,
            'args': args,
            'kwargs': kwargs
        }
        key_str = json.dumps(key_data, sort_keys=True)
        return hashlib.md5(key_str.encode()).hexdigest()
    
    def _get_cached_result(self, cache_key: str) -> Optional[Any]:
        """Get cached result if available and not expired"""
        with self._cache_lock:
            if cache_key in self._cache:
                cached_data = self._cache[cache_key]
                if time.time() - cached_data['timestamp'] < self._cache_ttl:
                    return cached_data['result']
                else:
                    # Remove expired entry
                    del self._cache[cache_key]
        return None
    
    def _cache_result(self, cache_key: str, result: Any):
        """Cache result with timestamp"""
        with self._cache_lock:
            self._cache[cache_key] = {
                'result': result,
                'timestamp': time.time()
            }
            
            # Clean cache if it gets too large
            if len(self._cache) > 500:
                self._clean_cache()
    
    def _clean_cache(self):
        """Remove expired cache entries"""
        current_time = time.time()
        expired_keys = [
            key for key, data in self._cache.items()
            if current_time - data['timestamp'] > self._cache_ttl
        ]
        for key in expired_keys:
            del self._cache[key]
    
    def test_connection(self) -> bool:
        """Test database connectivity"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT 1")
                    return cursor.fetchone()[0] == 1
        except Exception as e:
            logger.error(f"Database connection test failed: {str(e)}")
            return False
    
    @lru_cache(maxsize=100)
    def get_market_yield(
        self, 
        location: str, 
        property_type: str = "apartment",
        bedrooms: Optional[int] = None
    ) -> Dict[str, Any]:
        """Get market yield data with caching"""
        cache_key = self._get_cache_key('get_market_yield', location, property_type, bedrooms)
        
        # Check cache
        cached_result = self._get_cached_result(cache_key)
        if cached_result is not None:
            return cached_result
        
        # Get from database or generate mock data
        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    # Set search path for this connection
                    cursor.execute("SET search_path TO real_estate, public")
                    
                    query = """
                    SELECT 
                        AVG(p.price) as avg_price,
                        AVG(r.monthly_rent) as avg_rent,
                        AVG((r.monthly_rent * 12) / p.price * 100) as gross_yield,
                        COUNT(*) as sample_size,
                        MAX(p.updated_at) as data_currency
                    FROM properties p
                    LEFT JOIN rentals r ON p.id = r.property_id
                    WHERE p.city = %s 
                    AND p.property_type = %s
                    AND r.monthly_rent IS NOT NULL
                    """
                    params = [location, property_type]
                    
                    if bedrooms:
                        query += " AND p.bedrooms = %s"
                        params.append(bedrooms)
                    
                    cursor.execute(query, params)
                    result = cursor.fetchone()
                    
                    if result and result['sample_size'] > 0:
                        data = {
                            "location": location,
                            "property_type": property_type,
                            "bedrooms": bedrooms,
                            "avg_price": float(result['avg_price']),
                            "avg_monthly_rent": float(result['avg_rent']),
                            "gross_annual_yield": float(result['gross_yield']),
                            "sample_size": result['sample_size'],
                            "data_currency": result['data_currency']
                        }
                    else:
                        # Generate mock data for demo
                        data = self._generate_mock_yield_data(location, property_type, bedrooms)
        except Exception as e:
            logger.warning(f"Database query failed, using mock data: {str(e)}")
            # Generate mock data as fallback
            data = self._generate_mock_yield_data(location, property_type, bedrooms)
        
        # Cache result
        self._cache_result(cache_key, data)
        return data
    
    def _generate_mock_yield_data(self, location: str, property_type: str, bedrooms: Optional[int]) -> Dict[str, Any]:
        """Generate realistic mock data for demonstration"""
        import random
        
        # Base prices by location
        location_multipliers = {
            "seattle": 1.2, "san francisco": 1.8, "portland": 1.0,
            "los angeles": 1.5, "new york": 2.0, "boston": 1.4,
            "chicago": 0.9, "austin": 1.1, "denver": 1.0,
            "miami": 1.3, "atlanta": 0.8, "dallas": 0.9
        }
        
        # Property type multipliers
        property_multipliers = {
            "apartment": 1.0, "house": 1.4, "condo": 1.1,
            "townhouse": 1.2, "studio": 0.7
        }
        
        # Bedroom multipliers
        bedroom_multipliers = {
            None: 1.0, 0: 0.6, 1: 0.8, 2: 1.0, 3: 1.3, 4: 1.6
        }
        
        base_price = 300000
        location_mult = location_multipliers.get(location.lower(), 1.0)
        property_mult = property_multipliers.get(property_type.lower(), 1.0)
        bedroom_mult = bedroom_multipliers.get(bedrooms, 1.0)
        
        avg_price = base_price * location_mult * property_mult * bedroom_mult
        # Add some randomness
        avg_price *= random.uniform(0.9, 1.1)
        
        # Calculate rent (typical 0.5-0.8% of price per month)
        monthly_rent = avg_price * random.uniform(0.005, 0.008)
        
        # Calculate yield
        gross_yield = (monthly_rent * 12) / avg_price * 100
        
        return {
            "location": location,
            "property_type": property_type,
            "bedrooms": bedrooms,
            "avg_price": round(avg_price, 2),
            "avg_monthly_rent": round(monthly_rent, 2),
            "gross_annual_yield": round(gross_yield, 2),
            "sample_size": random.randint(15, 50),
            "data_currency": datetime.now().isoformat()
        }
    
    def get_market_trends(
        self, 
        location: str, 
        months: int = 12
    ) -> pd.DataFrame:
        """Get market trends with caching"""
        cache_key = self._get_cache_key('get_market_trends', location, months)
        
        # Check cache
        cached_result = self._get_cached_result(cache_key)
        if cached_result is not None:
            # Convert dict back to DataFrame if needed
            if isinstance(cached_result, dict) and 'data' in cached_result:
                return pd.DataFrame(cached_result['data'])
            return cached_result
        
        try:
            with self.get_connection() as conn:
                query = """
                SELECT 
                    DATE_TRUNC('month', date) as month,
                    property_type,
                    AVG(price) as avg_price,
                    AVG(monthly_rent) as avg_rent,
                    COUNT(*) as transaction_count
                FROM properties p
                LEFT JOIN rentals r ON p.id = r.property_id
                WHERE p.city = %s
                AND date >= %s
                GROUP BY month, property_type
                ORDER BY month DESC
                """
                
                start_date = datetime.now() - timedelta(days=months * 30)
                df = pd.read_sql_query(query, conn, params=[location, start_date])
                
                if df.empty:
                    # Generate mock trend data
                    df = self._generate_mock_trend_data(location, months)
        except Exception as e:
            logger.warning(f"Database query failed, using mock data: {str(e)}")
            df = self._generate_mock_trend_data(location, months)
        
        # Cache result (convert DataFrame to dict for JSON serialization)
        if isinstance(df, pd.DataFrame):
            cache_data = {'data': df.to_dict('records')}
            self._cache_result(cache_key, cache_data)
        else:
            self._cache_result(cache_key, df)
        
        return df
    
    def _generate_mock_trend_data(self, location: str, months: int) -> pd.DataFrame:
        """Generate mock trend data"""
        import random
        
        data = []
        base_price = 300000
        base_rent = 2000
        
        for i in range(months):
            month = datetime.now() - timedelta(days=i * 30)
            # Add trend and noise
            trend_factor = 1 + (i * 0.02)  # 2% growth per month
            noise = random.uniform(0.95, 1.05)
            
            data.append({
                'month': month,
                'property_type': 'apartment',
                'avg_price': base_price * trend_factor * noise,
                'avg_rent': base_rent * trend_factor * noise,
                'transaction_count': random.randint(10, 30)
            })
        
        return pd.DataFrame(data)
    
    def compare_locations(
        self, 
        locations: List[str], 
        property_type: str = "apartment"
    ) -> List[Dict[str, Any]]:
        """Compare locations with caching and parallel processing"""
        cache_key = self._get_cache_key('compare_locations', tuple(locations), property_type)
        
        # Check cache
        cached_result = self._get_cached_result(cache_key)
        if cached_result is not None:
            return cached_result
        
        # Get data for each location in parallel
        comparison_data = []
        
        def fetch_location_data(location: str) -> Optional[Dict[str, Any]]:
            """Fetch data for a single location"""
            try:
                yield_data = self.get_market_yield(location, property_type)
                if "error" not in yield_data:
                    return yield_data
            except Exception as e:
                logger.error(f"Error fetching data for {location}: {str(e)}")
            return None
        
        # Use ThreadPoolExecutor for parallel fetching
        with ThreadPoolExecutor(max_workers=min(len(locations), 5)) as executor:
            # Submit all locations
            future_to_location = {
                executor.submit(fetch_location_data, location): location 
                for location in locations
            }
            
            # Collect results as they complete
            for future in as_completed(future_to_location):
                try:
                    result = future.result()
                    if result:
                        comparison_data.append(result)
                except Exception as e:
                    location = future_to_location[future]
                    logger.error(f"Failed to get data for {location}: {str(e)}")
        
        # Sort by location name to maintain consistent order
        comparison_data.sort(key=lambda x: x.get('location', ''))
        
        # Cache result
        self._cache_result(cache_key, comparison_data)
        
        return comparison_data
    
    def get_investment_opportunities(
        self,
        min_yield: float = 4.0,
        max_price: Optional[float] = None,
        location: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get investment opportunities with caching"""
        cache_key = self._get_cache_key('get_investment_opportunities', min_yield, max_price, location)
        
        # Check cache
        cached_result = self._get_cached_result(cache_key)
        if cached_result is not None:
            return cached_result
        
        # Generate mock opportunities
        opportunities = self._generate_mock_opportunities(min_yield, max_price, location)
        
        # Cache result
        self._cache_result(cache_key, opportunities)
        
        return opportunities
    
    def _generate_mock_opportunities(self, min_yield: float, max_price: Optional[float], location: Optional[str]) -> List[Dict[str, Any]]:
        """Generate mock investment opportunities"""
        import random
        
        locations = ["Seattle", "Portland", "Austin", "Denver", "Atlanta"]
        if location:
            locations = [location]
        
        opportunities = []
        for i, loc in enumerate(locations[:5]):
            price = random.randint(200000, max_price or 800000)
            monthly_rent = price * random.uniform(0.006, 0.012)
            yield_val = (monthly_rent * 12) / price * 100
            
            if yield_val >= min_yield:
                opportunities.append({
                    "id": f"prop_{i+1}",
                    "location": loc,
                    "property_type": random.choice(["apartment", "house", "condo"]),
                    "price": price,
                    "monthly_rent": round(monthly_rent, 2),
                    "gross_yield": round(yield_val, 2),
                    "bedrooms": random.randint(1, 4)
                })
        
        return sorted(opportunities, key=lambda x: x['gross_yield'], reverse=True)
    
    def get_market_summary(self, location: str) -> Dict[str, Any]:
        """Get market summary with caching and parallel data fetching"""
        cache_key = self._get_cache_key('get_market_summary', location)
        
        # Check cache
        cached_result = self._get_cached_result(cache_key)
        if cached_result is not None:
            return cached_result
        
        # Fetch yield data and trends in parallel
        with ThreadPoolExecutor(max_workers=2) as executor:
            # Submit both tasks
            yield_future = executor.submit(self.get_market_yield, location, "apartment")
            trends_future = executor.submit(self.get_market_trends, location, 6)
            
            # Get results
            yield_data = yield_future.result()
            trends = trends_future.result()
        
        summary = {
            "location": location,
            "avg_yield": yield_data.get("gross_annual_yield", 0),
            "avg_price": yield_data.get("avg_price", 0),
            "avg_rent": yield_data.get("avg_monthly_rent", 0),
            "market_trend": "stable",
            "total_listings": yield_data.get("sample_size", 0),
            "last_updated": yield_data.get("data_currency", datetime.now().isoformat())
        }
        
        # Cache result
        self._cache_result(cache_key, summary)
        
        return summary
    
    def clear_cache(self):
        """Clear all cached data"""
        with self._cache_lock:
            self._cache.clear()
        self.get_market_yield.cache_clear()
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        with self._cache_lock:
            return {
                'entries': len(self._cache),
                'memory_usage': sum(len(str(v)) for v in self._cache.values()),
                'hit_rate': getattr(self, '_cache_hits', 0) / max(1, getattr(self, '_cache_hits', 0) + getattr(self, '_cache_misses', 0)) * 100
            }