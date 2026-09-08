#!/bin/bash
source ~/venvs/sidechannel/bin/activate
cd /mnt/e/RESEARCH/adapter-residency-sidechannel/scripts
python3 ../setup/train_adapter.py --base Qwen/Qwen2.5-1.5B --domain med --rank 8 --epochs 12 --out ../adapters/qwen_med
python3 ../setup/train_adapter.py --base Qwen/Qwen2.5-1.5B --domain law --rank 32 --epochs 12 --out ../adapters/qwen_law
python3 ../setup/make_junk_adapters.py --base Qwen/Qwen2.5-1.5B --n 4 --out ../adapters/qwen_junk --ranks 8 16 8 16
