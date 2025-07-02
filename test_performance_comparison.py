#!/usr/bin/env python3
"""
Performance comparison between original and optimized implementations
"""

import time
import statistics
from typing import List, Dict, Tuple, Any

# Test queries
TEST_QUERIES = [
    "What's the average yield for apartments in Seattle?",
    "Show me market trends in San Francisco",
    "Compare Portland vs Austin for rental investment",
    "Find properties with yield above 6%",
    "Market summary for Miami"
]

def measure_response_time(router, query: str) -> Tuple[float, str]:
    """Measure response time for a single query"""
    start_time = time.time()
    
    try:
        response = router.route_query(query)
        response_time = time.time() - start_time
        return response_time, response.engine_used
    except Exception as e:
        print(f"Error processing query: {e}")
        return -1, "error"

def run_performance_test(router_class_name: str, test_name: str, warm_cache: bool = False) -> Dict[str, Any]:
    """Run performance test with given router"""
    print(f"\n{'='*60}")
    print(f"Testing: {test_name}")
    print(f"Cache: {'Warm' if warm_cache else 'Cold'}")
    print(f"{'='*60}")
    
    # Import and initialize router
    if router_class_name == "QueryRouter":
        from src.query.router import QueryRouter
        router = QueryRouter()
    else:
        from src.query.optimized_router import OptimizedQueryRouter
        router = OptimizedQueryRouter()
    
    response_times = []
    
    # Warm up cache if requested
    if warm_cache:
        print("Warming up cache...")
        for query in TEST_QUERIES:
            _ = measure_response_time(router, query)
    
    # Run actual tests
    print("\nRunning tests...")
    for i, query in enumerate(TEST_QUERIES, 1):
        print(f"\nQuery {i}: {query[:50]}...")
        response_time, engine = measure_response_time(router, query)
        
        if response_time > 0:
            response_times.append(response_time)
            print(f"  Time: {response_time:.2f}s")
            print(f"  Engine: {engine}")
        else:
            print(f"  Error occurred")
    
    # Calculate statistics
    if response_times:
        stats = {
            'avg_time': statistics.mean(response_times),
            'median_time': statistics.median(response_times),
            'min_time': min(response_times),
            'max_time': max(response_times),
            'total_time': sum(response_times),
            'queries_completed': len(response_times)
        }
        
        print(f"\n{'-'*40}")
        print(f"Average response time: {stats['avg_time']:.2f}s")
        print(f"Median response time: {stats['median_time']:.2f}s")
        print(f"Min/Max: {stats['min_time']:.2f}s / {stats['max_time']:.2f}s")
        print(f"Total time: {stats['total_time']:.2f}s")
        print(f"Queries completed: {stats['queries_completed']}/{len(TEST_QUERIES)}")
        
        return stats
    else:
        print("\nNo successful queries")
        return {}

def main():
    """Run performance comparison"""
    print("Real Estate Chat Agent - Performance Comparison")
    print("=" * 60)
    
    results = {}
    
    # Test original implementation
    print("\n\n1. ORIGINAL IMPLEMENTATION")
    results['original'] = run_performance_test("QueryRouter", "Original Router", warm_cache=False)
    
    # Test optimized implementation (cold cache)
    print("\n\n2. OPTIMIZED IMPLEMENTATION (Cold Cache)")
    results['optimized_cold'] = run_performance_test("OptimizedQueryRouter", "Optimized Router", warm_cache=False)
    
    # Test optimized implementation (warm cache)
    print("\n\n3. OPTIMIZED IMPLEMENTATION (Warm Cache)")
    results['optimized_warm'] = run_performance_test("OptimizedQueryRouter", "Optimized Router", warm_cache=True)
    
    # Summary comparison
    print("\n\n" + "="*60)
    print("PERFORMANCE COMPARISON SUMMARY")
    print("="*60)
    
    if 'original' in results and results['original']:
        original_avg = results['original']['avg_time']
        print(f"\nOriginal Implementation:")
        print(f"  Average Response Time: {original_avg:.2f}s")
        
        if 'optimized_cold' in results and results['optimized_cold']:
            opt_cold_avg = results['optimized_cold']['avg_time']
            improvement_cold = ((original_avg - opt_cold_avg) / original_avg) * 100
            print(f"\nOptimized (Cold Cache):")
            print(f"  Average Response Time: {opt_cold_avg:.2f}s")
            print(f"  Improvement: {improvement_cold:.1f}%")
            print(f"  Speedup: {original_avg/opt_cold_avg:.1f}x")
        
        if 'optimized_warm' in results and results['optimized_warm']:
            opt_warm_avg = results['optimized_warm']['avg_time']
            improvement_warm = ((original_avg - opt_warm_avg) / original_avg) * 100
            print(f"\nOptimized (Warm Cache):")
            print(f"  Average Response Time: {opt_warm_avg:.2f}s")
            print(f"  Improvement: {improvement_warm:.1f}%")
            print(f"  Speedup: {original_avg/opt_warm_avg:.1f}x")
    
    print("\n" + "="*60)
    print("Test completed!")

if __name__ == "__main__":
    main()