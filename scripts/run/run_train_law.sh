#!/bin/bash
source ~/venvs/sidechannel/bin/activate
cd /mnt/e/RESEARCH/adapter-residency-sidechannel/scripts
python3 ../setup/train_adapter.py --domain law --rank 32 --epochs 12 --out ../adapters/law
