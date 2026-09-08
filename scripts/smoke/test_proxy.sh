#!/bin/bash
echo "--- direct to vLLM (port 8000) ---"
time curl -s -X POST http://localhost:8000/v1/completions \
  -H "Content-Type: application/json" \
  --data '{"model": "med", "prompt": "test", "max_tokens": 1, "temperature": 0}' -o /dev/null
echo "--- through proxy (port 8001) ---"
time curl -s -X POST http://localhost:8001/v1/completions \
  -H "Content-Type: application/json" \
  --data '{"model": "med", "prompt": "test", "max_tokens": 1, "temperature": 0}' -o /dev/null
