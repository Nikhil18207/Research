"""Scenario B, adaptive detector: concurrent-canary pairing + a rolling/windowed
baseline, evaluated head-to-head against the fixed-threshold-on-raw-latency
baseline from the same trials.

Motivation (PROJECT.md "Adaptive-Threshold Fix Attempt", 2026-09-03): the
original RQ2/RQ3 adaptive-threshold work found that (a) concurrent (not
sequential) canary pairing cancels shared queueing delay, but (b) a single
global threshold still fails when the ambient load level drifts across a run.
This driver combines both fixes for Scenario B specifically, which the
original work never got to: fire the target probe and a canary probe as
truly simultaneous requests (not sequential), and classify against a LOCAL
rolling baseline (median + MAD of recent diffs) instead of one global cutoff.

Design constraint this creates: Scenario B's usual attacker set is exactly
`max_loras` adapters (round-robin, no third adapter competing for slots -- see
scenario_b_self_eviction.py). Adding a dedicated, separately-probed canary
needs an (max_loras + 1)-th slot, which would reintroduce exactly the kind of
third-adapter competition Scenario B's core design avoids. Here we instead use
`max_loras - 1` round-robin adapters + 1 dedicated canary, so the resident set
size still equals max_loras (zero headroom preserved) -- a deliberate, small
change from the baseline experiment's exact adapter count, documented here
rather than silently assumed equivalent.

Honest limitation this does NOT resolve: unlike the original adaptive-threshold
work's canary (excluded from all contention), this canary shares the SAME
bounded max_loras/max_cpu_loras tiers as the victim and noise pool -- it is not
guaranteed evict-immune under Scenario B's contention, since every adapter here
draws from one shared cache. The concurrent-pairing benefit (shared queueing
delay cancels) should still hold; the "always-resident reference point"
assumption from the original design is weaker here and is evaluated, not
assumed.
"""
import argparse
import csv
import os
import sys
import time
from collections import deque
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "harness"))
from gpu_monitor import GPUMonitor  # noqa: E402
from probe import Prober  # noqa: E402


def median(vals):
    s = sorted(vals)
    n = len(s)
    if n == 0:
        return None
    mid = n // 2
    return s[mid] if n % 2 else (s[mid - 1] + s[mid]) / 2


def mad(vals, med):
    return median([abs(v - med) for v in vals])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", default="http://localhost:8000")
    ap.add_argument("--attacker-adapters", nargs="+", required=True,
                     help="round-robin adapters the attacker owns; count should equal max_loras - 1")
    ap.add_argument("--canary-adapter", required=True,
                     help="dedicated adapter probed concurrently with the target every trial, "
                          "never part of the round-robin, never the victim")
    ap.add_argument("--victim-adapter", required=True)
    ap.add_argument("--trials", type=int, default=150)
    ap.add_argument("--window", type=int, default=15, help="rolling window size (in trials) for the adaptive baseline")
    ap.add_argument("--k", type=float, default=1.5, help="margin multiplier on rolling MAD")
    ap.add_argument("--activity-gap-s", type=float, default=0.2)
    ap.add_argument("--out", default="../results/scenario_b_adaptive_raw.csv")
    args = ap.parse_args()

    assert args.victim_adapter not in args.attacker_adapters
    assert args.canary_adapter not in args.attacker_adapters
    assert args.canary_adapter != args.victim_adapter

    gpu = GPUMonitor()
    prober = Prober(base_url=args.base_url, gpu_monitor=gpu)
    executor = ThreadPoolExecutor(max_workers=2)

    diff_window = deque(maxlen=args.window)
    rows = []

    for trial in range(args.trials):
        ground_truth = "active" if trial % 2 == 0 else "idle"

        for a in args.attacker_adapters:
            prober.probe(a)
        lru_candidate = args.attacker_adapters[0]

        # keep the canary itself resident/warm going into this trial's pair
        prober.probe(args.canary_adapter)

        if ground_truth == "active":
            prober.probe(args.victim_adapter)  # hidden victim activity
        time.sleep(args.activity_gap_s)

        # concurrent (not sequential) paired dispatch -- both fire at once,
        # so shared queueing delay at this instant affects both similarly.
        fut_target = executor.submit(prober.probe, lru_candidate)
        fut_canary = executor.submit(prober.probe, args.canary_adapter)
        target_result = fut_target.result()
        canary_result = fut_canary.result()

        target_lat = target_result["latency_ms"]
        canary_lat = canary_result["latency_ms"]
        diff = target_lat - canary_lat

        # rolling baseline computed from PRIOR trials only (no leakage from current diff)
        if len(diff_window) >= 3:
            baseline = median(list(diff_window))
            spread = mad(list(diff_window), baseline)
            predicted_adaptive = "active" if diff > baseline + args.k * spread else "idle"
        else:
            baseline, spread = None, None
            predicted_adaptive = "idle"  # insufficient history -> default

        diff_window.append(diff)
        correct_adaptive = predicted_adaptive == ground_truth

        rows.append({
            "trial": trial,
            "ground_truth": ground_truth,
            "target_latency_ms": target_lat,
            "canary_latency_ms": canary_lat,
            "diff_ms": diff,
            "rolling_baseline_ms": baseline,
            "rolling_mad_ms": spread,
            "predicted_adaptive": predicted_adaptive,
            "correct_adaptive": correct_adaptive,
        })
        print(f"trial={trial:3d} truth={ground_truth:6s} target={target_lat:7.2f} canary={canary_lat:7.2f} "
              f"diff={diff:7.2f} baseline={baseline if baseline is None else round(baseline,2)} "
              f"pred_adaptive={predicted_adaptive:6s} {'OK' if correct_adaptive else 'ERR'}")

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    n_correct = sum(r["correct_adaptive"] for r in rows)
    print(f"\nAdaptive (rolling-baseline) accuracy: {n_correct}/{len(rows)} = {n_correct/len(rows)*100:.1f}%")
    print(f"Wrote {len(rows)} rows to {args.out}")
    gpu.close()
    executor.shutdown()


if __name__ == "__main__":
    main()
