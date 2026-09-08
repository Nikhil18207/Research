import pandas as pd
import numpy as np
from scipy import stats

df = pd.read_csv("/home/researcher/native_test/results/proxy_diag.csv")
print(f"n={len(df)} logged requests")
print(df[["t_true_ms", "t_release_ms", "overshoot_ms", "send_overhead_ms", "spin_iters"]].describe())

print("\n=== Correlation: does t_release/overshoot/send_overhead correlate with t_true? ===")
for col in ["t_release_ms", "overshoot_ms", "send_overhead_ms", "spin_iters"]:
    r, p = stats.pearsonr(df["t_true_ms"], df[col])
    print(f"corr(t_true_ms, {col}) = r={r:.4f}, p={p:.2e}")

# Only look at requests where t_true < T_MAX (i.e. padding actually engaged, not tail-leak cases)
padded = df[df["t_true_ms"] < 150]
print(f"\n=== Same, restricted to n={len(padded)} requests where t_true < T_MAX=150ms (padding actually engaged) ===")
for col in ["t_release_ms", "overshoot_ms", "send_overhead_ms", "spin_iters"]:
    r, p = stats.pearsonr(padded["t_true_ms"], padded[col])
    print(f"corr(t_true_ms, {col}) = r={r:.4f}, p={p:.2e}")

print(f"\nt_release_ms stats when padded (n={len(padded)}): mean={padded['t_release_ms'].mean():.3f}, std={padded['t_release_ms'].std():.3f}, min={padded['t_release_ms'].min():.3f}, max={padded['t_release_ms'].max():.3f}")
