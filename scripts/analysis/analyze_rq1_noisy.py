import pandas as pd
import numpy as np
from sklearn.metrics import roc_auc_score

df = pd.read_csv("../../results/rq1_noisy_raw.csv")

print("=== Per-state latency stats UNDER NOISE (ms) ===")
print(df.groupby("state")["latency_ms"].agg(["mean", "std", "median", "min", "max", "count"]).round(2))

print("\n=== GPU temp range under load ===")
print(df["gpu_gpu_temp_c"].agg(["min", "max", "mean"]))

def auc_between(a, b):
    sub = df[df["state"].isin([a, b])].copy()
    y = (sub["state"] == b).astype(int)
    return roc_auc_score(y, sub["latency_ms"])

print("\n=== Classification AUC UNDER NOISE (latency alone, single probe) ===")
for a, b in [("hot", "ram_evicted"), ("hot", "disk_evicted"), ("ram_evicted", "disk_evicted")]:
    print(f"{a:14s} vs {b:14s}: AUC = {auc_between(a, b):.4f}   (idle-GPU baseline was 0.92 / 1.00 / 1.00)")
