import pandas as pd
from sklearn.metrics import roc_auc_score

df = pd.read_csv("../../results/scenario_b_tightcpu_raw.csv")
print(df.groupby("ground_truth")["self_probe_latency_ms"].agg(["mean", "std", "min", "max"]).round(2))

y = (df["ground_truth"] == "active").astype(int)
auc = roc_auc_score(y, df["self_probe_latency_ms"])
print(f"\nTightened-CPU-tier Scenario B: AUC={auc:.4f}")
print(f"(default max_cpu_loras=4 config gave AUC=0.7875)")
