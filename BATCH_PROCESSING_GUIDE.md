# Batch Processing Guide

## Overview
This guide explains how to use the batch processing feature to test the Real Estate Chat Agent with CSV files containing multiple questions.

## Features

### 1. Custom PostgreSQL Database Connection
You can connect the application to your own PostgreSQL database by:

1. **Updating `.env` file** with your database credentials:
   ```env
   DB_HOST=your-database-host.com
   DB_PORT=5432
   DB_NAME=your_database_name
   DB_USER=your_username
   DB_PASSWORD=your_password
   ```

2. **Applying the schema** to your database:
   ```bash
   psql -h your-database-host.com -U your_username -d your_database_name < database/schema.sql
   ```

3. **Starting only the app container** (comment out 'db' service in docker-compose.yml)

### 2. Batch Processing CSV Questions

Perfect for testing with 1000+ questions that require database queries.

#### Input Format
Create a CSV file with questions:
```csv
question_id,question
1,"What's the average rental yield for apartments in Seattle?"
2,"Compare investment opportunities between Portland and San Francisco"
3,"Show me market trends for Austin over the last 6 months"
```

#### Running Batch Processing

**Basic usage:**
```bash
./run.sh batch --input questions.csv --output results.csv
```

**With parallel processing (recommended for 1000+ questions):**
```bash
./run.sh batch --input questions.csv --output results.csv --parallel --workers 10
```

**With progress tracking:**
```bash
./run.sh batch --input questions.csv --output results.csv --parallel --progress
```

#### Output Format
The results CSV includes:
- `question_id`: Original question ID
- `question`: The input question
- `answer`: The generated answer using database data
- `query_time_ms`: Time taken to process (milliseconds)
- `model_used`: AI model that generated the answer
- `engine_used`: Query engine type (database_query, ai_generated, etc.)
- `timestamp`: When the query was processed
- `status`: success or error
- `error`: Error message if failed

#### Example Output
```csv
question_id,question,answer,query_time_ms,model_used,engine_used,timestamp,status,error
1,"What's the average rental yield...","The average rental yield is 5.8%...",1234,meta-llama/llama-3.1-8b-instruct:free,database_query,2024-01-15T10:30:00,success,
2,"Compare investment opportunities...","Portland offers 6.2% yield while SF...",2156,meta-llama/llama-3.1-8b-instruct:free,database_query,2024-01-15T10:30:01,success,
```

## Performance Optimizations

### Parallel Processing
- Uses ThreadPoolExecutor for concurrent query processing
- Default: 5 workers, adjustable with `--workers` flag
- Recommended for batches > 100 questions

### Caching
- Responses are cached for 1 hour
- Duplicate questions use cached results
- Disable with `--no-cache` flag

### Progress Tracking
- Shows progress every 10 questions
- Estimates time remaining
- Disable with `--no-progress` flag

## Sample Files

A sample questions file is provided at:
```
data/sample_questions.csv
```

Test it with:
```bash
./run.sh batch --input data/sample_questions.csv --output data/results.csv --parallel
```

## Tips for Large Batches (1000+ questions)

1. **Use parallel processing**: Add `--parallel --workers 10`
2. **Enable caching**: Avoid duplicate API calls
3. **Monitor progress**: Use `--progress` flag
4. **Split very large files**: Process in chunks of 5000 questions
5. **Check rate limits**: Ensure your API key has sufficient quota

## Troubleshooting

### Common Issues

1. **"Services not running"**
   - Run `./run.sh start` first

2. **"Database connection failed"**
   - Check your database credentials in `.env`
   - Ensure database is accessible from Docker

3. **"Rate limit exceeded"**
   - Reduce workers: `--workers 3`
   - Add delays between batches
   - Upgrade your OpenRouter plan

4. **"Out of memory"**
   - Process smaller batches
   - Increase Docker memory allocation

### Performance Metrics

Expected processing times:
- 100 questions: ~30 seconds (parallel)
- 1000 questions: ~5 minutes (parallel)
- 10000 questions: ~50 minutes (parallel)

Note: Times vary based on query complexity and API response times.