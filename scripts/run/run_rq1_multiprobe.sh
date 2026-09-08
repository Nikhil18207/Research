#!/bin/bash
source ~/venvs/sidechannel/bin/activate
cd /mnt/e/RESEARCH/adapter-residency-sidechannel/scripts
python3 ../drivers/rq1_multiprobe_noisy.py \
  --target med \
  --fillers junk_0_r8 junk_1_r16 junk_2_r32 junk_3_r8 junk_4_r16 junk_5_r32 \
  --max-loras 2 \
  --max-cpu-loras 4 \
  --trials 15 \
  --k 10 \
  --out ../results/rq1_multiprobe_raw.csv
