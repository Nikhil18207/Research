import pandas as pd
import numpy as np
from sklearn.metrics import roc_auc_score

df = pd.read_csv("../../results/rq2_multiprobe_raw.csv")
pivot = df.pivot_table(index="trial", columns="ground_truth", values="latency_ms", aggfunc=list)
truth_by_trial = df.groupby("trial")["ground_truth"].first()

print("=== Attack-cost curve: RQ2 detection AUC vs number of probes averaged ===")
for n in [1, 2, 3, 5]:
    meds, truths = [], []
    for trial in df["trial"].unique():
        sub = df[df["trial"] == trial].sort_values("probe_idx")
        meds.append(np.median(sub["latency_ms"].values[:n]))
        truths.append(truth_by_trial[trial])
    y = [1 if t == "idle" else 0 for t in truths]
    auc = roc_auc_score(y, meds)
    print(f"N={n}: AUC={auc:.4f}")
