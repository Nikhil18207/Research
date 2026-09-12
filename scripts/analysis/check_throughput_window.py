import re

LOG = "/home/researcher/native_test/results/vllm_server_scenarioB_contention.log"

windows = {
    "w6_queueonly": ("15:02:42", "15:03:25"),
    "w6_pool":      ("15:03:30", "15:04:21"),
}

pat = re.compile(r"09-12 (\d\d:\d\d:\d\d).*Avg prompt throughput: ([\d.]+) tokens/s, Avg generation throughput: ([\d.]+)")

data = {k: [] for k in windows}
with open(LOG, errors="ignore") as f:
    for line in f:
        m = pat.search(line)
        if not m:
            continue
        ts, prompt_tps, gen_tps = m.group(1), float(m.group(2)), float(m.group(3))
        for name, (s, e) in windows.items():
            if s <= ts <= e:
                data[name].append((ts, prompt_tps, gen_tps))

for name, rows in data.items():
    print(f"=== {name} ({len(rows)} samples) ===")
    for r in rows:
        print(r)
    if rows:
        avg_prompt = sum(r[1] for r in rows) / len(rows)
        avg_gen = sum(r[2] for r in rows) / len(rows)
        print(f"  mean prompt_tps={avg_prompt:.2f} mean gen_tps={avg_gen:.2f}")
    print()
