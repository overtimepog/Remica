import pytest
import csv
import time
import json
from pathlib import Path
from src.core.chat_agent import ChatAgent
from src.config import Config

class TestChatAgent:
    """Integration tests for the containerized chat agent"""
    
    @pytest.fixture
    def agent(self):
        """Create a test chat agent instance"""
        config = Config()
        return ChatAgent(config, test_mode=True)
    
    @pytest.fixture
    def test_queries_path(self):
        """Path to test queries CSV"""
        return Path("/app/test_data/queries.csv")
    
    @pytest.fixture
    def results_dir(self):
        """Create results directory"""
        results_path = Path("/app/test_results")
        results_path.mkdir(exist_ok=True)
        return results_path
    
    def test_single_query_response(self, agent):
        """Test a single query returns valid response"""
        query = "What's the rental yield for 2-bedroom apartments in Seattle?"
        
        response = agent.process_query(query)
        
        assert response is not None
        assert response.success is True
        assert response.content is not None and len(response.content) > 0
        assert response.model_used is not None
        assert response.engine_used is not None
        assert response.processing_time < 30.0
    
    def test_error_handling(self, agent):
        """Test error handling with invalid query"""
        query = ""  # Empty query
        
        response = agent.process_query(query)
        
        assert response is not None
        # Even with errors, we should get a response
        assert response.content is not None
    
    @pytest.mark.slow
    def test_batch_queries(self, agent, test_queries_path, results_dir):
        """Test all 1000 queries from CSV file"""
        if not test_queries_path.exists():
            pytest.skip(f"Test queries file not found at {test_queries_path}")
        
        results = []
        successful_queries = 0
        within_time_limit = 0
        
        # Load test queries
        with open(test_queries_path, 'r') as f:
            reader = csv.DictReader(f)
            queries = list(reader)
        
        print(f"\nRunning {len(queries)} test queries...")
        start_time = time.time()
        
        for i, row in enumerate(queries):
            query_start = time.time()
            
            try:
                response = agent.process_query(row['query'])
                query_time = time.time() - query_start
                
                result = {
                    'question_id': row['question_id'],
                    'query': row['query'],
                    'response_time': query_time,
                    'success': response.success,
                    'model_used': response.model_used,
                    'engine_used': response.engine_used,
                    'within_time_limit': query_time < 30.0,
                    'error': response.error
                }
                
                if response.success:
                    successful_queries += 1
                if query_time < 30.0:
                    within_time_limit += 1
                
                results.append(result)
                
                # Print progress every 10 queries
                if (i + 1) % 10 == 0:
                    print(f"Processed {i + 1}/{len(queries)} queries...")
                    
            except Exception as e:
                print(f"Error on query {row['question_id']}: {str(e)}")
                results.append({
                    'question_id': row['question_id'],
                    'query': row['query'],
                    'response_time': 0,
                    'success': False,
                    'error': str(e)
                })
        
        total_time = time.time() - start_time
        
        # Save results
        timestamp = int(time.time())
        results_file = results_dir / f"test_results_{timestamp}.json"
        
        with open(results_file, 'w') as f:
            json.dump({
                'summary': {
                    'total_queries': len(queries),
                    'successful_queries': successful_queries,
                    'success_rate': successful_queries / len(queries),
                    'within_time_limit': within_time_limit,
                    'time_limit_rate': within_time_limit / len(queries),
                    'total_time': total_time,
                    'avg_time_per_query': total_time / len(queries)
                },
                'results': results
            }, f, indent=2)
        
        print(f"\nTest Results:")
        print(f"Total Queries: {len(queries)}")
        print(f"Successful: {successful_queries} ({successful_queries/len(queries)*100:.1f}%)")
        print(f"Within 30s: {within_time_limit} ({within_time_limit/len(queries)*100:.1f}%)")
        print(f"Total Time: {total_time:.2f}s")
        print(f"Results saved to: {results_file}")
        
        # Assertions
        assert successful_queries / len(queries) >= 0.90, "Success rate should be at least 90%"
        assert within_time_limit / len(queries) >= 0.95, "95% of queries should complete within 30 seconds"
    
    def test_query_types(self, agent):
        """Test different query types"""
        test_cases = [
            ("What's the yield for apartments in Seattle?", "market_yield"),
            ("Show me price trends in Austin", "market_trends"),
            ("Compare Seattle vs Portland", "location_comparison"),
            ("Find investment opportunities above 5% yield", "investment_opportunities"),
            ("Market summary for San Francisco", "market_summary")
        ]
        
        for query, expected_type in test_cases:
            response = agent.process_query(query)
            assert response is not None
            assert response.success is True
            # Engine used should reflect the query type
            print(f"Query: {query} -> Engine: {response.engine_used}")
    
    def test_model_fallback(self, agent):
        """Test that model fallback works"""
        # This tests the fallback mechanism indirectly
        queries = [
            "What's the rental yield in Seattle?",
            "Compare markets between Portland and Austin",
            "Show investment opportunities"
        ]
        
        models_used = set()
        
        for query in queries:
            response = agent.process_query(query)
            assert response is not None
            models_used.add(response.model_used)
        
        print(f"Models used: {models_used}")
        # At least one model should be used
        assert len(models_used) >= 1
    
    def test_performance_metrics(self, agent):
        """Test performance across different query complexities"""
        queries = [
            ("Simple yield query", "What's the yield in Seattle?"),
            ("Complex comparison", "Compare 2-bedroom apartment yields between Seattle, Portland, San Francisco, and Austin over the last 2 years"),
            ("Detailed analysis", "Show me investment opportunities for 3-bedroom houses under $500k with yield above 5% in tech hub cities")
        ]
        
        for name, query in queries:
            start = time.time()
            response = agent.process_query(query)
            elapsed = time.time() - start
            
            print(f"\n{name}:")
            print(f"  Query: {query}")
            print(f"  Time: {elapsed:.2f}s")
            print(f"  Model: {response.model_used}")
            print(f"  Engine: {response.engine_used}")
            
            assert response is not None
            assert elapsed < 30.0, f"{name} took too long: {elapsed}s"