# Analyzes results/scenario_b_gradient_scaled/*.csv (2026-09-12, "Ninth critique
# round" in PROJECT.md) -- the n=150/condition, 7-worker-level rerun that
# corrects the eighth round's n=60 pilot ("graded, not a cliff"): it is a cliff.
# Generated the same way as the pilot, against native_test's production-scale
# server (max_loras=8/max_cpu_loras=8) via run_scenario_b_gradient_sweep_scaled.sh.
import pandas as pd
import numpy as np
from sklearn.metrics import roc_auc_score
from scipy import stats

def hanley_mcneil_ci(auc, n1, n2, alpha=0.05):
    q1 = auc / (2 - auc)
    q2 = 2 * auc**2 / (1 + auc)
    se = np.sqrt((auc*(1-auc) + (n1-1)*(q1-auc**2) + (n2-1)*(q2-auc**2)) / (n1*n2))
    z = stats.norm.ppf(1 - alpha/2)
    return max(0, auc - z*se), min(1, auc + z*se), se

def bootstrap_auc_ci(y, x, n_boot=10000, seed=0):
    rng = np.random.default_rng(seed)
    n = len(y); y = np.asarray(y); x = np.asarray(x)
    aucs = []
    for _ in range(n_boot):
        idx = rng.integers(0, n, n)
        yy, xx = y[idx], x[idx]
        if len(set(yy)) < 2:
            continue
        aucs.append(roc_auc_score(yy, xx))
    return np.percentile(aucs, [2.5, 97.5])

conditions = ["w0", "w1", "w2", "w3", "w4", "w5", "w6", "w6_queueonly"]
base = "/home/researcher/native_test/results/scenario_b_gradient_scaled"

print(f"{'condition':14s} {'n':>4s} {'idle_mean':>10s} {'active_mean':>12s} {'AUC':>8s} {'HM_CI':>18s} {'boot_CI':>18s} {'MWU_p':>10s}")
results = {}
for c in conditions:
    df = pd.read_csv(f"{base}/{c}_raw.csv")
    y = (df["ground_truth"] == "active").astype(int)
    x = df["self_probe_latency_ms"]
    auc = roc_auc_score(y, x)
    n1 = (y == 1).sum(); n0 = (y == 0).sum()
    hm_lo, hm_hi, se = hanley_mcneil_ci(auc, n1, n0)
    b_lo, b_hi = bootstrap_auc_ci(y, x)
    idle_mean = df[df.ground_truth == "idle"]["self_probe_latency_ms"].mean()
    active_mean = df[df.ground_truth == "active"]["self_probe_latency_ms"].mean()
    active = df[df.ground_truth == "active"]["self_probe_latency_ms"]
    idle = df[df.ground_truth == "idle"]["self_probe_latency_ms"]
    u, p = stats.mannwhitneyu(active, idle, alternative="greater")
    results[c] = auc
    print(f"{c:14s} {len(df):4d} {idle_mean:10.2f} {active_mean:12.2f} {auc:8.4f} "
          f"[{hm_lo:.3f},{hm_hi:.3f}]     [{b_lo:.3f},{b_hi:.3f}]    {p:.4f}")

print()
print("=== dose-response summary (pool conditions only) ===")
for c in ["w0","w1","w2","w3","w4","w5","w6"]:
    print(f"  {c}: AUC={results[c]:.3f}")

print()
print("=== mechanism check: w6 pool vs w6 queueonly (same worker count) ===")
print(f"  w6 (cache-competing):   AUC={results['w6']:.4f}")
print(f"  w6_queueonly (no cache competition): AUC={results['w6_queueonly']:.4f}")
