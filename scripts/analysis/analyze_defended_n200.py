import sys
import pandas as pd
import numpy as np
from scipy import stats
from sklearn.metrics import roc_auc_score

def hanley_mcneil_ci(auc, n1, n2, alpha=0.05):
    q1 = auc / (2 - auc)
    q2 = 2 * auc**2 / (1 + auc)
    se = np.sqrt((auc*(1-auc) + (n1-1)*(q1-auc**2) + (n2-1)*(q2-auc**2)) / (n1*n2))
    z = stats.norm.ppf(1 - alpha/2)
    return se, auc - z*se, auc + z*se

path = sys.argv[1] if len(sys.argv) > 1 else "../../results/rq1_defended_n200_150_raw.csv"
df = pd.read_csv(path)
print(f"=== {path} ===")
print(df.groupby("state")["latency_ms"].agg(["mean", "std", "min", "max"]).round(3))
print()
n = len(df[df["state"]=="hot"])
for a, b in [("hot", "ram_evicted"), ("hot", "disk_evicted"), ("ram_evicted", "disk_evicted")]:
    sub = df[df["state"].isin([a, b])]
    y = (sub["state"] == b).astype(int)
    auc = roc_auc_score(y, sub["latency_ms"])
    advantage = max(auc, 1 - auc)
    se, lo, hi = hanley_mcneil_ci(auc, n, n)
    # CI on advantage: if auc<0.5, flip and CI flips too, but SE is symmetric so just recompute on advantage's own AUC-equivalent
    adv_lo, adv_hi = max(lo,1-hi), max(hi,1-lo)
    print(f"{a:14s} vs {b:14s}: AUC={auc:.4f}  advantage={advantage:.4f}  SE={se:.4f}  advantage_CI=[{min(adv_lo,adv_hi):.4f}, {max(adv_lo,adv_hi):.4f}]")
