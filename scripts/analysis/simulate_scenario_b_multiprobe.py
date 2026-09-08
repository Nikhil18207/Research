"""Bootstrap-simulate majority-vote accuracy vs. number of independent
probing rounds, using the empirical per-class distributions already
collected in scenario_b_self_eviction.py's single-probe data. A real
attacker repeats the whole round-robin-reset-probe protocol N times
(not re-probes an already-just-touched adapter, which would self-warm),
so each simulated "round" draws a fresh independent sample from the
measured class-conditional distribution.
"""
import argparse
import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in-csv", default="../../results/scenario_b_raw.csv")
    ap.add_argument("--threshold-ms", type=float, default=36.05)
    ap.add_argument("--n-boot", type=int, default=20000)
    ap.add_argument("--max-rounds", type=int, default=15)
    args = ap.parse_args()

    df = pd.read_csv(args.in_csv)
    active = df[df["ground_truth"] == "active"]["self_probe_latency_ms"].values
    idle = df[df["ground_truth"] == "idle"]["self_probe_latency_ms"].values

    single_auc = roc_auc_score([1]*len(active) + [0]*len(idle), list(active) + list(idle))
    print(f"Single-probe AUC (from {args.in_csv}): {single_auc:.4f}")
    print(f"n active={len(active)}, n idle={len(idle)}\n")

    rng = np.random.default_rng(0)
    print("=== Majority-vote accuracy vs. number of independent probing rounds ===")
    for n_rounds in range(1, args.max_rounds + 1):
        correct = 0
        total = args.n_boot
        for _ in range(total):
            # simulate an "active" trial: n_rounds independent draws from active dist
            votes_active = (rng.choice(active, size=n_rounds, replace=True) > args.threshold_ms).sum()
            pred_active = votes_active > n_rounds / 2
            correct += int(pred_active)

            votes_idle = (rng.choice(idle, size=n_rounds, replace=True) > args.threshold_ms).sum()
            pred_idle_as_idle = votes_idle <= n_rounds / 2
            correct += int(pred_idle_as_idle)
        acc = correct / (2 * total)
        print(f"N={n_rounds:2d} rounds: majority-vote accuracy = {acc*100:.2f}%")

if __name__ == "__main__":
    main()
