import pandas as pd
import numpy as np
from sklearn.metrics import roc_auc_score

df = pd.read_csv("../../results/rq1_multiprobe_raw.csv")

print("=== Raw per-state stats (all individual probes pooled) ===")
print(df.groupby("state")["latency_ms"].agg(["mean", "std", "median", "min", "max"]).round(2))

def median_of_n(group, n):
    return group.iloc[:n].median()

pivot = df.pivot_table(index=["trial"], columns="state", values="latency_ms", aggfunc=list)

print("\n=== Attack-cost curve: AUC vs number of probes averaged (median-of-N) ===")
for n in [1, 2, 3, 5, 10]:
    hot_meds = [np.median(x[:n]) for x in pivot["hot"]]
    ram_meds = [np.median(x[:n]) for x in pivot["ram_evicted"]]
    disk_meds = [np.median(x[:n]) for x in pivot["disk_evicted"]]

    y_hd = [0]*len(hot_meds) + [1]*len(disk_meds)
    auc_hd = roc_auc_score(y_hd, hot_meds + disk_meds)

    y_hr = [0]*len(hot_meds) + [1]*len(ram_meds)
    auc_hr = roc_auc_score(y_hr, hot_meds + ram_meds)

    y_rd = [0]*len(ram_meds) + [1]*len(disk_meds)
    auc_rd = roc_auc_score(y_rd, ram_meds + disk_meds)

    print(f"N={n:2d} probes/measurement (cost={n} req):  "
          f"hot-vs-disk AUC={auc_hd:.4f}   hot-vs-ram AUC={auc_hr:.4f}   ram-vs-disk AUC={auc_rd:.4f}")
