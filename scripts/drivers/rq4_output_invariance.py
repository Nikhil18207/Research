"""RQ4 -- Control: prove the channel is a pure timing leak, not interference.

Capture greedy-decoded completions (+ logprobs) from med/law on a fixed
prompt set, under two conditions run as SEPARATE invocations of this
script (--condition absent | present) so the caller controls whether the
noise generator is running concurrently. Comparison happens afterward in
analyze_rq4.py.
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "harness"))
import requests  # noqa: E402

PROMPTS = {
    "med": [
        "Q: What is the function of the kidneys?\nA:",
        "Q: What are common symptoms of the flu?\nA:",
        "Q: What is the purpose of a blood pressure cuff?\nA:",
        "Q: What causes a common cold?\nA:",
        "Q: What is the role of red blood cells?\nA:",
    ],
    "law": [
        "Q: What is a plaintiff?\nA:",
        "Q: What is the purpose of a lease agreement?\nA:",
        "Q: What is copyright infringement?\nA:",
        "Q: What is the role of a judge?\nA:",
        "Q: What is a legal deposition?\nA:",
    ],
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", default="http://localhost:8000")
    ap.add_argument("--condition", choices=["absent", "present"], required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    session = requests.Session()
    results = []
    for adapter, prompts in PROMPTS.items():
        for prompt in prompts:
            resp = session.post(
                f"{args.base_url}/v1/completions",
                json={
                    "model": adapter,
                    "prompt": prompt,
                    "max_tokens": 30,
                    "temperature": 0,
                    "logprobs": 5,
                },
                timeout=30,
            ).json()
            choice = resp["choices"][0]
            results.append({
                "adapter": adapter,
                "prompt": prompt,
                "condition": args.condition,
                "text": choice["text"],
                "logprobs": choice.get("logprobs"),
                "finish_reason": choice.get("finish_reason"),
            })
            print(f"[{args.condition}] {adapter}: {prompt[:40]!r} -> {choice['text'][:60]!r}")

    with open(args.out, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nWrote {len(results)} results to {args.out}")


if __name__ == "__main__":
    main()
