import logging
import psycopg2
from psycopg2.extras import RealDictCursor
from typing import List, Dict, Any, Optional, Tuple
from contextlib import contextmanager
from datetime import datetime, timedelta
import pandas as pd

try:
    from ..config import config
except ImportError:
    from config import config

logger = logging.getLogger(__name__)

class RealEstateDatabase:
    """Database interface for real estate queries"""
    
    def __init__(self):
        self.config = config.database
        self._connection = None
        
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
    
    def get_market_yield(
        self, 
        location: str, 
        property_type: str,
        bedrooms: Optional[int] = None
    ) -> Dict[str, Any]:
        """Get market yield for specific property type and location"""
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
                        return {
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
                        return {"error": "No data found for specified criteria"}
                        
        except Exception as e:
            logger.error(f"Error getting market yield: {str(e)}")
            return {"error": str(e)}
    
    def get_market_trends(
        self,
        location: str,
        months: int = 12
    ) -> pd.DataFrame:
        """Get market trends for a location over specified months"""
        try:
            with self.get_connection() as conn:
                query = """
                SELECT 
                    DATE_TRUNC('month', date) as month,
                    property_type,
                    AVG(price) as avg_price,
                    AVG(monthly_rent) as avg_rent,
                    COUNT(*) as transaction_count
                FROM properties
                WHERE location = %s
                AND date >= CURRENT_DATE - INTERVAL '%s months'
                GROUP BY month, property_type
                ORDER BY month, property_type
                """
                
                df = pd.read_sql_query(
                    query, 
                    conn, 
                    params=[location, months]
                )
                
                return df
                
        except Exception as e:
            logger.error(f"Error getting market trends: {str(e)}")
            return pd.DataFrame()
    
    def compare_locations(
        self,
        locations: List[str],
        property_type: str
    ) -> Dict[str, Any]:
        """Compare market metrics across multiple locations"""
        try:
            results = {}
            
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    for location in locations:
                        query = """
                        SELECT 
                            location,
                            AVG(price) as avg_price,
                            AVG(monthly_rent) as avg_rent,
                            AVG((monthly_rent * 12) / price * 100) as gross_yield,
                            STDDEV(price) as price_volatility,
                            COUNT(*) as market_size
                        FROM properties
                        WHERE location = %s 
                        AND property_type = %s
                        AND last_updated >= CURRENT_DATE - INTERVAL '30 days'
                        GROUP BY location
                        """
                        
                        cursor.execute(query, [location, property_type])
                        result = cursor.fetchone()
                        
                        if result:
                            results[location] = {
                                "avg_price": float(result['avg_price']),
                                "avg_rent": float(result['avg_rent']),
                                "gross_yield": float(result['gross_yield']),
                                "price_volatility": float(result['price_volatility']),
                                "market_size": result['market_size']
                            }
            
            return results
            
        except Exception as e:
            logger.error(f"Error comparing locations: {str(e)}")
            return {}
    
    def get_investment_opportunities(
        self,
        min_yield: float,
        max_price: float,
        location: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Find investment opportunities based on criteria"""
        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    query = """
                    SELECT 
                        property_id,
                        location,
                        property_type,
                        bedrooms,
                        price,
                        monthly_rent,
                        (monthly_rent * 12) / price * 100 as gross_yield,
                        last_updated
                    FROM properties
                    WHERE (monthly_rent * 12) / price * 100 >= %s
                    AND price <= %s
                    """
                    params = [min_yield, max_price]
                    
                    if location:
                        query += " AND location = %s"
                        params.append(location)
                    
                    query += " ORDER BY gross_yield DESC LIMIT 20"
                    
                    cursor.execute(query, params)
                    results = cursor.fetchall()
                    
                    return [dict(row) for row in results]
                    
        except Exception as e:
            logger.error(f"Error finding investment opportunities: {str(e)}")
            return []
    
    def get_market_summary(self, location: str) -> Dict[str, Any]:
        """Get comprehensive market summary for a location"""
        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    # Overall market metrics
                    query = """
                    SELECT 
                        COUNT(DISTINCT property_id) as total_properties,
                        AVG(price) as avg_price,
                        MIN(price) as min_price,
                        MAX(price) as max_price,
                        AVG(monthly_rent) as avg_rent,
                        AVG((monthly_rent * 12) / price * 100) as avg_yield
                    FROM properties
                    WHERE location = %s
                    AND last_updated >= CURRENT_DATE - INTERVAL '30 days'
                    """
                    
                    cursor.execute(query, [location])
                    overall = cursor.fetchone()
                    
                    # Breakdown by property type
                    query = """
                    SELECT 
                        property_type,
                        COUNT(*) as count,
                        AVG(price) as avg_price,
                        AVG((monthly_rent * 12) / price * 100) as avg_yield
                    FROM properties
                    WHERE location = %s
                    AND last_updated >= CURRENT_DATE - INTERVAL '30 days'
                    GROUP BY property_type
                    """
                    
                    cursor.execute(query, [location])
                    by_type = cursor.fetchall()
                    
                    return {
                        "location": location,
                        "overall": dict(overall),
                        "by_property_type": [dict(row) for row in by_type]
                    }
                    
        except Exception as e:
            logger.error(f"Error getting market summary: {str(e)}")
            return {}
    
    def create_tables(self):
        """Create necessary database tables if they don't exist"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                    CREATE TABLE IF NOT EXISTS properties (
                        property_id SERIAL PRIMARY KEY,
                        location VARCHAR(255) NOT NULL,
                        property_type VARCHAR(100) NOT NULL,
                        bedrooms INTEGER,
                        bathrooms INTEGER,
                        sqft INTEGER,
                        price DECIMAL(12, 2) NOT NULL,
                        monthly_rent DECIMAL(10, 2),
                        year_built INTEGER,
                        last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        date DATE DEFAULT CURRENT_DATE,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                    
                    CREATE INDEX IF NOT EXISTS idx_location ON properties(location);
                    CREATE INDEX IF NOT EXISTS idx_property_type ON properties(property_type);
                    CREATE INDEX IF NOT EXISTS idx_yield ON properties((monthly_rent * 12) / price);
                    """)
                    
                    conn.commit()
                    logger.info("Database tables created successfully")
                    
        except Exception as e:
            logger.error(f"Error creating tables: {str(e)}")
            raise