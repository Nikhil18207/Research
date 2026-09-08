"""RQ2 fix: adaptive (paired-baseline) detection to survive severe load.

The fixed-threshold detector collapsed to chance under severe contention
because absolute latency inflates 10-40x under queueing delay, and a
threshold calibrated on idle-GPU numbers becomes meaningless.

Fix: instead of probe_latency < THRESHOLD, pair each target probe with an
immediately-adjacent probe of a CANARY adapter that we keep warm (probed
right before, so it stays MRU/resident). Classify on
    diff = target_latency - canary_latency
rather than target_latency alone. Shared queueing delay hits both probes
roughly equally (they're temporally adjacent) and cancels out of the
difference; only the differential reload-cost survives.

Canary must be a DIFFERENT adapter from the target and NOT part of the
eviction filler set, so its own residency isn't disturbed by priming.
"""
import argparse
import csv
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "harness"))
from gpu_monitor import GPUMonitor  # noqa: E402
from probe import Prober  # noqa: E402


def prime_evict(prober, target, fillers, max_cpu_loras):
    prober.probe(target)
    n_needed = max_cpu_loras + 1
    for name in (fillers * ((n_needed // len(fillers)) + 1))[:n_needed]:
        prober.probe(name)


def paired_probe(prober, canary, target):
    """Probe canary (warms it / keeps it MRU) then target, back-to-back."""
    canary_lat = prober.probe(canary)["latency_ms"]
    target_lat = prober.probe(target)["latency_ms"]
    return target_lat - canary_lat, target_lat, canary_lat


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", default="http://localhost:8000")
    ap.add_argument("--target", required=True)
    ap.add_argument("--canary", required=True)
    ap.add_argument("--fillers", nargs="+", required=True)
    ap.add_argument("--max-cpu-loras", type=int, required=True)
    ap.add_argument("--trials", type=int, default=20)
    ap.add_argument("--k", type=int, default=3, help="paired probes per measurement, median-combined")
    ap.add_argument("--diff-threshold-ms", type=float, default=25.0)
    ap.add_argument("--activity-gap-s", type=float, default=0.3)
    ap.add_argument("--out", default="../results/rq2_adaptive_raw.csv")
    args = ap.parse_args()

    assert args.canary != args.target and args.canary not in args.fillers, \
        "canary must be distinct from target and not used as an eviction filler"

    gpu = GPUMonitor()
    prober = Prober(base_url=args.base_url, gpu_monitor=gpu)

    rows = []
    for trial in range(args.trials):
        ground_truth = "active" if trial % 2 == 0 else "idle"
        prime_evict(prober, args.target, args.fillers, args.max_cpu_loras)

        if ground_truth == "active":
            prober.probe(args.target)  # hidden victim reload
        time.sleep(args.activity_gap_s)

        diffs = []
        for k in range(args.k):
            diff, t_lat, c_lat = paired_probe(prober, args.canary, args.target)
            diffs.append(diff)
            rows.append({
                "trial": trial, "ground_truth": ground_truth, "probe_idx": k,
                "target_latency_ms": t_lat, "canary_latency_ms": c_lat, "diff_ms": diff,
            })

        import statistics
        med_diff = statistics.median(diffs)
        predicted = "active" if med_diff < args.diff_threshold_ms else "idle"
        correct = predicted == ground_truth
        print(f"trial={trial:3d} truth={ground_truth:6s} pred={predicted:6s} "
              f"{'OK ' if correct else 'ERR'} diffs={[round(d,1) for d in diffs]} median_diff={med_diff:.1f}")

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["trial", "ground_truth", "probe_idx",
                                                 "target_latency_ms", "canary_latency_ms", "diff_ms"])
        writer.writeheader()
        writer.writerows(rows)
    print(f"\nWrote {len(rows)} rows to {args.out}")
    gpu.close()


if __name__ == "__main__":
    main()
