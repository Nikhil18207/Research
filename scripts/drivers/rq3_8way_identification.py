"""RQ3 extension: does identification scale past 4 classes?

Original RQ3 tracks 2 named adapters, 4 classes (A/B/both/neither) -- a 2-bit
alphabet. This tests 8 named, independently-tracked adapters and asks WHICH
ONE was active (an 8-way, 3-bit single-label classification), to see whether
accuracy holds and how attacker probe cost scales as the tracked set grows
from 2 to 8 (2 probes/trial -> 8 probes/trial).

A single pass through >= max_cpu_loras+1 DISTINCT filler adapters (none of
them among the tracked 8) is sufficient to guarantee full eviction of all
8 tracked adapters regardless of their prior LRU position -- with capacity
C and N>C distinct new touches, the cache holds only the C most recent of
those N touches, so anything untouched during the pass (all 8 tracked
adapters here) is necessarily older than every surviving entry and has been
evicted. This halves the request cost relative to the original 2-adapter
protocol's double-pass safety margin.

Usage:
    python rq3_8way_identification.py --adapters med law track_0 ... (8 names) \
        --fillers junk_0_r8 ... --max-cpu-loras 64 --trials 80 \
        --out ../results/rq3_8way_raw.csv
"""
import argparse
import csv
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "harness"))
from gpu_monitor import GPUMonitor  # noqa: E402
from probe import Prober  # noqa: E402


def evict_all(prober, tracked, fillers, max_cpu_loras):
    for a in tracked:
        pass  # do NOT probe tracked adapters here -- would just reset their own LRU position
    n_needed = max_cpu_loras + 1
    cycle = (fillers * ((n_needed // len(fillers)) + 1))[:n_needed]
    for name in cycle:
        prober.probe(name)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", default="http://localhost:8000")
    ap.add_argument("--adapters", nargs="+", required=True, help="the 8 tracked adapter names")
    ap.add_argument("--fillers", nargs="+", required=True, help="filler adapters, none in --adapters")
    ap.add_argument("--max-cpu-loras", type=int, required=True)
    ap.add_argument("--trials", type=int, default=80)
    ap.add_argument("--activity-gap-s", type=float, default=0.3)
    ap.add_argument("--out", default="../results/rq3_8way_raw.csv")
    args = ap.parse_args()

    assert not (set(args.adapters) & set(args.fillers)), "tracked adapters must not appear in the filler pool"
    n = len(args.adapters)

    gpu = GPUMonitor()
    prober = Prober(base_url=args.base_url, gpu_monitor=gpu)

    rows = []
    for trial in range(args.trials):
        ground_truth_idx = trial % n
        ground_truth = args.adapters[ground_truth_idx]

        evict_all(prober, args.adapters, args.fillers, args.max_cpu_loras)

        prober.probe(ground_truth)  # hidden victim activity -- never seen by the detector
        time.sleep(args.activity_gap_s)

        # attacker's ONLY signal: burst-probe all 8, in fixed order
        latencies = {}
        for a in args.adapters:
            latencies[a] = prober.probe(a)["latency_ms"]

        predicted = min(latencies, key=latencies.get)  # fastest = most recently active
        correct = predicted == ground_truth

        row = {"trial": trial, "ground_truth": ground_truth, "predicted": predicted, "correct": correct}
        for a in args.adapters:
            row[f"latency_{a}_ms"] = latencies[a]
        rows.append(row)
        print(f"trial={trial:3d} truth={ground_truth:10s} pred={predicted:10s} "
              f"{'OK ' if correct else 'ERR'} latencies={ {k: round(v,1) for k,v in latencies.items()} }")

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    n_correct = sum(r["correct"] for r in rows)
    print(f"\n{n}-way accuracy: {n_correct}/{len(rows)} = {n_correct/len(rows)*100:.1f}% (chance = {100/n:.1f}%)")
    print(f"Wrote {len(rows)} rows to {args.out}")
    gpu.close()


if __name__ == "__main__":
    main()
