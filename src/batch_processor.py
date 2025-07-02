#!/usr/bin/env python3
"""
Batch processor for CSV questions
Processes questions from CSV and outputs results with timing information
"""

import csv
import time
import argparse
import logging
from datetime import datetime
from typing import List, Dict, Any
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from core.chat_agent import ChatAgent
from query.router import QueryRouter

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class BatchProcessor:
    """Process questions from CSV files in batch mode"""
    
    def __init__(self, parallel: bool = False, workers: int = 5, cache: bool = True):
        self.chat_agent = ChatAgent()
        self.router = QueryRouter()
        self.parallel = parallel
        self.workers = workers
        self.cache = cache
        
    def process_single_question(self, question_id: str, question: str) -> Dict[str, Any]:
        """Process a single question and return results with metrics"""
        start_time = time.time()
        
        try:
            # Process the question
            response = self.chat_agent.process_query(question)
            
            # Calculate metrics
            query_time_ms = int((time.time() - start_time) * 1000)
            
            return {
                'question_id': question_id,
                'question': question,
                'answer': response.content,
                'query_time_ms': query_time_ms,
                'model_used': response.model_used,
                'engine_used': response.engine_used,
                'timestamp': datetime.now().isoformat(),
                'status': 'success',
                'error': None
            }
            
        except Exception as e:
            query_time_ms = int((time.time() - start_time) * 1000)
            logger.error(f"Error processing question {question_id}: {str(e)}")
            
            return {
                'question_id': question_id,
                'question': question,
                'answer': None,
                'query_time_ms': query_time_ms,
                'model_used': None,
                'engine_used': None,
                'timestamp': datetime.now().isoformat(),
                'status': 'error',
                'error': str(e)
            }
    
    def process_csv(self, input_file: str, output_file: str, 
                   verbose: bool = False, include_tokens: bool = False,
                   progress: bool = True) -> None:
        """Process questions from input CSV and write results to output CSV"""
        
        # Read input questions
        questions = []
        with open(input_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                questions.append({
                    'id': row['question_id'],
                    'question': row['question']
                })
        
        logger.info(f"Loaded {len(questions)} questions from {input_file}")
        
        # Process questions
        results = []
        
        if self.parallel:
            # Parallel processing
            logger.info(f"Processing questions in parallel with {self.workers} workers")
            
            with ThreadPoolExecutor(max_workers=self.workers) as executor:
                # Submit all tasks
                future_to_question = {
                    executor.submit(
                        self.process_single_question, 
                        q['id'], 
                        q['question']
                    ): q for q in questions
                }
                
                # Process completed tasks
                completed = 0
                for future in as_completed(future_to_question):
                    result = future.result()
                    results.append(result)
                    
                    completed += 1
                    if progress and completed % 10 == 0:
                        logger.info(f"Progress: {completed}/{len(questions)} questions processed")
                        
        else:
            # Sequential processing
            logger.info("Processing questions sequentially")
            
            for i, q in enumerate(questions):
                result = self.process_single_question(q['id'], q['question'])
                results.append(result)
                
                if progress and (i + 1) % 10 == 0:
                    logger.info(f"Progress: {i + 1}/{len(questions)} questions processed")
        
        # Sort results by question_id
        results.sort(key=lambda x: int(x['question_id']))
        
        # Write output CSV
        fieldnames = [
            'question_id', 'question', 'answer', 'query_time_ms',
            'model_used', 'engine_used', 'timestamp', 'status', 'error'
        ]
        
        if include_tokens:
            fieldnames.extend(['input_tokens', 'output_tokens', 'total_tokens'])
        
        with open(output_file, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(results)
        
        # Print summary
        successful = sum(1 for r in results if r['status'] == 'success')
        failed = sum(1 for r in results if r['status'] == 'error')
        avg_time = sum(r['query_time_ms'] for r in results) / len(results) if results else 0
        
        logger.info(f"\nBatch processing complete!")
        logger.info(f"Total questions: {len(questions)}")
        logger.info(f"Successful: {successful}")
        logger.info(f"Failed: {failed}")
        logger.info(f"Average query time: {avg_time:.0f}ms")
        logger.info(f"Results written to: {output_file}")


def main():
    """Main entry point for batch processor"""
    parser = argparse.ArgumentParser(
        description='Batch process real estate questions from CSV'
    )
    
    parser.add_argument(
        '--input', '-i',
        required=True,
        help='Input CSV file with questions'
    )
    
    parser.add_argument(
        '--output', '-o',
        required=True,
        help='Output CSV file for results'
    )
    
    parser.add_argument(
        '--parallel', '-p',
        action='store_true',
        help='Enable parallel processing'
    )
    
    parser.add_argument(
        '--workers', '-w',
        type=int,
        default=5,
        help='Number of parallel workers (default: 5)'
    )
    
    parser.add_argument(
        '--cache',
        action='store_true',
        default=True,
        help='Enable response caching'
    )
    
    parser.add_argument(
        '--no-cache',
        action='store_true',
        help='Disable response caching'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose output'
    )
    
    parser.add_argument(
        '--include-tokens',
        action='store_true',
        help='Include token counts in output'
    )
    
    parser.add_argument(
        '--progress',
        action='store_true',
        default=True,
        help='Show progress updates'
    )
    
    parser.add_argument(
        '--no-progress',
        action='store_true',
        help='Disable progress updates'
    )
    
    args = parser.parse_args()
    
    # Configure logging
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Create processor
    processor = BatchProcessor(
        parallel=args.parallel,
        workers=args.workers,
        cache=not args.no_cache
    )
    
    # Process CSV
    processor.process_csv(
        input_file=args.input,
        output_file=args.output,
        verbose=args.verbose,
        include_tokens=args.include_tokens,
        progress=not args.no_progress
    )


if __name__ == '__main__':
    main()