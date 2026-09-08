#!/bin/bash
source ~/venvs/sidechannel/bin/activate
cd /mnt/e/RESEARCH/adapter-residency-sidechannel/scripts
for rank in 1 16 32 64; do
  echo "=== training med_r${rank} ==="
  python3 ../setup/train_adapter.py --domain med --rank ${rank} --epochs 12 --out ../adapters/med_r${rank}
done
