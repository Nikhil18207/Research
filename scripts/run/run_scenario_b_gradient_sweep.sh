#!/bin/bash
# Scenario B graduated-contention sweep + queueing-vs-cache-pressure control.
#
# Design (per user-approved plan): the existing n=200 6-worker contention
# result (scenario_b_native_tight_contention_n200_raw.csv) already showed the
# signal is not established at that one severe point. This sweep asks two new
# questions that single point cannot answer:
#   1. Is there a contention LEVEL below "severe" where the signal still holds
#      (graduated 0/2/4/6-worker sweep), rather than only a pass/fail at one
#      point?
#   2. Is the collapse caused by raw queueing delay, or by the noise pool
#      ALSO competing for the same shared max_loras=8 GPU cache slots (a
#      hypothesis PROJECT.md raised but never isolated)? The w6_queueonly
#      condition fires the same request volume at the BASE MODEL directly
#      (no LoRA adapter at all -> zero adapter-cache-slot competition,
#      pure scheduler/queueing concurrency) to isolate this.
#
# Condition order is shuffled (fixed seed) rather than run 0->2->4->6 in
# sequence, per the project's own established lesson (rq_volume_sweep.py's
# discarded blocked-order pilot) that monotonic level-vs-session-order is a
# real confound risk. A canary probe (5x on `law`) brackets the whole sweep
# to make session-length drift a checked number, not an assumption.
set -e
source ~/venvs/sidechannel/bin/activate
cd /home/researcher/native_test/scripts

OUT=/home/researcher/native_test/results/scenario_b_gradient
mkdir -p "$OUT"
MANIFEST="$OUT/manifest.log"
: > "$MANIFEST"

ATTACKER="law track_0 track_1 track_2 track_3 track_4 track_5 junk_0_r8"
VICTIM="med"
NOISE_POOL="noise_0 noise_1 noise_2 noise_3 noise_4 noise_5 noise_6 noise_7"
BASE_MODEL="meta-llama/Llama-3.2-1B"
TRIALS=60

log() { echo "[$(date +%s)] $*" | tee -a "$MANIFEST"; }

canary() {
    local tag=$1
    python3 - "$tag" "$MANIFEST" <<'PYEOF'
import sys, time, requests
tag, manifest_path = sys.argv[1], sys.argv[2]
s = requests.Session()
lats = []
for _ in range(5):
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
            --workers "$workers" --duration-s 1800 --min-tokens 1 --max-tokens 64 \
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
    sleep 5  # cooldown before next condition
}

log "SWEEP START"
canary "pre-sweep"

# Shuffled order (seed=42): w4, w0, w6_queueonly, w6, w2 -- decorrelates
# contention level from session position.
run_condition "w4" 4 "pool"
run_condition "w0" 0 "pool"
run_condition "w6_queueonly" 6 "queueonly"
run_condition "w6" 6 "pool"
run_condition "w2" 2 "pool"

canary "post-sweep"
log "SWEEP DONE"
