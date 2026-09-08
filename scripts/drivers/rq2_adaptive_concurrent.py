"""RQ2 fix v2: TRUE-concurrent paired-baseline detection.

rq2_adaptive.py's sequential canary-then-target pairing failed under
severe load: waiting for the canary's response before firing the target
probe means hundreds of ms pass between them on a saturated server, so
they no longer share the same queue state -- the pairing assumption
(shared noise cancels in the difference) requires near-simultaneity, not
just temporal proximity.

Fix: fire canary and target requests CONCURRENTLY (same wall-clock
instant, via a thread pool) so they experience the same queue depth /
scheduling window, then diff their individual completion latencies.
"""
import argparse
import csv
import os
import statistics
import sys
import time
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "harness"))
from gpu_monitor import GPUMonitor  # noqa: E402
from probe import Prober  # noqa: E402


def prime_evict(prober, target, fillers, max_cpu_loras):
    prober.probe(target)
    n_needed = max_cpu_loras + 1
    for name in (fillers * ((n_needed // len(fillers)) + 1))[:n_needed]:
        prober.probe(name)


def concurrent_paired_probe(prober, canary, target):
    with ThreadPoolExecutor(max_workers=2) as ex:
        f_canary = ex.submit(prober.probe, canary)
        f_target = ex.submit(prober.probe, target)
        canary_res = f_canary.result()
        target_res = f_target.result()
    return target_res["latency_ms"] - canary_res["latency_ms"], target_res["latency_ms"], canary_res["latency_ms"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", default="http://localhost:8000")
    ap.add_argument("--target", required=True)
    ap.add_argument("--canary", required=True)
    ap.add_argument("--fillers", nargs="+", required=True)
    ap.add_argument("--max-cpu-loras", type=int, required=True)
    ap.add_argument("--trials", type=int, default=20)
    ap.add_argument("--k", type=int, default=3)
    ap.add_argument("--diff-threshold-ms", type=float, default=25.0)
    ap.add_argument("--activity-gap-s", type=float, default=0.3)
    ap.add_argument("--out", default="../results/rq2_adaptive_concurrent_raw.csv")
    args = ap.parse_args()

    assert args.canary != args.target and args.canary not in args.fillers

    gpu = GPUMonitor()
    prober = Prober(base_url=args.base_url, gpu_monitor=gpu)
    # warm the canary once up front, then it's kept warm by the concurrent
    # probes each round (each round re-touches it, same as before)
    prober.probe(args.canary)

    rows = []
    for trial in range(args.trials):
        ground_truth = "active" if trial % 2 == 0 else "idle"
        prime_evict(prober, args.target, args.fillers, args.max_cpu_loras)

        if ground_truth == "active":
            prober.probe(args.target)
        time.sleep(args.activity_gap_s)

        diffs = []
        for k in range(args.k):
            diff, t_lat, c_lat = concurrent_paired_probe(prober, args.canary, args.target)
            diffs.append(diff)
            rows.append({
                "trial": trial, "ground_truth": ground_truth, "probe_idx": k,
                "target_latency_ms": t_lat, "canary_latency_ms": c_lat, "diff_ms": diff,
            })

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
