import pandas as pd
import numpy as np
from sklearn.metrics import roc_auc_score

df = pd.read_csv("../../results/rq1_raw.csv")
rng = np.random.default_rng(0)

def bootstrap_auc_ci(state_a, state_b, n_boot=10000):
    sub = df[df["state"].isin([state_a, state_b])].reset_index(drop=True)
    y = (sub["state"] == state_b).astype(int).values
    score = sub["latency_ms"].values
    n = len(y)
    aucs = []
    for _ in range(n_boot):
        idx = rng.integers(0, n, n)
        y_b, s_b = y[idx], score[idx]
        if len(np.unique(y_b)) < 2:
            continue
        aucs.append(roc_auc_score(y_b, s_b))
    aucs = np.array(aucs)
    point = roc_auc_score(y, score)
    lo, hi = np.percentile(aucs, [2.5, 97.5])
    return point, lo, hi

print("=== RQ1 AUC with bootstrap 95% CI (10,000 resamples, n=30/state) ===")
for a, b in [("hot", "ram_evicted"), ("hot", "disk_evicted"), ("ram_evicted", "disk_evicted")]:
    point, lo, hi = bootstrap_auc_ci(a, b)
    print(f"{a:14s} vs {b:14s}: AUC = {point:.4f}  [95% CI: {lo:.4f}, {hi:.4f}]")
