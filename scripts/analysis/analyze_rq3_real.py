import pandas as pd
import numpy as np
from sklearn.metrics import confusion_matrix, classification_report
from scipy import stats

df = pd.read_csv("../../results/rq3_real_raw.csv")

labels = ["A", "B", "both", "neither"]
cm = confusion_matrix(df["ground_truth"], df["predicted"], labels=labels)
print("=== Confusion matrix (med=A, law=B; rows=truth, cols=predicted) ===")
print(pd.DataFrame(cm, index=labels, columns=labels))
print()
print(classification_report(df["ground_truth"], df["predicted"], labels=labels, digits=4))

n = len(df)
errors = (df["ground_truth"] != df["predicted"]).sum()
print(f"n={n}, errors={errors}")
if errors == 0:
    print(f"Zero errors -> rule-of-three upper bound on true error rate: ~{3/n:.1%} at 95% confidence")

print("\n=== RANK-LEAKAGE BONUS: med(r8) vs law(r32) reload time when BOTH evicted ===")
neither = df[df["ground_truth"] == "neither"]
med_evicted = neither["latency_a_ms"]  # med = adapter A
law_evicted = neither["latency_b_ms"]  # law = adapter B
print(f"med (rank 8)  reload latency: mean={med_evicted.mean():.2f}ms std={med_evicted.std():.2f} n={len(med_evicted)}")
print(f"law (rank 32) reload latency: mean={law_evicted.mean():.2f}ms std={law_evicted.std():.2f} n={len(law_evicted)}")
t, p = stats.ttest_ind(law_evicted, med_evicted)
pooled_std = np.sqrt((med_evicted.std()**2 + law_evicted.std()**2) / 2)
d = (law_evicted.mean() - med_evicted.mean()) / pooled_std
print(f"Welch/independent t-test: t={t:.3f}, p={p:.6f}")
print(f"Cohen's d = {d:.2f}")
print(f"-> rank-32 adapter takes {law_evicted.mean() - med_evicted.mean():.1f}ms longer to reload than rank-8, on average")
