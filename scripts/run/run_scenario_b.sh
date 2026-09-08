#!/bin/bash
source ~/venvs/sidechannel/bin/activate
cd /mnt/e/RESEARCH/adapter-residency-sidechannel/scripts
python3 ../drivers/scenario_b_self_eviction.py \
  --attacker-adapters junk_0_r8 junk_1_r16 \
  --victim-adapter med \
  --trials 40 \
  --threshold-ms 60 \
  --out ../results/scenario_b_raw.csv
