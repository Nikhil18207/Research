#!/bin/bash
curl -s -X POST http://localhost:8000/v1/completions \
  -H "Content-Type: application/json" \
  --data '{"model": "junk_0_r8", "prompt": "The capital of France is", "max_tokens": 5, "temperature": 0}'
echo ""
