#!/bin/bash
echo "--- MED adapter ---"
curl -s -X POST http://localhost:8000/v1/completions \
  -H "Content-Type: application/json" \
  --data '{"model": "med", "prompt": "Q: What are the common symptoms of type 2 diabetes?\nA:", "max_tokens": 40, "temperature": 0}'
echo ""
echo "--- LAW adapter ---"
curl -s -X POST http://localhost:8000/v1/completions \
  -H "Content-Type: application/json" \
  --data '{"model": "law", "prompt": "Q: What is a contract?\nA:", "max_tokens": 40, "temperature": 0}'
echo ""
