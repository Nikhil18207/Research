"""Rank-sweep: measure disk-eviction reload latency across FIVE ranks of
the SAME content domain (med), isolating rank from the content-domain
confound present in the original med(r8)-vs-law(r32) comparison.
"""
import argparse
import csv
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "harness"))
from gpu_monitor import GPUMonitor  # noqa: E402
from probe import Prober  # noqa: E402


def force_disk_evicted(prober, target, fillers, max_cpu_loras):
    prober.probe(target)
    n_needed = max_cpu_loras + 1
    cycle = (fillers * ((n_needed // len(fillers)) + 1))[:n_needed]
    for name in cycle:
        prober.probe(name)
    return prober.probe(target)["latency_ms"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", default="http://localhost:8000")
    ap.add_argument("--targets", nargs="+", required=True, help="name:rank pairs, e.g. med_r1:1 med:8")
    ap.add_argument("--fillers", nargs="+", required=True)
    ap.add_argument("--max-cpu-loras", type=int, required=True)
    ap.add_argument("--trials", type=int, default=15)
    ap.add_argument("--out", default="../results/rank_sweep_raw.csv")
    args = ap.parse_args()

    targets = [t.split(":") for t in args.targets]
    targets = [(name, int(rank)) for name, rank in targets]

    gpu = GPUMonitor()
    prober = Prober(base_url=args.base_url, gpu_monitor=gpu)

    rows = []
    for trial in range(args.trials):
        for name, rank in targets:
            lat = force_disk_evicted(prober, name, args.fillers, args.max_cpu_loras)
            rows.append({"trial": trial, "adapter": name, "rank": rank, "latency_ms": lat})
            print(f"trial={trial:3d} adapter={name:10s} rank={rank:3d} latency={lat:7.2f}ms")

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["trial", "adapter", "rank", "latency_ms"])
        writer.writeheader()
        writer.writerows(rows)
    print(f"\nWrote {len(rows)} rows to {args.out}")
    gpu.close()


if __name__ == "__main__":
    main()
