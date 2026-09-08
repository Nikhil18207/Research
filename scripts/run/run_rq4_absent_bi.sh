#!/bin/bash
source ~/venvs/sidechannel/bin/activate
cd /mnt/e/RESEARCH/adapter-residency-sidechannel/scripts
python3 ../drivers/rq4_output_invariance.py --condition absent --out ../results/rq4_absent_bi.json
