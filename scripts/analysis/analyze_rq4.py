import json
import numpy as np

with open("../../results/rq4_absent.json") as f:
    absent = json.load(f)
with open("../../results/rq4_present.json") as f:
    present = json.load(f)

assert len(absent) == len(present)

print("=== Exact text match check ===")
text_mismatches = 0
for a, p in zip(absent, present):
    match = a["text"] == p["text"]
    if not match:
        text_mismatches += 1
        print(f"MISMATCH [{a['adapter']}] {a['prompt'][:30]!r}:")
        print(f"  absent : {a['text']!r}")
        print(f"  present: {p['text']!r}")
print(f"Text mismatches: {text_mismatches}/{len(absent)}")

print("\n=== Logprob comparison (top-1 token logprob per position) ===")
max_abs_diff = 0.0
all_diffs = []
for a, p in zip(absent, present):
    a_lp = a["logprobs"]["token_logprobs"] if a["logprobs"] else None
    p_lp = p["logprobs"]["token_logprobs"] if p["logprobs"] else None
    if a_lp is None or p_lp is None:
        continue
    n = min(len(a_lp), len(p_lp))
    for i in range(n):
        if a_lp[i] is None or p_lp[i] is None:
            continue
        diff = abs(a_lp[i] - p_lp[i])
        all_diffs.append(diff)
        max_abs_diff = max(max_abs_diff, diff)

all_diffs = np.array(all_diffs)
print(f"n token positions compared: {len(all_diffs)}")
print(f"max |logprob diff|: {max_abs_diff:.8f}")
print(f"mean |logprob diff|: {all_diffs.mean():.8f}")
print(f"All diffs == 0.0: {np.all(all_diffs == 0.0)}")
