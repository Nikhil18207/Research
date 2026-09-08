"""RQ3 fix: adaptive (paired-baseline) 4-class identification under severe load.

Same fix as rq2_adaptive.py, applied to both A and B independently:
diff_A = latency_A - canary_latency (canary probed immediately before A)
diff_B = latency_B - canary_latency (canary probed immediately before B)
classify each as active/evicted via diff vs threshold, then combine into
the 4-way A/B/both/neither label as before.
"""
import argparse
import csv
import os
import statistics
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "harness"))
from gpu_monitor import GPUMonitor  # noqa: E402
from probe import Prober  # noqa: E402


def evict_both(prober, adapter_a, adapter_b, fillers, max_cpu_loras):
    prober.probe(adapter_a)
    prober.probe(adapter_b)
    n_needed = max_cpu_loras + 1
    cycle = (fillers * ((n_needed // len(fillers)) + 1))[:n_needed]
    for name in cycle:
        prober.probe(name)
    for name in cycle:
        prober.probe(name)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", default="http://localhost:8000")
    ap.add_argument("--adapter-a", required=True)
    ap.add_argument("--adapter-b", required=True)
    ap.add_argument("--canary", required=True)
    ap.add_argument("--fillers", nargs="+", required=True)
    ap.add_argument("--max-cpu-loras", type=int, required=True)
    ap.add_argument("--trials", type=int, default=20)
    ap.add_argument("--k", type=int, default=3)
    ap.add_argument("--diff-threshold-ms", type=float, default=25.0)
    ap.add_argument("--activity-gap-s", type=float, default=0.3)
    ap.add_argument("--out", default="../results/rq3_adaptive_raw.csv")
    args = ap.parse_args()

    assert args.canary not in (args.adapter_a, args.adapter_b) and args.canary not in args.fillers

    gpu = GPUMonitor()
    prober = Prober(base_url=args.base_url, gpu_monitor=gpu)

    labels = ["A", "B", "both", "neither"]
    rows = []
    for trial in range(args.trials):
        ground_truth = labels[trial % len(labels)]
        evict_both(prober, args.adapter_a, args.adapter_b, args.fillers, args.max_cpu_loras)

        if ground_truth in ("A", "both"):
            prober.probe(args.adapter_a)
        if ground_truth in ("B", "both"):
            prober.probe(args.adapter_b)
        time.sleep(args.activity_gap_s)

        diffs_a, diffs_b = [], []
        for k in range(args.k):
            c1 = prober.probe(args.canary)["latency_ms"]
            a_lat = prober.probe(args.adapter_a)["latency_ms"]
            c2 = prober.probe(args.canary)["latency_ms"]
            b_lat = prober.probe(args.adapter_b)["latency_ms"]
            diff_a = a_lat - c1
            diff_b = b_lat - c2
            diffs_a.append(diff_a)
            diffs_b.append(diff_b)
            rows.append({
                "trial": trial, "ground_truth": ground_truth, "probe_idx": k,
                "latency_a_ms": a_lat, "latency_b_ms": b_lat,
                "canary1_ms": c1, "canary2_ms": c2, "diff_a_ms": diff_a, "diff_b_ms": diff_b,
            })

        med_diff_a = statistics.median(diffs_a)
        med_diff_b = statistics.median(diffs_b)
        a_active = med_diff_a < args.diff_threshold_ms
        b_active = med_diff_b < args.diff_threshold_ms
        if a_active and b_active:
            predicted = "both"
        elif a_active:
            predicted = "A"
        elif b_active:
            predicted = "B"
        else:
            predicted = "neither"
        correct = predicted == ground_truth
        print(f"trial={trial:3d} truth={ground_truth:8s} pred={predicted:8s} "
              f"{'OK ' if correct else 'ERR'} med_diff_a={med_diff_a:7.1f} med_diff_b={med_diff_b:7.1f}")

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["trial", "ground_truth", "probe_idx", "latency_a_ms",
                                                 "latency_b_ms", "canary1_ms", "canary2_ms", "diff_a_ms", "diff_b_ms"])
        writer.writeheader()
        writer.writerows(rows)
    print(f"\nWrote {len(rows)} rows to {args.out}")
    gpu.close()


if __name__ == "__main__":
    main()
