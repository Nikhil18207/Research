#!/bin/bash
source ~/venvs/sidechannel/bin/activate
cd /mnt/e/RESEARCH/adapter-residency-sidechannel/scripts
python3 ../drivers/rq3_multiprobe_noisy.py \
  --adapter-a med \
  --adapter-b law \
  --fillers junk_0_r8 junk_1_r16 junk_2_r32 junk_4_r16 \
  --max-cpu-loras 4 \
  --trials 20 \
  --k 5 \
  --out ../results/rq3_multiprobe_raw.csv
