#!/bin/bash
source ~/venvs/sidechannel/bin/activate
cd /mnt/e/RESEARCH/adapter-residency-sidechannel/scripts
python3 ../drivers/rq2_adaptive.py \
  --target med \
  --canary junk_5_r32 \
  --fillers junk_0_r8 junk_1_r16 junk_2_r32 junk_3_r8 junk_4_r16 \
  --max-cpu-loras 4 \
  --trials 20 \
  --k 3 \
  --diff-threshold-ms 25 \
  --out ../results/rq2_adaptive_raw.csv
