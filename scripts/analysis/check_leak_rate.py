import pandas as pd
df = pd.read_csv("../../results/superseded/rq1_defended_raw.csv")
T_MAX = 150.0
for state in ["hot", "ram_evicted", "disk_evicted"]:
    sub = df[df["state"] == state]
    leaked = (sub["latency_ms"] > T_MAX + 2).sum()  # +2ms margin for proxy overhead noise
    print(f"{state:14s}: {leaked}/{len(sub)} samples exceeded T_MAX+2ms ({leaked/len(sub)*100:.1f}%)")
