#!/bin/bash
source ~/venvs/sidechannel/bin/activate
cd /mnt/e/RESEARCH/adapter-residency-sidechannel/harness
nohup python3 noise_generator.py \
  --adapters med law junk_0_r8 junk_1_r16 junk_2_r32 junk_3_r8 junk_4_r16 junk_5_r32 \
  --workers 6 --duration-s 90 --min-tokens 1 --max-tokens 64 --min-words 3 --max-words 40 \
  > ../results/noise_generator4.log 2>&1 &
disown
sleep 1
echo NOISE_LAUNCHED
