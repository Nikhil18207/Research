#!/bin/bash
source ~/venvs/sidechannel/bin/activate
cd /mnt/e/RESEARCH/adapter-residency-sidechannel/scripts
echo "=== single-probe (corrected noise) ==="
python3 ../drivers/rq2_prime_probe.py \
  --target med \
  --fillers junk_0_r8 junk_1_r16 junk_2_r32 junk_3_r8 junk_4_r16 junk_5_r32 \
  --max-cpu-loras 4 --trials 40 --threshold-ms 60 \
  --out ../results/rq2_noisy2_raw.csv
echo "=== multiprobe (corrected noise) ==="
python3 ../drivers/rq2_multiprobe_noisy.py \
  --target med \
  --fillers junk_0_r8 junk_1_r16 junk_2_r32 junk_3_r8 junk_4_r16 junk_5_r32 \
  --max-cpu-loras 4 --trials 20 --k 5 \
  --out ../results/rq2_multiprobe2_raw.csv
