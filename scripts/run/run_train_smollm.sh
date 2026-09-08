#!/bin/bash
source ~/venvs/sidechannel/bin/activate
cd /mnt/e/RESEARCH/adapter-residency-sidechannel/scripts
python3 ../setup/train_adapter.py --base HuggingFaceTB/SmolLM2-1.7B --domain med --rank 8 --epochs 12 --out ../adapters/smol_med
python3 ../setup/train_adapter.py --base HuggingFaceTB/SmolLM2-1.7B --domain law --rank 32 --epochs 12 --out ../adapters/smol_law
python3 ../setup/make_junk_adapters.py --base HuggingFaceTB/SmolLM2-1.7B --n 4 --out ../adapters/smol_junk --ranks 8 16 8 16
