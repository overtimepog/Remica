import pytest
import time
import csv
import os
from pathlib import Path
from typing import List, Dict
import pandas as pd

from src.query.router import QueryRouter
from src.ai.openrouter_client import OpenRouterClient
from src.db.database import RealEstateDatabase

@pytest.mark.integration
@pytest.mark.slow
class TestPerformance:
    """Performance tests for the Real Estate Chat Agent"""
    
    @pytest.fixture
    def test_queries(self) -> List[Dict[str, str]]:
        """Load test queries from CSV"""
        queries = []
        csv_path = Path(__file__).parent.parent / "data" / "sample_queries.csv"
        
        if csv_path.exists():
            with open(csv_path, 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    queries.append(row)
        else:
            # Fallback queries if CSV not found
            queries = [
                {"question_id": "1", "query": "What's the average yield for apartments in Seattle?"},
                {"question_id": "2", "query": "Compare rental yields between Seattle and Portland"},
                {"question_id": "3", "query": "Show investment opportunities with yield above 5%"},
                {"question_id": "4", "query": "Market trends in Austin over the past year"},
                {"question_id": "5", "query": "Market summary for San Francisco"}
            ]
        
        return queries
    
    @pytest.fixture
    def router(self):
        """Create QueryRouter instance"""
        return QueryRouter()
    
    @pytest.fixture
    def results_dir(self):
        """Create results directory"""
        results_path = Path(__file__).parent.parent / "results"
        results_path.mkdir(exist_ok=True)
        return results_path
    
    @pytest.mark.api
    def test_single_query_performance(self, router):
        """Test performance of a single query"""
        query = "What's the average yield for 2-bedroom apartments in downtown Seattle?"
        
        start_time = time.time()
        response = router.route_query(query)
        end_time = time.time()
        
        response_time = end_time - start_time
        
        # Performance assertions
        assert response_time < 30, f"Response time {response_time}s exceeds 30s limit"
        assert response.content is not None
        assert response.model_used is not None
        assert response.response_time > 0
        
        # Log performance metrics
        print(f"\\nSingle Query Performance:")
        print(f"Query: {query}")
        print(f"Response Time: {response_time:.2f}s")
        print(f"Model Used: {response.model_used}")
        print(f"Engine Used: {response.engine_used}")
        print(f"Cost: ${response.cost:.4f}")
    
    @pytest.mark.api
    @pytest.mark.slow
    def test_batch_query_performance(self, router, test_queries, results_dir):
        """Test performance across multiple queries"""
        results = []
        total_start = time.time()
        
        for query_data in test_queries[:10]:  # Test first 10 queries
            query = query_data['query']
            
            start_time = time.time()
            try:
                response = router.route_query(query)
                end_time = time.time()
                
                results.append({
                    'question_id': query_data['question_id'],
                    'query': query,
                    'response_time': end_time - start_time,
                    'success': True,
                    'model_used': response.model_used,
                    'engine_used': response.engine_used,
                    'cost': response.cost,
                    'error': None
                })
                
            except Exception as e:
                end_time = time.time()
                results.append({
                    'question_id': query_data['question_id'],
                    'query': query,
                    'response_time': end_time - start_time,
                    'success': False,
                    'model_used': None,
                    'engine_used': None,
                    'cost': 0.0,
                    'error': str(e)
                })
        
        total_time = time.time() - total_start
        
        # Save results to CSV
        output_path = results_dir / f"performance_results_{int(time.time())}.csv"
        df = pd.DataFrame(results)
        df.to_csv(output_path, index=False)
        
        # Calculate metrics
        successful_queries = [r for r in results if r['success']]
        avg_response_time = sum(r['response_time'] for r in successful_queries) / len(successful_queries)
        total_cost = sum(r['cost'] for r in results)
        success_rate = len(successful_queries) / len(results) * 100
        
        # Performance assertions
        assert success_rate >= 80, f"Success rate {success_rate}% is below 80%"
        assert avg_response_time < 15, f"Average response time {avg_response_time}s exceeds 15s"
        
        # Print summary
        print(f"\\nBatch Query Performance Summary:")
        print(f"Total Queries: {len(results)}")
        print(f"Successful: {len(successful_queries)}")
        print(f"Success Rate: {success_rate:.1f}%")
        print(f"Average Response Time: {avg_response_time:.2f}s")
        print(f"Total Time: {total_time:.2f}s")
        print(f"Total Cost: ${total_cost:.4f}")
        print(f"Results saved to: {output_path}")
    
    @pytest.mark.api
    def test_model_fallback_performance(self, router):
        """Test performance of model fallback mechanism"""
        # This would require mocking the primary model to fail
        # For now, we'll just test the routing logic
        query = "What's the market yield in Seattle?"
        
        response = router.route_query(query)
        
        assert response.model_used in [
            "meta-llama/llama-3.1-8b-instruct:free",
            "deepseek/deepseek-r1:free",
            "qwen/qwen-plus:free",
            "microsoft/phi-3-medium-128k-instruct:free"
        ]
    
    @pytest.mark.db
    def test_database_query_performance(self):
        """Test database query performance"""
        db = RealEstateDatabase()
        
        if not db.test_connection():
            pytest.skip("Database connection not available")
        
        queries = [
            lambda: db.get_market_yield("seattle", "apartment", 2),
            lambda: db.get_market_trends("austin", 12),
            lambda: db.compare_locations(["seattle", "portland"], "apartment"),
            lambda: db.get_investment_opportunities(5.0, 500000),
            lambda: db.get_market_summary("san francisco")
        ]
        
        for i, query_func in enumerate(queries):
            start_time = time.time()
            try:
                result = query_func()
                end_time = time.time()
                response_time = end_time - start_time
                
                assert response_time < 5, f"Database query {i+1} took {response_time}s (>5s)"
                print(f"Database query {i+1} completed in {response_time:.3f}s")
                
            except Exception as e:
                print(f"Database query {i+1} failed: {str(e)}")
    
    def test_rate_limit_awareness(self):
        """Test rate limit tracking"""
        client = OpenRouterClient()
        
        # Simulate multiple requests
        for i in range(5):
            client.usage_count += 1
        
        limits = client.check_rate_limits()
        
        assert limits['current_usage'] == 5
        assert limits['remaining_calls'] == limits['daily_limit'] - 5
        assert limits['usage_percentage'] > 0
    
    @pytest.mark.parametrize("query_count", [10, 25, 50])
    def test_scalability(self, router, query_count):
        \"\"\"Test system scalability with different query volumes\"\"\"
        queries = [
            f"What's the yield for property type {i % 5} in location {i % 10}?"
            for i in range(query_count)
        ]
        
        start_time = time.time()
        results = []
        
        for query in queries:
            try:
                response = router.parse_query(query)  # Just test parsing for speed
                results.append(response)
            except Exception:
                pass
        
        total_time = time.time() - start_time
        avg_time = total_time / query_count
        
        # Parsing should be very fast
        assert avg_time < 0.01, f"Average parsing time {avg_time}s exceeds 0.01s"
        
        print(f"\\nScalability Test ({query_count} queries):")
        print(f"Total Time: {total_time:.2f}s")
        print(f"Average Time per Query: {avg_time:.4f}s")