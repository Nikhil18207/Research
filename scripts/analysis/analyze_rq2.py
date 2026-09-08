import pandas as pd
import numpy as np
from sklearn.metrics import roc_auc_score

df = pd.read_csv("../../results/rq2_raw.csv")

print("=== Per-truth-label latency stats (attacker's probe only, ms) ===")
print(df.groupby("ground_truth")["probe_latency_ms"].agg(["mean", "std", "median", "min", "max", "count"]).round(2))

y = (df["ground_truth"] == "idle").astype(int)  # idle = slow = higher score
auc = roc_auc_score(y, df["probe_latency_ms"])
print(f"\nDetection AUC (probe latency alone): {auc:.4f}")

fp = ((df["ground_truth"] == "idle") & (df["predicted"] == "active")).sum()
fn = ((df["ground_truth"] == "active") & (df["predicted"] == "idle")).sum()
n_idle = (df["ground_truth"] == "idle").sum()
n_active = (df["ground_truth"] == "active").sum()
print(f"\nAt threshold=50ms:")
print(f"  False positives (idle predicted active): {fp}/{n_idle} = {fp/n_idle*100:.1f}%")
print(f"  False negatives (active predicted idle): {fn}/{n_active} = {fn/n_active*100:.1f}%")
print(f"  Overall accuracy: {(df['correct']=='True').sum() if df['correct'].dtype==object else df['correct'].sum()}/{len(df)}")
