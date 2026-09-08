#!/bin/bash
pkill -9 -f constant_time_proxy.py 2>/dev/null
sleep 1
source ~/venvs/sidechannel/bin/activate
cd /mnt/e/RESEARCH/adapter-residency-sidechannel/harness
nohup python3 constant_time_proxy.py --port 8001 --upstream http://localhost:8000 --t-max-ms 300 \
  > ../results/proxy_300.log 2>&1 &
disown
sleep 1
echo LAUNCHED
