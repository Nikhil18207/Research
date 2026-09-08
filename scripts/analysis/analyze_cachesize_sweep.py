import pandas as pd
from sklearn.metrics import roc_auc_score

configs = {
    1: "../../results/cachesize_maxloras1_raw.csv",
    2: "../../results/rq1_raw.csv",  # original baseline, already n=30
    4: "../../results/cachesize_maxloras4_raw.csv",
}

print("=== Cache-size sweep: hot-vs-disk_evicted AUC at each max_loras setting ===")
for max_loras, path in configs.items():
    df = pd.read_csv(path)
    sub = df[df["state"].isin(["hot", "disk_evicted"])]
    y = (sub["state"] == "disk_evicted").astype(int)
    auc = roc_auc_score(y, sub["latency_ms"])
    means = df.groupby("state")["latency_ms"].mean().round(2)
    n = len(df[df["state"] == "hot"])
    print(f"max_loras={max_loras} (n={n}/state): AUC={auc:.4f}  hot={means.get('hot','-')}  "
          f"ram_evicted={means.get('ram_evicted','-')}  disk_evicted={means.get('disk_evicted','-')}")
