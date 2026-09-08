#!/bin/bash
source ~/venvs/sidechannel/bin/activate
cd /mnt/e/RESEARCH/adapter-residency-sidechannel/harness
nohup python3 constant_time_proxy.py --port 8001 --upstream http://localhost:8000 --t-max-ms 150 \
  > ../results/proxy.log 2>&1 &
disown
sleep 1
echo LAUNCHED
