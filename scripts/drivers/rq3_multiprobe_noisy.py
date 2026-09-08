"""RQ3 robustness follow-up: does median-of-K burst-probing recover
4-class identification accuracy under noise?

Per trial: evict both -> flip hidden ground truth -> K repeated
burst-probes of (A, B) without re-priming between repeats (same
reasoning as rq2_multiprobe_noisy: the post-event state is static until
the next eviction, so repeated reads all measure the same state).
"""
import argparse
import csv
import os
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
    ap.add_argument("--fillers", nargs="+", required=True)
    ap.add_argument("--max-cpu-loras", type=int, required=True)
    ap.add_argument("--trials", type=int, default=20)
    ap.add_argument("--k", type=int, default=5)
    ap.add_argument("--activity-gap-s", type=float, default=0.3)
    ap.add_argument("--out", default="../results/rq3_multiprobe_raw.csv")
    args = ap.parse_args()

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

        for k in range(args.k):
            ra = prober.probe(args.adapter_a)
            rb = prober.probe(args.adapter_b)
            rows.append({
                "trial": trial, "ground_truth": ground_truth, "probe_idx": k,
                "latency_a_ms": ra["latency_ms"], "latency_b_ms": rb["latency_ms"],
            })
        print(f"trial={trial:3d} truth={ground_truth:8s} done ({args.k} repeats)")

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["trial", "ground_truth", "probe_idx", "latency_a_ms", "latency_b_ms"])
        writer.writeheader()
        writer.writerows(rows)
    print(f"\nWrote {len(rows)} rows to {args.out}")
    gpu.close()


if __name__ == "__main__":
    main()
