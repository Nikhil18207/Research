#!/bin/bash
source ~/venvs/sidechannel/bin/activate
cd /mnt/e/RESEARCH/adapter-residency-sidechannel/scripts
python3 ../drivers/rank_sweep_measure.py \
  --targets med_r1:1 med:8 med_r16:16 med_r32:32 med_r64:64 \
  --fillers junk_0_r8 junk_1_r16 junk_2_r32 junk_3_r8 junk_4_r16 junk_5_r32 \
  --max-cpu-loras 4 \
  --trials 15 \
  --out ../results/rank_sweep_raw.csv
