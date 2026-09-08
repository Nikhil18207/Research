#!/bin/bash
source ~/venvs/sidechannel/bin/activate
cd /mnt/e/RESEARCH/adapter-residency-sidechannel/scripts
python3 ../drivers/rq3_identification.py \
  --adapter-a junk_0_r8 \
  --adapter-b junk_3_r8 \
  --fillers junk_1_r16 junk_2_r32 junk_4_r16 junk_5_r32 \
  --max-cpu-loras 4 \
  --trials 40 \
  --threshold-ms 60 \
  --out ../results/rq3_raw.csv
