import pandas as pd
from sklearn.metrics import roc_auc_score

df = pd.read_csv("../../results/rq1_defended_300_raw.csv")
print("=== Defended (T_MAX=300ms, fixed proxy) latency by state ===")
print(df.groupby("state")["latency_ms"].agg(["mean", "std", "min", "max"]).round(3))

print("\n=== AUC and distinguishing advantage ===")
for a, b in [("hot", "ram_evicted"), ("hot", "disk_evicted"), ("ram_evicted", "disk_evicted")]:
    sub = df[df["state"].isin([a, b])]
    y = (sub["state"] == b).astype(int)
    auc = roc_auc_score(y, sub["latency_ms"])
    advantage = max(auc, 1 - auc)
    print(f"{a:14s} vs {b:14s}: AUC={auc:.4f}  advantage={advantage:.4f}")
