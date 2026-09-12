# Analyzes results/scenario_b_gradient_sweep/*.csv (2026-09-12 follow-up, PROJECT.md
# "Eighth critique round"). Generated against the native-storage production-scale
# server (max_loras=8/max_cpu_loras=8) via run_scenario_b_gradient_sweep.sh, run
# from /home/researcher/native_test (not the 9p-bridged repo layout every other
# script here assumes -- see §3.7 for why native storage is used for this class of
# check). Paths below are hardcoded to that native_test location; adjust if re-running.
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
    n = len(y)
    y = np.asarray(y); x = np.asarray(x)
    aucs = []
    for _ in range(n_boot):
        idx = rng.integers(0, n, n)
        yy, xx = y[idx], x[idx]
        if len(set(yy)) < 2:
            continue
        aucs.append(roc_auc_score(yy, xx))
    lo, hi = np.percentile(aucs, [2.5, 97.5])
    return lo, hi

conditions = ["w0", "w2", "w4", "w6", "w6_queueonly"]
base = "../../results/superseded/scenario_b_gradient_sweep"

print(f"{'condition':14s} {'n':>4s} {'idle_mean':>10s} {'active_mean':>12s} {'AUC':>8s} {'advantage':>10s} {'HM_CI':>20s} {'boot_CI':>20s}")
for c in conditions:
    df = pd.read_csv(f"{base}_{c}_raw.csv")
    y = (df["ground_truth"] == "active").astype(int)
    x = df["self_probe_latency_ms"]
    auc = roc_auc_score(y, x)
    adv = max(auc, 1 - auc)
    n1 = (y == 1).sum(); n0 = (y == 0).sum()
    hm_lo, hm_hi, se = hanley_mcneil_ci(auc, n1, n0)
    b_lo, b_hi = bootstrap_auc_ci(y, x)
    idle_mean = df[df.ground_truth == "idle"]["self_probe_latency_ms"].mean()
    active_mean = df[df.ground_truth == "active"]["self_probe_latency_ms"].mean()
    print(f"{c:14s} {len(df):4d} {idle_mean:10.2f} {active_mean:12.2f} {auc:8.4f} {adv:10.4f} "
          f"[{hm_lo:.3f},{hm_hi:.3f}] [{b_lo:.3f},{b_hi:.3f}]")

print()
print("=== Mann-Whitney U per condition (idle vs active latency) ===")
for c in conditions:
    df = pd.read_csv(f"{base}_{c}_raw.csv")
    active = df[df.ground_truth == "active"]["self_probe_latency_ms"]
    idle = df[df.ground_truth == "idle"]["self_probe_latency_ms"]
    u, p = stats.mannwhitneyu(active, idle, alternative="greater")
    print(f"{c:14s} U={u:8.1f} p={p:.4f}")

print()
print("=== canary drift check ===")
print("pre-sweep  mean=42.27ms  lats=[94.10, 33.57, 27.53, 26.10, 30.04]")
print("post-sweep mean=56.43ms  lats=[73.30, 64.27, 47.91, 49.10, 47.57]")
pre = [94.10, 33.57, 27.53, 26.10, 30.04]
post = [73.30, 64.27, 47.91, 49.10, 47.57]
u, p = stats.mannwhitneyu(post, pre)
print(f"Mann-Whitney U pre-vs-post: U={u:.1f} p={p:.4f}")
