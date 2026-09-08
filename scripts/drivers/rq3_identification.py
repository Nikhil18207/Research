"""RQ3 — Identification (headline result).

Evict BOTH target adapters, then probe each independently in a burst.
The pattern of fast/slow across the burst names which tenant was active:

    probe_a  probe_b  conclusion
    fast     slow     A was active
    slow     fast     B was active
    fast     fast     both were active
    slow     slow     neither was active

Ground truth (which of A/B was "active") is experimenter-controlled via a
hidden reload call, exactly as in RQ2 -- the detector only ever sees the
attacker's own burst-probe latencies, never the hidden ground-truth calls.

KNOWN TRAP (see PROJECT.md RQ3 section): with --max-loras 2, probing A
then B keeps both resident simultaneously (2 slots, 2 adapters) so a
single burst does not self-evict. But the burst ORDER matters for a
subtlety: A is probed first (still reflecting pre-burst residency), then
B is probed second (whose probe is itself a residency-changing event for
the NEXT round). We log full order + timestamps, not just latency values,
so this is analyzable rather than hidden.

Usage:
    python rq3_identification.py --adapter-a junk_0_r8 --adapter-b junk_3_r8 \
        --fillers junk_1_r16 junk_2_r32 junk_4_r16 junk_5_r32 \
        --max-cpu-loras 4 --trials 40 --out ../results/rq3_raw.csv
"""
import argparse
import csv
import os
import random
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "harness"))
from gpu_monitor import GPUMonitor  # noqa: E402
from probe import Prober  # noqa: E402


def evict_both(prober, adapter_a, adapter_b, fillers, max_cpu_loras):
    """Push BOTH targets out of both cache tiers before each trial."""
    prober.probe(adapter_a)
    prober.probe(adapter_b)
    n_needed = max_cpu_loras + 1
    cycle = (fillers * ((n_needed // len(fillers)) + 1))[:n_needed]
    for name in cycle:
        prober.probe(name)
    # second pass ensures BOTH a and b (not just whichever was least-recent)
    # actually got pushed past the CPU tier too
    for name in cycle:
        prober.probe(name)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", default="http://localhost:8000")
    ap.add_argument("--adapter-a", required=True)
    ap.add_argument("--adapter-b", required=True)
    ap.add_argument("--fillers", nargs="+", required=True)
    ap.add_argument("--max-cpu-loras", type=int, required=True)
    ap.add_argument("--trials", type=int, default=40)
    ap.add_argument("--threshold-ms", type=float, default=60.0)
    ap.add_argument("--activity-gap-s", type=float, default=0.3)
    ap.add_argument("--out", default="../results/rq3_raw.csv")
    args = ap.parse_args()

    gpu = GPUMonitor()
    prober = Prober(base_url=args.base_url, gpu_monitor=gpu)

    labels = ["A", "B", "both", "neither"]
    rows = []
    for trial in range(args.trials):
        ground_truth = labels[trial % len(labels)]  # balanced across 4 classes

        evict_both(prober, args.adapter_a, args.adapter_b, args.fillers, args.max_cpu_loras)

        if ground_truth in ("A", "both"):
            prober.probe(args.adapter_a)  # hidden victim-A activity
        if ground_truth in ("B", "both"):
            prober.probe(args.adapter_b)  # hidden victim-B activity
        time.sleep(args.activity_gap_s)

        # attacker's ONLY signal: burst-probe both, in order, with timestamps
        result_a = prober.probe(args.adapter_a)
        result_b = prober.probe(args.adapter_b)

        pred_a_active = result_a["latency_ms"] < args.threshold_ms
        pred_b_active = result_b["latency_ms"] < args.threshold_ms
        if pred_a_active and pred_b_active:
            predicted = "both"
        elif pred_a_active:
            predicted = "A"
        elif pred_b_active:
            predicted = "B"
        else:
            predicted = "neither"

        correct = predicted == ground_truth
        row = {
            "trial": trial,
            "ground_truth": ground_truth,
            "predicted": predicted,
            "correct": correct,
            "latency_a_ms": result_a["latency_ms"],
            "latency_b_ms": result_b["latency_ms"],
            "wall_timestamp_a_ns": result_a["wall_timestamp_ns"],
            "wall_timestamp_b_ns": result_b["wall_timestamp_ns"],
            "gpu_temp_c": result_a.get("gpu_gpu_temp_c"),
        }
        rows.append(row)
        print(f"trial={trial:3d} truth={ground_truth:8s} pred={predicted:8s} "
              f"{'OK ' if correct else 'ERR'} lat_a={result_a['latency_ms']:7.2f} lat_b={result_b['latency_ms']:7.2f}")

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=sorted({k for r in rows for k in r}))
        writer.writeheader()
        writer.writerows(rows)

    n_correct = sum(r["correct"] for r in rows)
    print(f"\nAccuracy: {n_correct}/{len(rows)} = {n_correct/len(rows)*100:.1f}%")
    print(f"Wrote {len(rows)} rows to {args.out}")
    gpu.close()


if __name__ == "__main__":
    main()
