"""Core timing primitive: probe one adapter through vLLM's OpenAI-compatible API
and measure request latency with nanosecond timestamps.

This is the ATTACKER's view — client-side wall-clock timing only. Ground-truth
residency state (for labeling, not for the attack itself) must come from a
separate server-side instrumentation path, never from this module.
"""
import time
import requests

from gpu_monitor import GPUMonitor


class Prober:
    def __init__(self, base_url="http://localhost:8000", gpu_monitor: GPUMonitor | None = None):
        self.base_url = base_url.rstrip("/")
        self.gpu = gpu_monitor
        self.session = requests.Session()

    def probe(self, adapter_name, prompt="The", max_tokens=1, timeout=30):
        """Send one minimal completion request to `adapter_name`, time it.

        max_tokens=1 keeps generation cost near-fixed so latency is
        dominated by (reload time, if any) + prefill, not decode length.
        """
        payload = {
            "model": adapter_name,
            "prompt": prompt,
            "max_tokens": max_tokens,
            "temperature": 0,
        }
        gpu_before = self.gpu.sample() if self.gpu else {}

        t0 = time.perf_counter_ns()
        wall_t0 = time.time_ns()
        resp = self.session.post(f"{self.base_url}/v1/completions", json=payload, timeout=timeout)
        t1 = time.perf_counter_ns()

        latency_ms = (t1 - t0) / 1e6
        return {
            "adapter": adapter_name,
            "wall_timestamp_ns": wall_t0,
            "latency_ms": latency_ms,
            "http_status": resp.status_code,
            **{f"gpu_{k}": v for k, v in gpu_before.items()},
        }

    def burst_probe(self, adapter_names, prompt="The", max_tokens=1):
        """Probe each adapter in `adapter_names` once, in order.

        Order and per-probe timestamps are kept (not just latency numbers) —
        RQ3's identity signal lives in the pattern across a burst, not a
        single reading.
        """
        return [self.probe(name, prompt=prompt, max_tokens=max_tokens) for name in adapter_names]
