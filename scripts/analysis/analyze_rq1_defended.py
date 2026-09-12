import pandas as pd
from sklearn.metrics import roc_auc_score

df = pd.read_csv("../../results/superseded/rq1_defended_raw.csv")
print("=== Defended (through constant-time proxy) latency by state ===")
print(df.groupby("state")["latency_ms"].agg(["mean", "std", "min", "max"]).round(2))

for a, b in [("hot", "ram_evicted"), ("hot", "disk_evicted"), ("ram_evicted", "disk_evicted")]:
    sub = df[df["state"].isin([a, b])]
    y = (sub["state"] == b).astype(int)
    auc = roc_auc_score(y, sub["latency_ms"])
    print(f"{a:14s} vs {b:14s}: AUC = {auc:.4f}  (undefended baseline was 0.92/1.00/1.00)")
