import pandas as pd
import numpy as np
from sklearn.metrics import roc_auc_score

df = pd.read_csv("../../results/rq1_raw.csv")

print("=== Per-state latency stats (ms) ===")
stats = df.groupby("state")["latency_ms"].agg(["mean", "std", "median", "min", "max", "count"])
print(stats.round(2))

print("\n=== GPU temp range (confound check) ===")
print(df["gpu_gpu_temp_c"].agg(["min", "max", "mean"]))

def auc_between(state_a, state_b):
    sub = df[df["state"].isin([state_a, state_b])].copy()
    y = (sub["state"] == state_b).astype(int)
    score = sub["latency_ms"]
    return roc_auc_score(y, score)

print("\n=== Classification AUC (latency alone) ===")
for a, b in [("hot", "ram_evicted"), ("hot", "disk_evicted"), ("ram_evicted", "disk_evicted")]:
    auc = auc_between(a, b)
    print(f"{a:14s} vs {b:14s}: AUC = {auc:.4f}")

print("\n=== Effect size (mean gap / pooled std) ===")
def cohens_d(state_a, state_b):
    a = df[df["state"] == state_a]["latency_ms"]
    b = df[df["state"] == state_b]["latency_ms"]
    pooled_std = np.sqrt((a.std()**2 + b.std()**2) / 2)
    return (b.mean() - a.mean()) / pooled_std

for a, b in [("hot", "ram_evicted"), ("hot", "disk_evicted"), ("ram_evicted", "disk_evicted")]:
    d = cohens_d(a, b)
    print(f"{a:14s} vs {b:14s}: Cohen's d = {d:.2f}")
