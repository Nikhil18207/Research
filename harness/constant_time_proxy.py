"""Constant-time defense: pad every response to a fixed worst-case
latency, regardless of the adapter's true residency state.

Classic side-channel mitigation (constant-time cryptographic operations,
applied here to adapter serving). Sits in front of vLLM; forwards
/v1/completions, measures true completion latency, and if it's under
T_MAX, sleeps out the remainder before replying -- so every client-observed
latency is >= T_MAX regardless of whether the adapter was hot or evicted.

This directly measures the mitigation's cost too: throughput drops to
1/T_MAX requests/sec per connection in the worst case (the hot-case
requests that used to take ~30ms now always take T_MAX).
"""
import argparse
import csv
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import requests

T_MAX_S = 0.15  # set via CLI; module-level default overridden in main()
UPSTREAM = "http://localhost:8000"
BUCKET_S = None  # if set (via --bucket-ms), switch to quantized-padding mode
DIAG_LOG = None  # if set (via --diag-log), instrument every request's release timing
_diag_lock = threading.Lock()
_diag_file = None
_diag_writer = None

# A persistent, connection-pooled Session, not the module-level requests.post()
# convenience function. requests.post() opens and tears down a fresh TCP
# connection on every call; over a long-running proxy handling thousands of
# requests, this accumulates connection-establishment overhead and TIME_WAIT
# sockets, which showed up as latency inflation that scaled with how long the
# proxy had been running (T_MAX=300 runs, which take ~2x longer in wall-clock
# time for the same trial count, were visibly worse than T_MAX=150 runs) --
# not evidence of ambient system load, as first (wrongly) suspected.
_session = requests.Session()
_adapter = requests.adapters.HTTPAdapter(pool_connections=20, pool_maxsize=20)
_session.mount("http://", _adapter)


class ConstantTimeHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass  # silence default request logging -- keep proxy overhead minimal

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)

        t0 = time.monotonic()
        resp = _session.post(f"{UPSTREAM}{self.path}", data=body,
                              headers={"Content-Type": "application/json"}, timeout=30)
        t_true = time.monotonic() - t0  # true upstream latency

        if BUCKET_S is not None:
            # Quantized padding: round the true elapsed time UP to the next
            # multiple of BUCKET_S, rather than a single fixed T_MAX ceiling.
            # A request whose true latency exceeds one bucket still only
            # reveals a BUCKET INDEX (coarse, discrete) rather than its exact
            # true latency -- narrower leak than an unbounded hard ceiling,
            # at the cost of occasionally paying more than one bucket even
            # for a request that only slightly exceeded the previous one.
            elapsed_now = time.monotonic() - t0
            import math
            n_buckets = math.ceil(elapsed_now / BUCKET_S) if elapsed_now > 0 else 1
            deadline = t0 + n_buckets * BUCKET_S
        else:
            deadline = t0 + T_MAX_S

        # Block until an ABSOLUTE deadline, not a computed remainder.
        # A naive `time.sleep(T_MAX - true_latency)` re-leaks the residency bit:
        # sleep() overshoot and scheduler wakeup jitter scale with sleep duration,
        # so a hot request (long remainder, long sleep) accumulates more overshoot
        # than an evicted request (short remainder, short sleep) -- inverting the
        # timing signal instead of erasing it. Sleep most of the way, then busy-wait
        # the last ~1ms to land on the deadline precisely regardless of true latency.
        spin_iters = 0
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                break
            elif remaining > 0.002:
                time.sleep(remaining - 0.001)
            else:
                spin_iters += 1  # count spin-phase iterations for diagnosis

        t_release = time.monotonic() - t0  # when the wait loop actually broke

        self.send_response(resp.status_code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(resp.content)

        t_response_sent = time.monotonic() - t0

        if DIAG_LOG is not None:
            with _diag_lock:
                _diag_writer.writerow({
                    "t_true_ms": t_true * 1000,
                    "t_release_ms": t_release * 1000,
                    "t_response_sent_ms": t_response_sent * 1000,
                    "overshoot_ms": (t_release - T_MAX_S) * 1000,
                    "send_overhead_ms": (t_response_sent - t_release) * 1000,
                    "spin_iters": spin_iters,
                })
                _diag_file.flush()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8001)
    ap.add_argument("--upstream", default="http://localhost:8000")
    ap.add_argument("--t-max-ms", type=float, default=150.0,
                     help="worst-case padded latency, ms -- must exceed the slowest real reload time")
    ap.add_argument("--bucket-ms", type=float, default=None,
                     help="if set, use quantized padding instead of a hard T_MAX ceiling: "
                          "round elapsed time up to the next multiple of this bucket size")
    ap.add_argument("--diag-log", default=None,
                     help="if set, log t_true/t_release/t_response_sent/spin_iters per request to this CSV path")
    args = ap.parse_args()

    global T_MAX_S, UPSTREAM, BUCKET_S, DIAG_LOG, _diag_file, _diag_writer
    T_MAX_S = args.t_max_ms / 1000.0
    UPSTREAM = args.upstream
    BUCKET_S = args.bucket_ms / 1000.0 if args.bucket_ms else None
    DIAG_LOG = args.diag_log
    if DIAG_LOG is not None:
        _diag_file = open(DIAG_LOG, "w", newline="")
        _diag_writer = csv.DictWriter(_diag_file, fieldnames=[
            "t_true_ms", "t_release_ms", "t_response_sent_ms", "overshoot_ms", "send_overhead_ms", "spin_iters"])
        _diag_writer.writeheader()

    server = ThreadingHTTPServer(("0.0.0.0", args.port), ConstantTimeHandler)
    mode = f"quantized, bucket={args.bucket_ms}ms" if BUCKET_S else f"T_MAX={args.t_max_ms}ms"
    print(f"Constant-time proxy on :{args.port} -> {UPSTREAM}, {mode}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
