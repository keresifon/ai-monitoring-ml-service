#!/bin/bash

# Test script for ML Service
# Make sure the service is running: uvicorn main:app --reload

BASE_URL="http://localhost:8000"

echo "========================================="
echo "Testing ML Service"
echo "========================================="
echo ""

# Test 1: Health Check
echo "1. Testing Health Check..."
curl -s "$BASE_URL/api/v1/health" | jq '.'
echo ""
echo ""

# Test 2: Readiness Check
echo "2. Testing Readiness Check..."
curl -s "$BASE_URL/api/v1/ready" | jq '.'
echo ""
echo ""

# Test 3: Model Info (before training)
echo "3. Testing Model Info (before training)..."
curl -s "$BASE_URL/api/v1/model/info" | jq '.'
echo ""
echo ""

# Test 4: Train Model
echo "4. Training Model with sample data..."
curl -s -X POST "$BASE_URL/api/v1/train" \
  -H "Content-Type: application/json" \
  -d @sample_training_data.json | jq '.'
echo ""
echo ""

# Test 5: Model Info (after training)
echo "5. Testing Model Info (after training)..."
curl -s "$BASE_URL/api/v1/model/info" | jq '.'
echo ""
echo ""

# Test 6: Predict Normal Log
echo "6. Testing Prediction - Normal Log..."
curl -s -X POST "$BASE_URL/api/v1/predict" \
  -H "Content-Type: application/json" \
  -d '{
    "log_id": "test-log-001",
    "features": {
      "message_length": 50,
      "level": "INFO",
      "service": "api-gateway",
      "has_exception": false,
      "has_timeout": false,
      "has_connection_error": false
    }
  }' | jq '.'
echo ""
echo ""

# Test 7: Predict Anomalous Log
echo "7. Testing Prediction - Anomalous Log..."
curl -s -X POST "$BASE_URL/api/v1/predict" \
  -H "Content-Type: application/json" \
  -d '{
    "log_id": "test-log-002",
    "features": {
      "message_length": 500,
      "level": "FATAL",
      "service": "unknown-service",
      "has_exception": true,
      "has_timeout": true,
      "has_connection_error": true
    }
  }' | jq '.'
echo ""
echo ""

# Test 8: Batch Prediction
echo "8. Testing Batch Prediction..."
curl -s -X POST "$BASE_URL/api/v1/predict/batch" \
  -H "Content-Type: application/json" \
  -d '[
    {
      "log_id": "batch-001",
      "features": {
        "message_length": 45,
        "level": "INFO",
        "service": "api-gateway",
        "has_exception": false,
        "has_timeout": false,
        "has_connection_error": false
      }
    },
    {
      "log_id": "batch-002",
      "features": {
        "message_length": 300,
        "level": "ERROR",
        "service": "unknown",
        "has_exception": true,
        "has_timeout": true,
        "has_connection_error": true
      }
    }
  ]' | jq '.'
echo ""
echo ""

echo "========================================="
echo "All tests completed!"
echo "========================================="

# Made with Bob
