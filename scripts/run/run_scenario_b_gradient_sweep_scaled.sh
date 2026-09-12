#!/bin/bash
# Scaled-up Scenario B graduated-contention sweep (2026-09-12, second pass).
#
# The pilot (n=60/condition, 5 conditions: 0/2/4/6 pool + 6-queueonly) established
# the mechanism (cache-slot competition, not queueing delay) and a graded
# dose-response. This run makes it statistically solid: n=150/condition, and adds
# three more worker-count points (1/3/5) for a fuller dose-response curve, per the
# user's "n>=100-200 ... and maybe a rate dimension" request -- interpreted as
# finer worker-count granularity rather than a new requests/sec knob in
# noise_generator.py, since worker-count is this paper's established contention
# proxy throughout (§4.5, §5.5).
set -e
source ~/venvs/sidechannel/bin/activate
cd /home/researcher/native_test/scripts

OUT=/home/researcher/native_test/results/scenario_b_gradient_scaled
mkdir -p "$OUT"
MANIFEST="$OUT/manifest.log"
: > "$MANIFEST"

ATTACKER="law track_0 track_1 track_2 track_3 track_4 track_5 junk_0_r8"
VICTIM="med"
NOISE_POOL="noise_0 noise_1 noise_2 noise_3 noise_4 noise_5 noise_6 noise_7"
BASE_MODEL="meta-llama/Llama-3.2-1B"
TRIALS=150

log() { echo "[$(date +%s)] $*" | tee -a "$MANIFEST"; }

canary() {
    local tag=$1
    python3 - "$tag" "$MANIFEST" <<'PYEOF'
import sys, time, requests
tag, manifest_path = sys.argv[1], sys.argv[2]
s = requests.Session()
lats = []
for _ in range(8):
    t0 = time.perf_counter_ns()
    s.post("http://localhost:8000/v1/completions",
           json={"model": "law", "prompt": "The", "max_tokens": 1, "temperature": 0}, timeout=30)
    lats.append((time.perf_counter_ns() - t0) / 1e6)
line = f"[{int(time.time())}] CANARY {tag}: lats_ms={['%.2f'%x for x in lats]} mean={sum(lats)/len(lats):.2f}"
print(line)
with open(manifest_path, "a") as f:
    f.write(line + "\n")
PYEOF
}

run_condition() {
    local name=$1
    local workers=$2
    local mode=$3  # "pool" or "queueonly"
    local noise_pid=""

    log "=== condition=$name workers=$workers mode=$mode START ==="

    if [ "$workers" -gt 0 ]; then
        if [ "$mode" = "queueonly" ]; then
            adapters="$BASE_MODEL"
        else
            adapters="$NOISE_POOL"
        fi
        cd /home/researcher/native_test/harness
        nohup python3 noise_generator.py --adapters $adapters \
            --workers "$workers" --duration-s 3600 --min-tokens 1 --max-tokens 64 \
            --min-words 3 --max-words 40 > "$OUT/noise_${name}.log" 2>&1 &
        noise_pid=$!
        disown
        cd /home/researcher/native_test/scripts
        sleep 3
        log "noise generator pid=$noise_pid started for $name"
    fi

    python3 scenario_b_self_eviction.py \
        --base-url http://localhost:8000 \
        --attacker-adapters $ATTACKER \
        --victim-adapter $VICTIM \
        --trials $TRIALS \
        --threshold-ms 60 \
        --activity-gap-s 0.2 \
        --out "$OUT/${name}_raw.csv" 2>&1 | tee "$OUT/${name}_stdout.log" | tail -5

    if [ -n "$noise_pid" ]; then
        kill "$noise_pid" 2>/dev/null || true
        wait "$noise_pid" 2>/dev/null || true
        log "noise generator pid=$noise_pid stopped for $name"
    fi

    log "=== condition=$name workers=$workers mode=$mode END ==="
    sleep 5
}

log "SCALED SWEEP START"
canary "pre-sweep"

# Shuffled order across 8 conditions (manual, decorrelates level from session time)
run_condition "w3" 3 "pool"
run_condition "w0" 0 "pool"
run_condition "w6_queueonly" 6 "queueonly"
run_condition "w1" 1 "pool"
run_condition "w5" 5 "pool"
run_condition "w2" 2 "pool"
run_condition "w6" 6 "pool"
run_condition "w4" 4 "pool"

canary "post-sweep"
log "SCALED SWEEP DONE"
