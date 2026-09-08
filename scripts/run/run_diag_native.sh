#!/bin/bash
pkill -9 -f constant_time_proxy.py 2>/dev/null
sleep 1
source ~/venvs/sidechannel/bin/activate
cd /home/researcher/native_test/harness
nohup python3 constant_time_proxy.py --port 8001 --upstream http://localhost:8000 --t-max-ms 150 \
  --diag-log ../results/proxy_diag.csv \
  > ../results/proxy_diag_stdout.log 2>&1 &
disown
sleep 1
cd ../scripts
python3 ../drivers/rq1_tier_characterization.py \
  --base-url http://localhost:8001 \
  --target med \
  --fillers junk_0_r8 junk_1_r16 junk_2_r32 junk_3_r8 junk_4_r16 junk_5_r32 \
  --max-loras 2 --max-cpu-loras 4 --trials 100 \
  --out ../results/rq1_native_diag_raw.csv
