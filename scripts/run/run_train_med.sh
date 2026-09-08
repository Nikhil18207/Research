#!/bin/bash
source ~/venvs/sidechannel/bin/activate
cd /mnt/e/RESEARCH/adapter-residency-sidechannel/scripts
python3 ../setup/train_adapter.py --domain med --rank 8 --epochs 12 --out ../adapters/med
