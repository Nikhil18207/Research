#!/bin/bash
pkill -9 -f 'vllm serve' 2>/dev/null
sleep 2
source ~/venvs/sidechannel/bin/activate
cd /mnt/e/RESEARCH/adapter-residency-sidechannel
VLLM_WSL2_ENABLE_PIN_MEMORY=1 VLLM_USE_FLASHINFER_SAMPLER=0 VLLM_BATCH_INVARIANT=1 nohup vllm serve HuggingFaceTB/SmolLM2-1.7B \
  --enable-lora --max-loras 2 --max-cpu-loras 4 --max-lora-rank 32 \
  --gpu-memory-utilization 0.75 --max-model-len 4096 \
  --lora-modules med=./adapters/smol_med law=./adapters/smol_law \
    junk_0_r8=./adapters/smol_junk/junk_0_r8 junk_1_r16=./adapters/smol_junk/junk_1_r16 \
    junk_2_r8=./adapters/smol_junk/junk_2_r8 junk_3_r16=./adapters/smol_junk/junk_3_r16 \
  > results/vllm_server_smol.log 2>&1 &
disown
sleep 2
echo LAUNCHED
