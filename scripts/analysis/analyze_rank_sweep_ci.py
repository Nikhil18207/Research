import pandas as pd
import numpy as np
from scipy import stats

df = pd.read_csv("../../results/rank_sweep_raw.csv")

slope, intercept, r_value, p_value, std_err = stats.linregress(df["rank"], df["latency_ms"])
n = len(df)
t_crit = stats.t.ppf(0.975, n - 2)
ci_low = slope - t_crit * std_err
ci_high = slope + t_crit * std_err

print(f"n={n}")
print(f"slope = {slope:.3f} ms/rank-unit, 95% CI = [{ci_low:.3f}, {ci_high:.3f}]")
print(f"intercept = {intercept:.2f} ms")
print(f"R^2 = {r_value**2:.4f}")
print(f"(raw p-value = {p_value:.2e} -- reported for completeness, not as the headline statistic)")
