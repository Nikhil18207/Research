import pandas as pd
df = pd.read_csv("../../results/superseded/rq1_defended_raw.csv")
for margin in [10, 20]:
    print(f"--- margin=+{margin}ms ---")
    for state in ["hot", "ram_evicted", "disk_evicted"]:
        sub = df[df["state"] == state]
        leaked = (sub["latency_ms"] > 150 + margin).sum()
        print(f"{state:14s}: {leaked}/{len(sub)} samples exceeded T_MAX+{margin}ms")
