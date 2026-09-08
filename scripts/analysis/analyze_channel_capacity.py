import pandas as pd
import numpy as np

df = pd.read_csv("../../results/rq3_real_raw.csv")

# wall_timestamp_a_ns marks the start of each trial's burst-probe phase
timestamps = df["wall_timestamp_a_ns"].values / 1e9  # -> seconds
total_duration_s = timestamps[-1] - timestamps[0]
n_trials = len(df)
avg_trial_time_s = total_duration_s / (n_trials - 1)

bits_per_trial = np.log2(4)  # 4 balanced classes (A, B, both, neither), 0 errors observed
capacity_bits_per_s = bits_per_trial / avg_trial_time_s

# requests-per-trial: 2 initial hot-probes + 2*(evict_both double pass) + up to 2 hidden + 2 burst
# evict_both: n_needed = max_cpu_loras+1 = 5, done TWICE (double pass) = 10, x2 adapters no -- shared fillers
# concretely: 2 (ensure hot) + 10 (evict pass1) + 10 (evict pass2) + up to 2 (hidden activity) + 2 (burst probe) 
n_fillers_per_pass = 5  # max_cpu_loras + 1
requests_per_trial_est = 2 + n_fillers_per_pass + n_fillers_per_pass + 2  # rough (hidden count varies 0-2)
bits_per_request = bits_per_trial / requests_per_trial_est

print(f"n_trials={n_trials}, total wall-clock={total_duration_s:.1f}s")
print(f"avg time per trial: {avg_trial_time_s:.3f}s")
print(f"bits per trial (4-class, ~0 error): {bits_per_trial:.2f} bits")
print(f"channel capacity: {capacity_bits_per_s:.3f} bits/s")
print(f"est. requests per trial: ~{requests_per_trial_est}")
print(f"measurements-per-bit: ~{requests_per_trial_est/bits_per_trial:.1f} attacker requests per bit of identity information")
