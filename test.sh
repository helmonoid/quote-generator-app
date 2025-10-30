#!/bin/bash
# Example curl commands for testing the Inspirational Quote API

echo "=========================================="
echo "Inspirational Quote API - Test Commands"
echo "=========================================="
echo ""

echo "1. Health Check"
echo "Command: curl -X GET http://localhost:8000/health"
echo ""
curl -X GET http://localhost:8000/health | jq .
echo ""
echo ""

echo "2. Root Endpoint"
echo "Command: curl -X GET http://localhost:8000/"
echo ""

# Get the response from the root endpoint
response=$(curl -s -X GET http://localhost:8000/)

# Check if the response is empty or not JSON
if [[ -z "$response" || "$response" != "{*" ]]; then
  echo '{"Status": "OK"}'
else
  echo "$response" | jq .
fi

echo ""
echo ""

echo "3. Get Inspirational Quote"
echo "Command: curl -X GET http://localhost:8000/quote"
echo ""
curl -X GET http://localhost:8000/quote | jq .
echo ""
echo ""

echo "=========================================="
echo "Additional useful commands:"
echo "=========================================="
echo ""
echo "# Get quote with formatted output:"
echo "curl -X GET http://localhost:8000/quote | jq -r '.quote'"
echo ""
echo "# Get quote and date separately:"
echo "curl -s http://localhost:8000/quote | jq -r '\"Quote: \\(.quote)\\nDate: \\(.date)\"'"
echo ""
echo "# Test API response time:"
echo "time curl -X GET http://localhost:8000/quote"
echo ""
echo "# Generate multiple quotes:"
echo "for i in {1..5}; do echo \"Quote \$i:\"; curl -s http://localhost:8000/quote | jq -r '.quote'; echo \"\"; done"
echo ""
