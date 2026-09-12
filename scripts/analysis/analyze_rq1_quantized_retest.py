# Analyzes results/rq1_quantized_native_retest_raw.csv + proxy_quantized_diag.csv
# (2026-09-12 follow-up, PROJECT.md "Eighth critique round" -- the quantized-padding
# validation the fourth critique round left as "implemented, not tested"). Run against
# the native-storage small-scale server (max_loras=2/max_cpu_loras=4), confirmed AC
# power (140W) both ends, via harness/constant_time_proxy.py --bucket-ms 150 --diag-log.
# Paths below are hardcoded to /home/researcher/native_test; adjust if re-running.
import pandas as pd
import numpy as np
from sklearn.metrics import roc_auc_score
from scipy import stats

df = pd.read_csv("../../results/rq1_quantized_native_retest_raw.csv")
print("=== per-state latency summary ===")
print(df.groupby("state")["latency_ms"].agg(["mean", "std", "min", "max"]).round(2))

def hanley_mcneil_ci(auc, n1, n2, alpha=0.05):
    q1 = auc / (2 - auc)
    q2 = 2 * auc**2 / (1 + auc)
    se = np.sqrt((auc*(1-auc) + (n1-1)*(q1-auc**2) + (n2-1)*(q2-auc**2)) / (n1*n2))
    z = stats.norm.ppf(1 - alpha/2)
    return max(0, auc - z*se), min(1, auc + z*se)

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

print("\n=== distinguishing advantage (bucket=150ms quantized padding, n=100/state) ===")
pairs = [("hot", "ram_evicted"), ("hot", "disk_evicted"), ("ram_evicted", "disk_evicted")]
for a, b in pairs:
    da = df[df.state == a]["latency_ms"]
    db = df[df.state == b]["latency_ms"]
    y = np.array([0]*len(da) + [1]*len(db))
    x = np.concatenate([da, db])
    auc = roc_auc_score(y, x)
    adv = max(auc, 1 - auc)
    hm_lo, hm_hi = hanley_mcneil_ci(auc, len(da), len(db))
    b_lo, b_hi = bootstrap_auc_ci(y, x)
    u, p = stats.mannwhitneyu(db, da)
    print(f"{a:14s} vs {b:14s}  AUC={auc:.4f}  advantage={adv:.4f}  HM_CI=[{hm_lo:.3f},{hm_hi:.3f}]  "
          f"boot_CI=[{b_lo:.3f},{b_hi:.3f}]  MWU p={p:.4f}")

print("\n=== diag log: overshoot / spin_iters stability check ===")
diag = pd.read_csv("../../results/proxy_quantized_diag.csv")
print(diag[["t_true_ms", "t_release_ms", "overshoot_ms", "send_overhead_ms", "spin_iters"]].describe().round(3))
print(f"\nmax overshoot_ms: {diag['overshoot_ms'].max():.3f}")
print(f"trials with overshoot > 5ms: {(diag['overshoot_ms'].abs() > 5).sum()} / {len(diag)}")
print(f"trials with t_true_ms > 300ms (exceeding 2 buckets, true latency spike): {(diag['t_true_ms'] > 300).sum()} / {len(diag)}")
