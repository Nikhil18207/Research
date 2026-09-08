"""Background concurrent-load generator for the noise-robustness matrix.

Fires requests continuously at randomized adapters, prompt lengths, and
generation lengths, from multiple concurrent worker threads -- simulating
realistic multi-tenant contention rather than testing on an idle GPU.

Run as a detached background process while the main RQ script runs
against the same server.
"""
import argparse
import random
import threading
import time

import requests

WORD_BANK = [
    "the", "quick", "brown", "fox", "jumps", "over", "lazy", "dog", "system",
    "model", "data", "server", "request", "process", "compute", "value",
    "result", "input", "output", "network", "signal", "state", "memory",
]


def random_prompt(min_words, max_words):
    n = random.randint(min_words, max_words)
    return " ".join(random.choice(WORD_BANK) for _ in range(n))


def worker(worker_id, base_url, adapters, stop_event, min_tokens, max_tokens, min_words, max_words, stats):
    session = requests.Session()
    count = 0
    while not stop_event.is_set():
        adapter = random.choice(adapters)
        prompt = random_prompt(min_words, max_words)
        max_tok = random.randint(min_tokens, max_tokens)
        try:
            session.post(
                f"{base_url}/v1/completions",
                json={"model": adapter, "prompt": prompt, "max_tokens": max_tok, "temperature": 0.7},
                timeout=30,
            )
            count += 1
        except Exception:
            pass
    stats[worker_id] = count


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", default="http://localhost:8000")
    ap.add_argument("--adapters", nargs="+", required=True)
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--duration-s", type=float, default=60.0)
    ap.add_argument("--min-tokens", type=int, default=1)
    ap.add_argument("--max-tokens", type=int, default=64)
    ap.add_argument("--min-words", type=int, default=3)
    ap.add_argument("--max-words", type=int, default=40)
    args = ap.parse_args()

    stop_event = threading.Event()
    stats = {}
    threads = [
        threading.Thread(
            target=worker,
            args=(i, args.base_url, args.adapters, stop_event, args.min_tokens, args.max_tokens,
                  args.min_words, args.max_words, stats),
        )
        for i in range(args.workers)
    ]
    print(f"Starting {args.workers} noise workers for {args.duration_s}s ...", flush=True)
    for t in threads:
        t.start()

    time.sleep(args.duration_s)
    stop_event.set()
    for t in threads:
        t.join()

    total = sum(stats.values())
    print(f"Noise generator done. Total requests fired: {total} ({total/args.duration_s:.1f} req/s)", flush=True)


if __name__ == "__main__":
    main()
