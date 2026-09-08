import pandas as pd
from sklearn.metrics import roc_auc_score

df = pd.read_csv("../../results/scenario_b_defended_raw.csv")
print(df.groupby("ground_truth")["self_probe_latency_ms"].agg(["mean", "std", "min", "max"]).round(3))

y = (df["ground_truth"] == "active").astype(int)
auc = roc_auc_score(y, df["self_probe_latency_ms"])
advantage = max(auc, 1 - auc)
print(f"\nDefended Scenario B: AUC={auc:.4f}, distinguishing advantage={advantage:.4f}")
print(f"(undefended Scenario B advantage was {max(0.7875, 1-0.7875):.4f})")
