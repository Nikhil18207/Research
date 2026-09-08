#!/bin/bash
source ~/venvs/sidechannel/bin/activate
cd /mnt/e/RESEARCH/adapter-residency-sidechannel/scripts
python3 ../drivers/rq2_poisson_traffic.py \
  --target med \
  --fillers junk_0_r8 junk_1_r16 junk_2_r32 junk_3_r8 junk_4_r16 junk_5_r32 \
  --max-cpu-loras 4 \
  --trials 40 \
  --window-s 3.0 \
  --probes-per-window 1 \
  --threshold-ms 60 \
  --out ../results/rq2_poisson_fixed_raw.csv
