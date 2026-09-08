import pandas as pd
import numpy as np
from sklearn.metrics import confusion_matrix

df = pd.read_csv("../../results/rq3_multiprobe_raw.csv")
truth_by_trial = df.groupby("trial")["ground_truth"].first()
labels = ["A", "B", "both", "neither"]

THRESH = 60.0

print("=== RQ3 corrected-noise multiprobe: accuracy vs number of probes averaged ===")
for n in [1, 2, 3, 5]:
    preds, truths = [], []
    for trial in df["trial"].unique():
        sub = df[df["trial"] == trial].sort_values("probe_idx")
        med_a = np.median(sub["latency_a_ms"].values[:n])
        med_b = np.median(sub["latency_b_ms"].values[:n])
        a_active = med_a < THRESH
        b_active = med_b < THRESH
        if a_active and b_active:
            pred = "both"
        elif a_active:
            pred = "A"
        elif b_active:
            pred = "B"
        else:
            pred = "neither"
        preds.append(pred)
        truths.append(truth_by_trial[trial])
    acc = sum(p == t for p, t in zip(preds, truths)) / len(truths)
    print(f"N={n}: accuracy={acc*100:.1f}% ({sum(p==t for p,t in zip(preds,truths))}/{len(truths)})")
    if n == 5:
        cm = confusion_matrix(truths, preds, labels=labels)
        print("Confusion matrix at N=5 (rows=truth, cols=pred):")
        print(pd.DataFrame(cm, index=labels, columns=labels))

print("\n=== Raw latency stats by truth label (all probes pooled) ===")
print(df.groupby("ground_truth")[["latency_a_ms", "latency_b_ms"]].agg(["mean", "std"]).round(1))
