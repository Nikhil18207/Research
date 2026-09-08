#!/bin/bash
source ~/venvs/sidechannel/bin/activate
cd /mnt/e/RESEARCH/adapter-residency-sidechannel/scripts
python3 ../drivers/rq1_tier_characterization.py \
  --target junk_0_r8 \
  --fillers junk_1_r16 junk_2_r32 junk_3_r8 junk_4_r16 junk_5_r32 \
  --max-loras 2 \
  --max-cpu-loras 4 \
  --trials 30 \
  --out ../results/rq1_raw.csv
