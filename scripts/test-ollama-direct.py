#!/usr/bin/env python3
"""Test Ollama API directly to debug timeout issues."""

import httpx
import json
import time

# Simple test prompt
prompt = """You are an expert Python developer. Fix this typo in the code:

FILE: test.py
```python
def hello():
    print("Helo World")  # Typo: Helo -> Hello
```

Generate the corrected file in this format:

FILE: test.py
```python
# corrected code here
```
"""

print("🧪 Testing Ollama API...")
print(f"Prompt length: {len(prompt)} characters")
print()

# Request payload
payload = {
    "model": "qwen2.5-coder:3b",
    "prompt": prompt,
    "stream": False,
    "options": {
        "temperature": 0.2,
        "top_p": 0.9,
    }
}

print("📤 Sending request to Ollama...")
print(f"Model: {payload['model']}")
print(f"Stream: {payload['stream']}")
print()

start_time = time.time()

try:
    with httpx.Client(timeout=600.0) as client:  # 10 minute timeout
        response = client.post(
            "http://localhost:11434/api/generate",
            json=payload
        )
        
        elapsed = time.time() - start_time
        
        response.raise_for_status()
        data = response.json()
        
        print(f"✅ Success! ({elapsed:.2f} seconds)")
        print()
        print("📊 Response stats:")
        print(f"  Response length: {len(data.get('response', ''))} chars")
        print(f"  Total duration: {data.get('total_duration', 0) / 1e9:.2f}s")
        print(f"  Load duration: {data.get('load_duration', 0) / 1e9:.2f}s")
        print(f"  Eval count: {data.get('eval_count', 0)} tokens")
        print()
        print("📝 Generated response:")
        print("-" * 80)
        print(data.get('response', ''))
        print("-" * 80)
        
except httpx.ReadTimeout:
    elapsed = time.time() - start_time
    print(f"❌ Timeout after {elapsed:.2f} seconds")
    print()
    print("💡 The model is taking too long. Try:")
    print("  1. Use a smaller model")
    print("  2. Reduce prompt size")
    print("  3. Increase timeout further")
    
except httpx.HTTPError as e:
    print(f"❌ HTTP Error: {e}")
    
except Exception as e:
    print(f"❌ Error: {e}")

print()
print("This is exactly what your worker sends to Ollama.")
print("If this times out, the issue is Ollama performance, not your code.")

