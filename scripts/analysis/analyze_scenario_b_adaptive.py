# Analyzes results/scenario_b_adaptive_w6_raw.csv (2026-09-12, "Ninth critique
# round"): fixed-threshold vs. concurrent-canary-diff vs. full rolling-baseline
# adaptive detector, all under 6-worker cache-competing contention, n=150.
# Generated via scripts/drivers/scenario_b_adaptive.py against native_test's
# production-scale server, using a dedicated canary_0 adapter (see that
# driver's docstring for the max_loras-1-round-robin design constraint).
import pandas as pd
import numpy as np
from sklearn.metrics import roc_auc_score, accuracy_score
from scipy import stats

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

def wilson_ci(k, n, z=1.96):
    p = k / n
    denom = 1 + z**2/n
    centre = p + z**2/(2*n)
    adj = z * np.sqrt(p*(1-p)/n + z**2/(4*n**2))
    return (centre - adj) / denom, (centre + adj) / denom

df = pd.read_csv("/home/researcher/native_test/results/scenario_b_adaptive_w6_raw.csv")
print(f"n={len(df)}")
print(df.groupby("ground_truth")[["target_latency_ms", "canary_latency_ms", "diff_ms"]].agg(["mean", "std"]).round(2))
print()

y = (df["ground_truth"] == "active").astype(int)

# 1. Fixed-threshold-style baseline: raw target latency alone, no canary, no adaptivity
auc_fixed = roc_auc_score(y, df["target_latency_ms"])
lo_f, hi_f = bootstrap_auc_ci(y, df["target_latency_ms"])
adv_fixed = max(auc_fixed, 1 - auc_fixed)

# 2. Concurrent-canary diff, threshold-free (pairing only, no rolling baseline)
auc_diff = roc_auc_score(y, df["diff_ms"])
lo_d, hi_d = bootstrap_auc_ci(y, df["diff_ms"])
adv_diff = max(auc_diff, 1 - auc_diff)

print("=== Threshold-free comparisons (AUC / advantage) ===")
print(f"Fixed (raw target latency alone):      AUC={auc_fixed:.4f}  advantage={adv_fixed:.4f}  CI=[{lo_f:.3f},{hi_f:.3f}]")
print(f"Concurrent-canary diff (pairing only):  AUC={auc_diff:.4f}  advantage={adv_diff:.4f}  CI=[{lo_d:.3f},{hi_d:.3f}]")
u, p = stats.mannwhitneyu(df[df.ground_truth=="active"]["diff_ms"], df[df.ground_truth=="idle"]["diff_ms"])
print(f"Mann-Whitney (diff_ms, active vs idle): p={p:.4f}")
print()

# 3. Full adaptive online decision: rolling median+MAD baseline, evaluated only where
#    a real (non-default) decision was made (i.e., window had >=3 points)
valid = df[df["rolling_baseline_ms"].notna()]
print(f"=== Full adaptive (rolling baseline) online decision, n={len(valid)} (excludes {len(df)-len(valid)} warm-up trials) ===")
acc = accuracy_score(valid["ground_truth"] == "active", valid["predicted_adaptive"] == "active")
k = (valid["ground_truth"] == valid["predicted_adaptive"]).sum()
lo_w, hi_w = wilson_ci(k, len(valid))
print(f"Accuracy: {k}/{len(valid)} = {acc*100:.1f}%  Wilson 95% CI=[{lo_w*100:.1f}%,{hi_w*100:.1f}%]")

# confusion breakdown
print(pd.crosstab(valid["ground_truth"], valid["predicted_adaptive"], rownames=["truth"], colnames=["predicted"]))
print()

# For reference: what would raw-latency fixed-threshold accuracy have been at the
# same 60ms cutoff this whole project has used throughout?
fixed_pred = np.where(df["target_latency_ms"] < 60, "idle", "active")  # NOTE: Scenario B calls "active" when latency is HIGH
fixed_pred = np.where(df["target_latency_ms"] > 60, "active", "idle")
acc_fixed60 = accuracy_score(df["ground_truth"], fixed_pred)
print(f"Reference: fixed 60ms-threshold accuracy on the SAME trials = {acc_fixed60*100:.1f}%")
