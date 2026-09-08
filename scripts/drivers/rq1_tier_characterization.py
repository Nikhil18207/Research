"""RQ1 — Existence (go/no-go gate).

Characterizes latency for THREE residency states, not two:
  hot            — target adapter already resident in GPU cache
  ram_evicted    — pushed out of GPU cache, spilled to CPU-RAM cache tier
  disk_evicted   — pushed out of BOTH tiers, must reload from disk

Do not assume the hot/evicted gap is ~200ms — that number only holds for
disk_evicted. ram_evicted may be a much smaller gap. This script measures
all three so later RQs can be designed around whichever gap is reliably
large, and so we know how many filler adapters are needed to force each
state given the server's --max-loras / --max-cpu-loras settings.

Usage:
    python rq1_tier_characterization.py \
        --target med_stub --fillers junk_0_r8 junk_1_r16 junk_2_r32 junk_3_r8 junk_4_r16 junk_5_r32 \
        --max-loras 2 --max-cpu-loras 4 --trials 30 --out ../results/rq1_raw.csv
"""
import argparse
import csv
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "harness"))
from gpu_monitor import GPUMonitor  # noqa: E402
from probe import Prober  # noqa: E402


def force_hot(prober, target):
    prober.probe(target)  # warm it up
    time.sleep(0.2)
    return prober.probe(target)  # this reading = hot state


def force_ram_evicted(prober, target, fillers, max_loras):
    prober.probe(target)  # ensure it starts hot
    # push exactly enough fillers through to evict target from the GPU
    # tier while staying within the CPU-RAM tier's capacity.
    n_needed = max_loras
    for name in fillers[:n_needed]:
        prober.probe(name)
    return prober.probe(target)


def force_disk_evicted(prober, target, fillers, max_cpu_loras):
    prober.probe(target)  # ensure it starts hot
    # push enough fillers through to overflow BOTH tiers.
    n_needed = max_cpu_loras + 1
    for name in (fillers * ((n_needed // len(fillers)) + 1))[:n_needed]:
        prober.probe(name)
    return prober.probe(target)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", default="http://localhost:8000")
    ap.add_argument("--target", required=True, help="adapter name to characterize")
    ap.add_argument("--fillers", nargs="+", required=True, help="adapter names used as eviction pressure")
    ap.add_argument("--max-loras", type=int, required=True, help="server's --max-loras value")
    ap.add_argument("--max-cpu-loras", type=int, required=True, help="server's --max-cpu-loras value")
    ap.add_argument("--trials", type=int, default=30)
    ap.add_argument("--out", default="../results/rq1_raw.csv")
    args = ap.parse_args()

    gpu = GPUMonitor()
    prober = Prober(base_url=args.base_url, gpu_monitor=gpu)

    rows = []
    for trial in range(args.trials):
        for state_name, fn in [
            ("hot", lambda: force_hot(prober, args.target)),
            ("ram_evicted", lambda: force_ram_evicted(prober, args.target, args.fillers, args.max_loras)),
            ("disk_evicted", lambda: force_disk_evicted(prober, args.target, args.fillers, args.max_cpu_loras)),
        ]:
            result = fn()
            result["trial"] = trial
            result["state"] = state_name
            rows.append(result)
            print(f"trial={trial:3d} state={state_name:12s} latency_ms={result['latency_ms']:8.2f} "
                  f"gpu_temp={result.get('gpu_gpu_temp_c', '?')}")

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=sorted({k for r in rows for k in r}))
        writer.writeheader()
        writer.writerows(rows)

    print(f"\nWrote {len(rows)} rows to {args.out}")
    gpu.close()


if __name__ == "__main__":
    main()
