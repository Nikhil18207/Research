"""Volume sweep: does detection frequency track victim request rate?

Directly demonstrates the paper's motivating competitive-intelligence scenario
(§1): a co-tenant estimating a rival's traffic VOLUME, not just a binary
active/idle flag. Generalizes rq2_poisson_traffic.py's four fixed regimes
(idle/low/high/bursty) to an explicit sweep over victim request rates,
reporting single-probe-at-window-end AUC (idle vs. that rate) at each point.

Usage:
    python rq_volume_sweep.py --target med --fillers junk_0_r8 ... \
        --max-cpu-loras 4 --rates 0 0.1 0.3 0.5 1.0 2.0 --trials-per-rate 20 \
        --out ../results/volume_sweep_raw.csv
"""
import argparse
import csv
import os
import random
import sys
import threading
import time

CANARY_ADAPTER = None  # set via --canary; if given, probed 10x at start and end of the run

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "harness"))
from gpu_monitor import GPUMonitor  # noqa: E402
from probe import Prober  # noqa: E402


def prime_evict(prober, target, fillers, max_cpu_loras):
    prober.probe(target)
    n_needed = max_cpu_loras + 1
    for name in (fillers * ((n_needed // len(fillers)) + 1))[:n_needed]:
        prober.probe(name)


def victim_traffic_thread(base_url, target, rate, window_s, stop_flag):
    """Same interruptible-sleep pattern as rq2_poisson_traffic.py -- a thread
    must never outlive its own window (expovariate's long tail plus
    join(timeout=...) not actually killing a thread was a real bug there)."""
    import requests
    session = requests.Session()
    t_end = time.time() + window_s
    MAX_SLEEP_CHUNK = 0.15

    def sleep_interruptible(duration):
        remaining = duration
        while remaining > 0 and not stop_flag["stop"]:
            chunk = min(MAX_SLEEP_CHUNK, remaining)
            time.sleep(chunk)
            remaining -= chunk

    if rate <= 0:
        return  # idle: no arrivals

    while time.time() < t_end and not stop_flag["stop"]:
        session.post(f"{base_url}/v1/completions",
                     json={"model": target, "prompt": "victim traffic", "max_tokens": 1, "temperature": 0},
                     timeout=10)
        sleep_interruptible(random.expovariate(rate))


def run_one_trial(prober, base_url, target, fillers, max_cpu_loras, rate, window_s):
    prime_evict(prober, target, fillers, max_cpu_loras)
    stop_flag = {"stop": False}
    vt = threading.Thread(target=victim_traffic_thread, args=(base_url, target, rate, window_s, stop_flag))
    vt.start()
    time.sleep(window_s)
    lat = prober.probe(target)["latency_ms"]
    stop_flag["stop"] = True
    vt.join(timeout=2.0)
    return lat


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", default="http://localhost:8000")
    ap.add_argument("--target", required=True)
    ap.add_argument("--fillers", nargs="+", required=True)
    ap.add_argument("--max-cpu-loras", type=int, required=True)
    ap.add_argument("--rates", type=float, nargs="+", required=True,
                     help="victim request rates (req/s) to test; 0 = idle baseline, included once")
    ap.add_argument("--trials-per-rate", type=int, default=20)
    ap.add_argument("--window-s", type=float, default=3.0)
    ap.add_argument("--canary", default=None,
                     help="adapter name to probe 10x at start and end of the run, to log whether "
                          "the measurement environment drifted across the session (§3.7 discipline)")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out", default="../results/volume_sweep_raw.csv")
    args = ap.parse_args()

    gpu = GPUMonitor()
    prober = Prober(base_url=args.base_url, gpu_monitor=gpu)

    canary_start, canary_end = [], []
    if args.canary:
        canary_start = [prober.probe(args.canary)["latency_ms"] for _ in range(10)]
        print(f"canary ({args.canary}) at start: {[round(x,1) for x in canary_start]}")

    # Build the full (rate, trial) schedule and SHUFFLE it -- rate must not be
    # collinear with session-order/time, or session-length drift (documented
    # in §4.5/§4.6) becomes indistinguishable from a genuine rate effect.
    rng = random.Random(args.seed)
    schedule = [(rate, trial) for rate in args.rates for trial in range(args.trials_per_rate)]
    rng.shuffle(schedule)

    rows = []
    for session_order, (rate, trial) in enumerate(schedule):
        lat = run_one_trial(prober, args.base_url, args.target, args.fillers,
                             args.max_cpu_loras, rate, args.window_s)
        row = {"rate": rate, "trial": trial, "session_order": session_order, "latency_ms": lat}
        rows.append(row)
        print(f"order={session_order:3d} rate={rate:5.2f} trial={trial:3d} latency_ms={lat:8.2f}")

    if args.canary:
        canary_end = [prober.probe(args.canary)["latency_ms"] for _ in range(10)]
        print(f"canary ({args.canary}) at end: {[round(x,1) for x in canary_end]}")

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["rate", "trial", "session_order", "latency_ms"])
        writer.writeheader()
        writer.writerows(rows)

    if args.canary:
        canary_path = os.path.splitext(args.out)[0] + "_canary.csv"
        with open(canary_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["position", "latency_ms"])
            writer.writeheader()
            for lat in canary_start:
                writer.writerow({"position": "start", "latency_ms": lat})
            for lat in canary_end:
                writer.writerow({"position": "end", "latency_ms": lat})
        print(f"Wrote canary readings to {canary_path}")

    print(f"\nWrote {len(rows)} rows to {args.out} (schedule shuffled, seed={args.seed})")
    gpu.close()


if __name__ == "__main__":
    main()
