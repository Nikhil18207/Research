#!/bin/bash
echo "--- direct to vLLM ---"
time curl -s -X POST http://localhost:8000/v1/completions \
  -H "Content-Type: application/json" \
  --data '{"model": "med", "prompt": "test", "max_tokens": 1, "temperature": 0}' -o /dev/null -w "%{http_code}\n"
