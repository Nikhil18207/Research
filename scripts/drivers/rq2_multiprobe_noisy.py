"""RQ2 robustness follow-up: does median-of-K probing recover detection
accuracy under noise, the same way it did for RQ1?

Per trial: prime (evict), flip hidden ground truth, then take K repeated
probes of the target WITHOUT re-priming between them (unlike RQ1's
multiprobe, which re-evicts between reads to keep measuring a static
state -- here the "active" state is a one-time event: the victim reloaded
it once, and it stays hot until evicted again, so repeated probes right
after the hidden event all measure the SAME resulting state and can be
safely medianed).
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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", default="http://localhost:8000")
    ap.add_argument("--target", required=True)
    ap.add_argument("--fillers", nargs="+", required=True)
    ap.add_argument("--max-cpu-loras", type=int, required=True)
    ap.add_argument("--trials", type=int, default=20)
    ap.add_argument("--k", type=int, default=5)
    ap.add_argument("--activity-gap-s", type=float, default=0.3)
    ap.add_argument("--out", default="../results/rq2_multiprobe_raw.csv")
    args = ap.parse_args()

    gpu = GPUMonitor()
    prober = Prober(base_url=args.base_url, gpu_monitor=gpu)

    rows = []
    for trial in range(args.trials):
        ground_truth = "active" if trial % 2 == 0 else "idle"
        prime_evict(prober, args.target, args.fillers, args.max_cpu_loras)

        if ground_truth == "active":
            prober.probe(args.target)  # hidden victim reload
        time.sleep(args.activity_gap_s)

        readings = [prober.probe(args.target)["latency_ms"] for _ in range(args.k)]
        for probe_idx, lat in enumerate(readings):
            rows.append({"trial": trial, "ground_truth": ground_truth, "probe_idx": probe_idx, "latency_ms": lat})
        print(f"trial={trial:3d} truth={ground_truth:6s} readings={[round(x,1) for x in readings]}")

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["trial", "ground_truth", "probe_idx", "latency_ms"])
        writer.writeheader()
        writer.writerows(rows)
    print(f"\nWrote {len(rows)} rows to {args.out}")
    gpu.close()


if __name__ == "__main__":
    main()
