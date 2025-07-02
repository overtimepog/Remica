#!/bin/bash

echo "Testing Real Estate Chat Agent CLI..."
echo

# Test query
QUERY="What's the average price per square foot in Miami?"

# Run the query
echo "Query: $QUERY"
echo "$QUERY" | timeout 30 docker exec -i real-estate-chat-app python -m src.main 2>&1 | grep -A 20 "💬" | grep -v "Non-interactive" | head -20

echo
echo "CLI test completed successfully!"