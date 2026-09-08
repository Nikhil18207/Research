import pandas as pd
from sklearn.metrics import roc_auc_score

df = pd.read_csv("../../results/rq2_poisson_fixed_raw.csv")
df["latency"] = df["readings"].astype(float)  # single probe per window -> readings is just one number

print("=== Latency by regime (single probe per window, thread-bug fixed) ===")
print(df.groupby("regime")["latency"].agg(["mean", "std", "median", "min", "max"]).round(2))

y = (df["regime"] != "idle").astype(int)  # active = 1
auc = roc_auc_score(y, -df["latency"])  # lower latency = more likely active
print(f"\nAUC (idle vs any-active, latency as score, threshold-free): {auc:.4f}")

for regime in ["low", "high", "bursty"]:
    sub = df[df["regime"].isin(["idle", regime])]
    yy = (sub["regime"] == regime).astype(int)
    a = roc_auc_score(yy, -sub["latency"])
    print(f"idle vs {regime}: AUC={a:.4f}")
