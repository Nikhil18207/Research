#!/bin/bash
source ~/venvs/sidechannel/bin/activate
cd /mnt/e/RESEARCH/adapter-residency-sidechannel/scripts
echo "=== Qwen RQ1 ==="
python3 ../drivers/rq1_tier_characterization.py \
  --target med \
  --fillers junk_0_r8 junk_1_r16 junk_2_r8 junk_3_r16 \
  --max-loras 2 --max-cpu-loras 4 --trials 20 \
  --out ../results/qwen_rq1_raw.csv
echo "=== Qwen RQ3 ==="
python3 ../drivers/rq3_identification.py \
  --adapter-a med --adapter-b law \
  --fillers junk_0_r8 junk_1_r16 junk_2_r8 junk_3_r16 \
  --max-cpu-loras 4 --trials 40 --threshold-ms 60 \
  --out ../results/qwen_rq3_raw.csv
