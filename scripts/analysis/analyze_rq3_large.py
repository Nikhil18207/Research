import pandas as pd
import numpy as np
from sklearn.metrics import confusion_matrix, classification_report

df = pd.read_csv("../../results/rq3_large_raw.csv")
labels = ["A", "B", "both", "neither"]

cm = confusion_matrix(df["ground_truth"], df["predicted"], labels=labels)
print("=== Confusion matrix (n=120, med=A, law=B) ===")
print(pd.DataFrame(cm, index=labels, columns=labels))
print()
print(classification_report(df["ground_truth"], df["predicted"], labels=labels, digits=4))

n = len(df)
errors = (df["ground_truth"] != df["predicted"]).sum()
acc = 1 - errors / n
print(f"n={n}, errors={errors}, accuracy={acc*100:.2f}%")

# Bootstrap 95% CI on accuracy (formalizing what was only rule-of-three before)
rng = np.random.default_rng(0)
correct = (df["ground_truth"] == df["predicted"]).values.astype(float)
boot_accs = []
for _ in range(10000):
    sample = rng.choice(correct, size=n, replace=True)
    boot_accs.append(sample.mean())
boot_accs = np.array(boot_accs)
ci_low, ci_high = np.percentile(boot_accs, [2.5, 97.5])
print(f"\nBootstrap 95% CI on accuracy (10,000 resamples): [{ci_low*100:.2f}%, {ci_high*100:.2f}%]")

if errors == 0:
    print(f"Zero errors at n={n} -> rule-of-three upper bound on true error rate: ~{3/n:.1%} at 95% confidence")
    print("(tighter than the n=60 bound of ~5.0% and the n=40 bound of ~7.5%)")

# Wilson score interval as a second, more standard method for a 0-error proportion
from scipy import stats
z = stats.norm.ppf(0.975)
phat = acc
denom = 1 + z**2/n
center = (phat + z**2/(2*n)) / denom
half_width = z * np.sqrt(phat*(1-phat)/n + z**2/(4*n**2)) / denom
print(f"Wilson score 95% CI on accuracy: [{max(0,center-half_width)*100:.2f}%, {min(1,center+half_width)*100:.2f}%]")
