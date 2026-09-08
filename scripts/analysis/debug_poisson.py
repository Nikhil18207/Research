import sys, os, time, threading, requests
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "harness"))
from probe import Prober

BASE = "http://localhost:8000"
TARGET = "med"
FILLERS = ["junk_0_r8","junk_1_r16","junk_2_r32","junk_3_r8","junk_4_r16","junk_5_r32"]

prober = Prober(base_url=BASE)

# prime evict
prober.probe(TARGET)
for f in (FILLERS * 2)[:5]:
    prober.probe(f)
print("primed (evicted).")

victim_log = []
def victim():
    s = requests.Session()
    t_end = time.time() + 3.0
    n = 0
    while time.time() < t_end:
        t0 = time.time()
        r = s.post(f"{BASE}/v1/completions", json={"model": TARGET, "prompt": "victim traffic", "max_tokens": 1, "temperature": 0}, timeout=10)
        t1 = time.time()
        victim_log.append((t0, t1, r.status_code))
        n += 1
        time.sleep(0.3)  # fixed rate ~3.3/s for this debug test, not Poisson
    print(f"victim thread fired {n} requests")

vt = threading.Thread(target=victim)
window_start = time.time()
vt.start()
time.sleep(3.0)
probe_start = time.time()
result = prober.probe(TARGET)
probe_end = time.time()
vt.join()

print(f"window_start={window_start:.3f}")
for t0, t1, code in victim_log:
    print(f"  victim req: start={t0-window_start:.3f}s end={t1-window_start:.3f}s status={code}")
print(f"attacker probe: start={probe_start-window_start:.3f}s end={probe_end-window_start:.3f}s latency_ms={result['latency_ms']:.2f}")
