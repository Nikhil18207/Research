#!/bin/bash
pkill -f 'vllm serve'
sleep 2
source ~/venvs/sidechannel/bin/activate
cd /mnt/e/RESEARCH/adapter-residency-sidechannel
VLLM_WSL2_ENABLE_PIN_MEMORY=1 VLLM_USE_FLASHINFER_SAMPLER=0 VLLM_BATCH_INVARIANT=1 nohup vllm serve Qwen/Qwen2.5-1.5B \
  --enable-lora --max-loras 2 --max-cpu-loras 4 --max-lora-rank 32 \
  --gpu-memory-utilization 0.75 --max-model-len 4096 \
  --lora-modules med=./adapters/qwen_med law=./adapters/qwen_law \
    junk_0_r8=./adapters/qwen_junk/junk_0_r8 junk_1_r16=./adapters/qwen_junk/junk_1_r16 \
    junk_2_r8=./adapters/qwen_junk/junk_2_r8 junk_3_r16=./adapters/qwen_junk/junk_3_r16 \
  > results/vllm_server_qwen.log 2>&1 &
disown
sleep 2
echo LAUNCHED
