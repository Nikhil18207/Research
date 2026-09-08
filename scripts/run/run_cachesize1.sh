#!/bin/bash
source ~/venvs/sidechannel/bin/activate
cd /mnt/e/RESEARCH/adapter-residency-sidechannel/scripts
python3 ../drivers/rq1_tier_characterization.py \
  --target med \
  --fillers junk_0_r8 junk_1_r16 junk_2_r32 junk_3_r8 junk_4_r16 junk_5_r32 \
  --max-loras 1 \
  --max-cpu-loras 4 \
  --trials 15 \
  --out ../results/cachesize_maxloras1_raw.csv
