import pandas as pd
import numpy as np
from sklearn.metrics import confusion_matrix, classification_report

df = pd.read_csv("../../results/rq3_raw.csv")

print("=== Latency by ground truth (A probe, B probe) ===")
print(df.groupby("ground_truth")[["latency_a_ms", "latency_b_ms"]].agg(["mean", "std"]).round(2))

labels = ["A", "B", "both", "neither"]
cm = confusion_matrix(df["ground_truth"], df["predicted"], labels=labels)
print("\n=== Confusion matrix (rows=truth, cols=predicted) ===")
print(pd.DataFrame(cm, index=labels, columns=labels))

print("\n=== Per-class precision/recall ===")
print(classification_report(df["ground_truth"], df["predicted"], labels=labels, digits=4))

# rough channel capacity: 2 bits of ground truth per trial (4 classes),
# how many bits are actually getting through given the (here, zero) error rate
n = len(df)
errors = (df["ground_truth"] != df["predicted"]).sum()
print(f"n={n} trials, errors={errors}")
if errors == 0:
    print("Zero errors observed -> cannot estimate a finite empirical error rate from this sample;")
    print("by rule-of-three, true error rate plausibly as high as ~3/n = {:.1%} at 95% confidence.".format(3/n))
