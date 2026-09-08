import pandas as pd
from sklearn.metrics import roc_auc_score

df = pd.read_csv("../../results/smol_rq1_raw.csv")
print(df.groupby("state")["latency_ms"].agg(["mean", "std", "min", "max"]).round(2))

sub = df[df["state"].isin(["hot", "disk_evicted"])]
y = (sub["state"] == "disk_evicted").astype(int)
auc = roc_auc_score(y, sub["latency_ms"])
print(f"\nSmolLM2-1.7B hot-vs-disk_evicted AUC: {auc:.4f}")
