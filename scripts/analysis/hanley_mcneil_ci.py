import numpy as np
from scipy import stats

def hanley_mcneil_ci(auc, n1, n2, alpha=0.05):
    q1 = auc / (2 - auc)
    q2 = 2 * auc**2 / (1 + auc)
    se = np.sqrt((auc*(1-auc) + (n1-1)*(q1-auc**2) + (n2-1)*(q2-auc**2)) / (n1*n2))
    z = stats.norm.ppf(1 - alpha/2)
    return auc - z*se, auc + z*se, se

for label, auc, n1, n2 in [
    ("Scenario B, default config", 0.7875, 20, 20),
    ("Scenario B, tightened CPU tier", 0.9875, 20, 20),
]:
    lo, hi, se = hanley_mcneil_ci(auc, n1, n2)
    print(f"{label}: AUC={auc:.4f}, SE={se:.4f}, 95% CI=[{max(0,lo):.4f}, {min(1,hi):.4f}]")
