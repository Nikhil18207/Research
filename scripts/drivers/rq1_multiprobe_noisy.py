"""RQ1 robustness follow-up: does multi-probe aggregation recover the
signal that a single probe loses under concurrent contention?

For each trial/state, take K repeated probes (not just 1) and log all of
them. Post-hoc analysis (analyze_multiprobe.py) subsamples medians of
N=1,3,5,10 probes to produce an attack-cost curve: AUC vs. number of
probes spent per measurement, under the same noisy conditions as
rq1_noisy_raw.csv.
"""
import argparse
import csv
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "harness"))
from gpu_monitor import GPUMonitor  # noqa: E402
from probe import Prober  # noqa: E402


def force_hot(prober, target, k):
    prober.probe(target)
    return [prober.probe(target)["latency_ms"] for _ in range(k)]


def force_ram_evicted(prober, target, fillers, max_loras, k):
    prober.probe(target)
    for name in fillers[:max_loras]:
        prober.probe(name)
    readings = [prober.probe(target)["latency_ms"]]
    # keep re-evicting between repeated reads so each of the K probes
    # measures the SAME state, not "already reloaded by probe 1"
    for _ in range(k - 1):
        for name in fillers[:max_loras]:
            prober.probe(name)
        readings.append(prober.probe(target)["latency_ms"])
    return readings


def force_disk_evicted(prober, target, fillers, max_cpu_loras, k):
    prober.probe(target)
    n_needed = max_cpu_loras + 1
    cycle = (fillers * ((n_needed // len(fillers)) + 1))[:n_needed]
    for name in cycle:
        prober.probe(name)
    readings = [prober.probe(target)["latency_ms"]]
    for _ in range(k - 1):
        for name in cycle:
            prober.probe(name)
        readings.append(prober.probe(target)["latency_ms"])
    return readings


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", default="http://localhost:8000")
    ap.add_argument("--target", required=True)
    ap.add_argument("--fillers", nargs="+", required=True)
    ap.add_argument("--max-loras", type=int, required=True)
    ap.add_argument("--max-cpu-loras", type=int, required=True)
    ap.add_argument("--trials", type=int, default=15)
    ap.add_argument("--k", type=int, default=10, help="repeated probes per state per trial")
    ap.add_argument("--out", default="../results/rq1_multiprobe_raw.csv")
    args = ap.parse_args()

    gpu = GPUMonitor()
    prober = Prober(base_url=args.base_url, gpu_monitor=gpu)

    rows = []
    for trial in range(args.trials):
        for state_name, fn in [
            ("hot", lambda: force_hot(prober, args.target, args.k)),
            ("ram_evicted", lambda: force_ram_evicted(prober, args.target, args.fillers, args.max_loras, args.k)),
            ("disk_evicted", lambda: force_disk_evicted(prober, args.target, args.fillers, args.max_cpu_loras, args.k)),
        ]:
            readings = fn()
            for probe_idx, lat in enumerate(readings):
                rows.append({"trial": trial, "state": state_name, "probe_idx": probe_idx, "latency_ms": lat})
            print(f"trial={trial:3d} state={state_name:12s} readings={[round(x,1) for x in readings]}")

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["trial", "state", "probe_idx", "latency_ms"])
        writer.writeheader()
        writer.writerows(rows)
    print(f"\nWrote {len(rows)} rows to {args.out}")
    gpu.close()


if __name__ == "__main__":
    main()
