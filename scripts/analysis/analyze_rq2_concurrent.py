import pandas as pd
import numpy as np
from sklearn.metrics import roc_auc_score

df = pd.read_csv("../../results/rq2_adaptive_concurrent_raw.csv")
truth_by_trial = df.groupby("trial")["ground_truth"].first()

print("=== diff_ms stats by ground truth (all probes pooled) ===")
print(df.groupby("ground_truth")["diff_ms"].agg(["mean", "std", "median", "min", "max"]).round(2))

print("\n=== AUC (threshold-free) vs number of paired probes averaged ===")
for n in [1, 2, 3]:
    meds, truths = [], []
    for trial in df["trial"].unique():
        sub = df[df["trial"] == trial].sort_values("probe_idx")
        meds.append(np.median(sub["diff_ms"].values[:n]))
        truths.append(truth_by_trial[trial])
    y = [1 if t == "idle" else 0 for t in truths]
    auc = roc_auc_score(y, meds)
    print(f"N={n}: AUC={auc:.4f}")

print("\n=== diff_ms by trial-half (checking for non-stationary load) ===")
df["half"] = (df["trial"] >= df["trial"].max() // 2).map({True: "second_half", False: "first_half"})
print(df.groupby(["half", "ground_truth"])["diff_ms"].agg(["mean", "std"]).round(2))
