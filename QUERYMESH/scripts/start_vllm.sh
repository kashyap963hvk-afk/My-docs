#!/usr/bin/env bash
# Start the language model server on the Hyperstack GPU (OpenAI-compatible API on port 8000).
set -euo pipefail
cd "$(dirname "$0")/.."
LLM_API_KEY=$(grep '^LLM_API_KEY=' .env | cut -d= -f2)

docker rm -f vllm 2>/dev/null || true
docker run -d --name vllm --restart unless-stopped \
  --gpus all --ipc=host -p 8000:8000 \
  -v "$HOME/.cache/huggingface:/root/.cache/huggingface" \
  vllm/vllm-openai:v0.32.0 \
  --model Qwen/Qwen3-4B-Instruct-2507 \
  --served-model-name qwen3-4b \
  --max-model-len 32768 \
  --gpu-memory-utilization 0.80 \
  --api-key "$LLM_API_KEY"
echo "vLLM is starting. Follow the log with: docker logs -f vllm"
