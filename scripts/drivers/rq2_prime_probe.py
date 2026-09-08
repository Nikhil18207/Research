"""RQ2 — Inducibility (prime + probe).

Ground truth (victim active/idle) is experimenter-controlled and simulated
via a SEPARATE call that is never given to the classifier — only the
attacker's own probe latency is used for detection, matching the real
threat model (attacker only ever times its own requests).

Per trial:
  1. ensure target starts hot
  2. PRIME: evict target via disk-eviction pressure (the reliable tier per RQ1)
  3. flip ground truth: active | idle
  4. if active: simulate victim's own request reloading the target
     (latency NOT used by the detector — this is the hidden ground truth)
  5. brief wait (gap between victim activity and attacker's probe)
  6. PROBE: attacker times ITS OWN request to target -> this is the signal
  7. classify: latency < threshold => predict "active", else "idle"

Usage:
    python rq2_prime_probe.py --target junk_0_r8 \
        --fillers junk_1_r16 junk_2_r32 junk_3_r8 junk_4_r16 junk_5_r32 \
        --max-cpu-loras 4 --trials 40 --threshold-ms 50 --out ../results/rq2_raw.csv
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
    """Push target out of BOTH cache tiers (disk-eviction, the reliable signal per RQ1)."""
    prober.probe(target)  # ensure it starts hot before eviction pressure
    n_needed = max_cpu_loras + 1
    for name in (fillers * ((n_needed // len(fillers)) + 1))[:n_needed]:
        prober.probe(name)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", default="http://localhost:8000")
    ap.add_argument("--target", required=True)
    ap.add_argument("--fillers", nargs="+", required=True)
    ap.add_argument("--max-cpu-loras", type=int, required=True)
    ap.add_argument("--trials", type=int, default=40)
    ap.add_argument("--threshold-ms", type=float, default=50.0,
                     help="latency below this = predict 'active' (adapter reloaded)")
    ap.add_argument("--activity-gap-s", type=float, default=0.3,
                     help="wait between simulated victim activity and attacker's probe")
    ap.add_argument("--out", default="../results/rq2_raw.csv")
    args = ap.parse_args()

    gpu = GPUMonitor()
    prober = Prober(base_url=args.base_url, gpu_monitor=gpu)

    rows = []
    for trial in range(args.trials):
        ground_truth = "active" if trial % 2 == 0 else "idle"  # balanced, not coin-flipped

        prime_evict(prober, args.target, args.fillers, args.max_cpu_loras)

        if ground_truth == "active":
            hidden = prober.probe(args.target)  # victim's own request -- NOT given to detector
            time.sleep(args.activity_gap_s)
        else:
            hidden = None
            time.sleep(args.activity_gap_s)

        probe_result = prober.probe(args.target)  # attacker's ONLY signal
        predicted = "active" if probe_result["latency_ms"] < args.threshold_ms else "idle"
        correct = predicted == ground_truth

        row = {
            "trial": trial,
            "ground_truth": ground_truth,
            "predicted": predicted,
            "correct": correct,
            "probe_latency_ms": probe_result["latency_ms"],
            "hidden_activity_latency_ms": hidden["latency_ms"] if hidden else None,
            "gpu_temp_c": probe_result.get("gpu_gpu_temp_c"),
        }
        rows.append(row)
        print(f"trial={trial:3d} truth={ground_truth:6s} pred={predicted:6s} "
              f"{'OK ' if correct else 'ERR'} latency={probe_result['latency_ms']:7.2f}ms")

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
