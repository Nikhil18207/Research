import pandas as pd
import numpy as np
from sklearn.metrics import roc_auc_score

df = pd.read_csv("../../results/rq2_multiprobe2_raw.csv")
truth_by_trial = df.groupby("trial")["ground_truth"].first()

print("=== RQ2 corrected-noise multiprobe: AUC vs number of probes averaged ===")
for n in [1, 2, 3, 5]:
    meds, truths = [], []
    for trial in df["trial"].unique():
        sub = df[df["trial"] == trial].sort_values("probe_idx")
        meds.append(np.median(sub["latency_ms"].values[:n]))
        truths.append(truth_by_trial[trial])
    y = [1 if t == "idle" else 0 for t in truths]
    auc = roc_auc_score(y, meds)
    print(f"N={n}: AUC={auc:.4f}")

single_df = pd.read_csv("../../results/rq2_noisy2_raw.csv")
y2 = (single_df["ground_truth"] == "idle").astype(int)
auc_single = roc_auc_score(y2, single_df["probe_latency_ms"])
print(f"\nFor comparison, single-probe (N=1, separate run) AUC: {auc_single:.4f}")
