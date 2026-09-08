import pandas as pd
from sklearn.metrics import roc_auc_score

df = pd.read_csv("../../results/rq2_noisy_raw.csv")
print(df.groupby("ground_truth")["probe_latency_ms"].agg(["mean", "std", "median", "min", "max"]).round(2))
y = (df["ground_truth"] == "idle").astype(int)
auc = roc_auc_score(y, df["probe_latency_ms"])
print(f"\nSingle-probe Detection AUC under noise: {auc:.4f}  (idle-GPU baseline was 1.0000)")
