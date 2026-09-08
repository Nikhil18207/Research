import pandas as pd
import numpy as np
from scipy import stats

df = pd.read_csv("../../results/rank_sweep_raw.csv")

print("=== Rank sweep: latency by rank (n=15 per rank, same content domain) ===")
summary = df.groupby("rank")["latency_ms"].agg(["mean", "std", "median", "min", "max"]).round(2)
print(summary)

# Pearson correlation (linear) and Spearman (monotonic, rank-based -- more appropriate
# given latency vs rank need not be exactly linear)
pearson_r, pearson_p = stats.pearsonr(df["rank"], df["latency_ms"])
spearman_r, spearman_p = stats.spearmanr(df["rank"], df["latency_ms"])
print(f"\nPearson r={pearson_r:.4f}, p={pearson_p:.2e}")
print(f"Spearman rho={spearman_r:.4f}, p={spearman_p:.2e}")

# linear regression for a reportable slope (ms per unit rank)
slope, intercept, r_value, p_value, std_err = stats.linregress(df["rank"], df["latency_ms"])
print(f"\nLinear fit: latency_ms = {slope:.3f} * rank + {intercept:.2f}  (R^2={r_value**2:.4f})")

# also fit on log(rank) since rank doubles (1,8,16,32,64) -- log-linear may fit better
log_rank = np.log2(df["rank"])
slope2, intercept2, r2, p2, se2 = stats.linregress(log_rank, df["latency_ms"])
print(f"Log-linear fit: latency_ms = {slope2:.3f} * log2(rank) + {intercept2:.2f}  (R^2={r2**2:.4f})")
