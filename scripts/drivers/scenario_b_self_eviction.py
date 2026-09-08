"""Scenario B: self-eviction-only observer.

The attacker NEVER names or probes the victim's adapter -- the one
capability Scenario A requires and Scenario B explicitly denies. The
attacker owns exactly `max_loras` adapters of its own and keeps
touching only those, round-robin. Under pure self-traffic and LRU
eviction, with #attacker-adapters == max_loras, neither of the
attacker's own adapters should ever be evicted by the attacker's own
activity alone -- there's no third adapter competing for the slots.

If a real third party (the victim, an adapter the attacker never names)
becomes active, the victim's request needs a cache slot too, evicting
whichever of the attacker's own adapters was least-recently-used --
purely as a side effect of shared-cache contention, with no naming of
the victim required. The attacker detects this by probing ONLY its own
adapter and noticing it came back unexpectedly slow.

This can, at best, tell the attacker "someone else was active" -- NOT
who. That is the whole point: this is the weaker channel the paper's
identification claim (RQ3) does NOT require, and it is the fallback
that should survive even if a platform blocks cross-tenant adapter
naming entirely.
"""
import argparse
import csv
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "harness"))
from gpu_monitor import GPUMonitor  # noqa: E402
from probe import Prober  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", default="http://localhost:8000")
    ap.add_argument("--attacker-adapters", nargs="+", required=True,
                     help="adapters the attacker OWNS and probes; count should equal --max-loras")
    ap.add_argument("--victim-adapter", required=True,
                     help="the real victim adapter -- NEVER probed by the attacker's detector, "
                          "only touched by the hidden experimenter-controlled ground-truth step")
    ap.add_argument("--trials", type=int, default=40)
    ap.add_argument("--threshold-ms", type=float, default=60.0)
    ap.add_argument("--activity-gap-s", type=float, default=0.2)
    ap.add_argument("--out", default="../results/scenario_b_raw.csv")
    args = ap.parse_args()

    assert args.victim_adapter not in args.attacker_adapters, \
        "the whole point of Scenario B is that the attacker never touches the victim's adapter"

    gpu = GPUMonitor()
    prober = Prober(base_url=args.base_url, gpu_monitor=gpu)

    rows = []
    for trial in range(args.trials):
        ground_truth = "active" if trial % 2 == 0 else "idle"

        # attacker's own round-robin baseline: touch all its own adapters in order,
        # establishing which is LRU (the first one touched) right before the window
        for a in args.attacker_adapters:
            prober.probe(a)
        lru_candidate = args.attacker_adapters[0]  # least-recently-used among attacker's own set

        if ground_truth == "active":
            prober.probe(args.victim_adapter)  # hidden victim activity -- attacker NEVER sees this call
        time.sleep(args.activity_gap_s)

        # attacker's ONLY signal: probe its OWN adapter, never the victim's name
        result = prober.probe(lru_candidate)
        predicted = "active" if result["latency_ms"] > args.threshold_ms else "idle"
        correct = predicted == ground_truth

        rows.append({
            "trial": trial, "ground_truth": ground_truth, "predicted": predicted,
            "correct": correct, "self_probe_latency_ms": result["latency_ms"],
        })
        print(f"trial={trial:3d} truth={ground_truth:6s} pred={predicted:6s} "
              f"{'OK ' if correct else 'ERR'} self_probe_latency={result['latency_ms']:7.2f}ms "
              f"(probed own adapter {lru_candidate!r}, never touched victim {args.victim_adapter!r})")

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["trial", "ground_truth", "predicted", "correct", "self_probe_latency_ms"])
        writer.writeheader()
        writer.writerows(rows)

    n_correct = sum(r["correct"] for r in rows)
    print(f"\nAccuracy (existence/activity ONLY, no identification): {n_correct}/{len(rows)} = {n_correct/len(rows)*100:.1f}%")
    print(f"Wrote {len(rows)} rows to {args.out}")
    gpu.close()


if __name__ == "__main__":
    main()
