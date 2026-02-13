#!/bin/bash

echo "🧪 Testing Ollama connectivity..."
echo ""

# Test 1: Is Ollama running?
echo "1. Checking if Ollama is running..."
if curl -s http://localhost:11434/api/tags > /dev/null; then
    echo "   ✅ Ollama is running"
else
    echo "   ❌ Ollama is NOT running"
    echo "   Start with: ollama serve"
    exit 1
fi

# Test 2: List models
echo ""
echo "2. Available models:"
curl -s http://localhost:11434/api/tags | jq -r '.models[].name' || echo "   No models found"

# Test 3: Simple generation test
echo ""
echo "3. Testing generation with qwen2.5-coder:1.5b..."
RESPONSE=$(curl -s -X POST http://localhost:11434/api/generate \
  -d '{
    "model": "qwen2.5-coder:1.5b",
    "prompt": "Write hello world in Python",
    "stream": false
  }')

if echo "$RESPONSE" | grep -q "response"; then
    echo "   ✅ Model responds correctly"
    echo "   Response: $(echo $RESPONSE | jq -r '.response' | head -c 100)..."
else
    echo "   ❌ Model failed"
    echo "   Error: $RESPONSE"
fi

echo ""
echo "✅ Ollama test complete"

