"""RQ2 realism upgrade: detect activity from REALISTIC (Poisson-process)
victim traffic, not one deterministic inserted request.

Per critique: "Does this actually resemble realistic tenant traffic?" --
this replaces the single hidden request with a victim thread generating
Poisson-arrival requests to the target over an observation window, while
the attacker independently fires its own probes across the same window
and must infer window-level activity from the PATTERN of its own
readings, not a single before/after snapshot.

Ground truth per trial: one of several realistic traffic regimes.
  idle    -- no victim arrivals in the window
  low     -- Poisson rate ~0.3 req/s (sparse, occasional victim activity)
  high    -- Poisson rate ~2.0 req/s (busy victim)
  bursty  -- all arrivals clustered in the first third of the window
             (same expected count as 'high', different temporal shape)
"""
import argparse
import csv
import os
import random
import statistics
import sys
import threading
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "harness"))
from gpu_monitor import GPUMonitor  # noqa: E402
from probe import Prober  # noqa: E402


def prime_evict(prober, target, fillers, max_cpu_loras):
    prober.probe(target)
    n_needed = max_cpu_loras + 1
    for name in (fillers * ((n_needed // len(fillers)) + 1))[:n_needed]:
        prober.probe(name)


def victim_traffic_thread(base_url, target, regime, window_s, stop_flag):
    """Runs concurrently with the attacker's probing. Uses its OWN
    session -- ground-truth traffic generation must not share a client
    with the attacker's measurement path."""
    import requests
    session = requests.Session()
    t_end = time.time() + window_s

    if regime == "idle":
        return  # no arrivals

    if regime == "low":
        rate = 0.3
    elif regime == "high":
        rate = 2.0
    elif regime == "bursty":
        rate = 2.0  # same expected count as 'high', different shape
    else:
        raise ValueError(regime)

    MAX_SLEEP_CHUNK = 0.15  # check stop_flag frequently -- a thread must never
    # outlive its window by more than this, or it lingers into FUTURE trials
    # (a real bug found here: expovariate() has a long tail, and join(timeout=2.0)
    # does not kill a thread, it just stops waiting for it -- an orphaned thread
    # firing delayed requests minutes later silently contaminates later trials)

    def sleep_interruptible(duration):
        remaining = duration
        while remaining > 0 and not stop_flag["stop"]:
            chunk = min(MAX_SLEEP_CHUNK, remaining)
            time.sleep(chunk)
            remaining -= chunk

    if regime == "bursty":
        burst_end = time.time() + window_s / 3
        while time.time() < burst_end and not stop_flag["stop"]:
            session.post(f"{base_url}/v1/completions",
                         json={"model": target, "prompt": "victim traffic", "max_tokens": 1, "temperature": 0},
                         timeout=10)
            sleep_interruptible(random.expovariate(rate * 3))
        return

    while time.time() < t_end and not stop_flag["stop"]:
        session.post(f"{base_url}/v1/completions",
                     json={"model": target, "prompt": "victim traffic", "max_tokens": 1, "temperature": 0},
                     timeout=10)
        sleep_interruptible(random.expovariate(rate))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", default="http://localhost:8000")
    ap.add_argument("--target", required=True)
    ap.add_argument("--fillers", nargs="+", required=True)
    ap.add_argument("--max-cpu-loras", type=int, required=True)
    ap.add_argument("--trials", type=int, default=20)
    ap.add_argument("--window-s", type=float, default=3.0)
    ap.add_argument("--probes-per-window", type=int, default=1,
                     help="1 = clean design (evict once, generate traffic, probe once at window end -- "
                          "avoids the attacker's own repeated probing self-sustaining residency)")
    ap.add_argument("--threshold-ms", type=float, default=60.0)
    ap.add_argument("--out", default="../results/rq2_poisson_raw.csv")
    args = ap.parse_args()

    gpu = GPUMonitor()
    prober = Prober(base_url=args.base_url, gpu_monitor=gpu)

    regimes = ["idle", "low", "high", "bursty"]
    rows = []
    for trial in range(args.trials):
        regime = regimes[trial % len(regimes)]
        prime_evict(prober, args.target, args.fillers, args.max_cpu_loras)

        stop_flag = {"stop": False}
        vt = threading.Thread(target=victim_traffic_thread,
                               args=(args.base_url, args.target, regime, args.window_s, stop_flag))
        vt.start()

        probe_interval = args.window_s / args.probes_per_window
        readings = []
        window_start = time.time()
        for p in range(args.probes_per_window):
            # probes land across (0, window_s], so a single probe fires at window END
            # (after traffic has had the full window to occur), not at window start
            target_t = window_start + (p + 1) * probe_interval
            sleep_for = target_t - time.time()
            if sleep_for > 0:
                time.sleep(sleep_for)
            lat = prober.probe(args.target)["latency_ms"]
            readings.append(lat)

        stop_flag["stop"] = True
        vt.join(timeout=2.0)

        n_hot = sum(1 for r in readings if r < args.threshold_ms)
        frac_hot = n_hot / len(readings)
        predicted = "idle" if n_hot == 0 else ("low" if frac_hot < 0.5 else "high_or_bursty")
        # ground truth collapsed to a coarse label for scoring: did the window show ANY victim activity signal?
        gt_any_activity = "idle" if regime == "idle" else "active"
        pred_any_activity = "idle" if n_hot == 0 else "active"
        correct = gt_any_activity == pred_any_activity

        row = {
            "trial": trial, "regime": regime, "n_hot": n_hot, "frac_hot": frac_hot,
            "predicted_coarse": predicted, "gt_any_activity": gt_any_activity,
            "pred_any_activity": pred_any_activity, "correct": correct,
            "readings": ";".join(f"{r:.1f}" for r in readings),
        }
        rows.append(row)
        print(f"trial={trial:3d} regime={regime:8s} n_hot={n_hot}/{len(readings)} "
              f"frac_hot={frac_hot:.2f} gt={gt_any_activity:6s} pred={pred_any_activity:6s} "
              f"{'OK' if correct else 'ERR'}")

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    n_correct = sum(r["correct"] for r in rows)
    print(f"\nCoarse (any-activity) accuracy: {n_correct}/{len(rows)} = {n_correct/len(rows)*100:.1f}%")
    print(f"Wrote {len(rows)} rows to {args.out}")
    gpu.close()


if __name__ == "__main__":
    main()
