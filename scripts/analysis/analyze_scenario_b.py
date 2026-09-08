import pandas as pd
from sklearn.metrics import roc_auc_score

df = pd.read_csv("../../results/scenario_b_raw.csv")
print(df.groupby("ground_truth")["self_probe_latency_ms"].agg(["mean", "std", "min", "max"]).round(2))

y = (df["ground_truth"] == "active").astype(int)
auc = roc_auc_score(y, df["self_probe_latency_ms"])
print(f"\nThreshold-free AUC (self-probe latency alone): {auc:.4f}")

from sklearn.metrics import roc_curve
fpr, tpr, thresholds = roc_curve(y, df["self_probe_latency_ms"])
j_scores = tpr - fpr
best_idx = j_scores.argmax()
best_thresh = thresholds[best_idx]
print(f"\nOptimal (Youden's J) threshold: {best_thresh:.2f}ms")

pred = (df["self_probe_latency_ms"] > best_thresh).astype(int)
acc = (pred == y).mean()
print(f"Accuracy at optimal threshold: {acc*100:.1f}%")
