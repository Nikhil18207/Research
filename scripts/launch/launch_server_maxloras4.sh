#!/bin/bash
pkill -f 'vllm serve'
sleep 2
source ~/venvs/sidechannel/bin/activate
cd /mnt/e/RESEARCH/adapter-residency-sidechannel
VLLM_WSL2_ENABLE_PIN_MEMORY=1 VLLM_USE_FLASHINFER_SAMPLER=0 VLLM_BATCH_INVARIANT=1 nohup vllm serve meta-llama/Llama-3.2-1B \
  --enable-lora --max-loras 4 --max-cpu-loras 4 --max-lora-rank 32 \
  --gpu-memory-utilization 0.75 --max-model-len 4096 \
  --lora-modules med=./adapters/med law=./adapters/law \
    junk_0_r8=./adapters/junk_0_r8 junk_1_r16=./adapters/junk_1_r16 junk_2_r32=./adapters/junk_2_r32 \
    junk_3_r8=./adapters/junk_3_r8 junk_4_r16=./adapters/junk_4_r16 junk_5_r32=./adapters/junk_5_r32 \
  > results/vllm_server_maxloras4.log 2>&1 &
disown
sleep 2
echo LAUNCHED
