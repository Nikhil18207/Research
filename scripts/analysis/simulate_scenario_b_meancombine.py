"""Mean-combining (soft-decision) multi-round detection, correctly done:
average k raw latency draws before thresholding, using a threshold
recalibrated for multi-round combining (midpoint of the two class means),
not the single-shot Youden threshold (which sits near the idle mean and
is suboptimal once you're averaging).
"""
import argparse
import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in-csv", default="../../results/scenario_b_raw.csv")
    ap.add_argument("--n-boot", type=int, default=20000)
    ap.add_argument("--max-rounds", type=int, default=15)
    args = ap.parse_args()

    df = pd.read_csv(args.in_csv)
    active = df[df["ground_truth"] == "active"]["self_probe_latency_ms"].values
    idle = df[df["ground_truth"] == "idle"]["self_probe_latency_ms"].values

    mu_a, mu_i = active.mean(), idle.mean()
    sd_a, sd_i = active.std(), idle.std()
    pooled_sd = np.sqrt((sd_a**2 + sd_i**2) / 2)
    d_prime = (mu_a - mu_i) / pooled_sd
    midpoint = (mu_a + mu_i) / 2
    print(f"mu_active={mu_a:.2f} (sd={sd_a:.2f}), mu_idle={mu_i:.2f} (sd={sd_i:.2f})")
    print(f"single-probe d'={d_prime:.3f}, recalibrated midpoint threshold={midpoint:.2f}ms\n")

    rng = np.random.default_rng(0)
    print("=== Mean-combining accuracy vs. number of independent probing rounds ===")
    print("(explicitly assumes rounds are iid -- thermal drift, queue state, and temporal")
    print(" correlation in real victim traffic could violate this; treat as an upper-bound")
    print(" estimate pending real sequential data, not a guaranteed field result)\n")
    for n_rounds in [1, 2, 3, 5, 7, 10, 15]:
        correct = 0
        total = args.n_boot
        for _ in range(total):
            mean_active = rng.choice(active, size=n_rounds, replace=True).mean()
            mean_idle = rng.choice(idle, size=n_rounds, replace=True).mean()
            correct += int(mean_active > midpoint)
            correct += int(mean_idle <= midpoint)
        acc = correct / (2 * total)
        expected_d = d_prime * np.sqrt(n_rounds)
        print(f"N={n_rounds:2d}: mean-combining accuracy = {acc*100:.2f}%  (d'_N approx {expected_d:.2f})")

if __name__ == "__main__":
    main()
