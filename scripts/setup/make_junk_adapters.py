"""Generate placeholder LoRA adapters for RQ1 tier characterization.

RQ1 only needs to measure reload LATENCY, not adapter quality — a
standard-init LoRA adapter (B=0, so it's a no-op) still has real tensors
of the right shape that vLLM must load, so it's a valid stand-in here.
Real med/law adapters (trained on actual content) come later, once RQ1
has confirmed the signal exists on this hardware.

Usage:
    python make_junk_adapters.py --base meta-llama/Llama-3.2-1B --n 6 --out ../adapters
"""
import argparse
import os

from peft import LoraConfig, get_peft_model
from transformers import AutoModelForCausalLM

TARGET_MODULES = ["q_proj", "k_proj", "v_proj", "o_proj"]


def make_adapter(base_model, rank, out_dir):
    config = LoraConfig(
        r=rank,
        lora_alpha=rank * 2,
        target_modules=TARGET_MODULES,
        lora_dropout=0.0,
        bias="none",
        task_type="CAUSAL_LM",
    )
    peft_model = get_peft_model(base_model, config)
    peft_model.save_pretrained(out_dir)
    # get_peft_model wraps in place; detach the adapter so the next call
    # starts from a clean base again.
    peft_model.unload()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="meta-llama/Llama-3.2-1B")
    ap.add_argument("--n", type=int, default=6, help="number of junk adapters")
    ap.add_argument("--ranks", type=int, nargs="+", default=None,
                     help="explicit rank per adapter; defaults to cycling [8,16,32]")
    ap.add_argument("--out", default="../adapters")
    args = ap.parse_args()

    ranks = args.ranks or [[8, 16, 32][i % 3] for i in range(args.n)]

    print(f"Loading base model {args.base} ...")
    base_model = AutoModelForCausalLM.from_pretrained(args.base)

    for i, rank in enumerate(ranks):
        out_dir = os.path.join(args.out, f"junk_{i}_r{rank}")
        os.makedirs(out_dir, exist_ok=True)
        make_adapter(base_model, rank, out_dir)
        print(f"  wrote {out_dir} (rank={rank})")

    print("Done.")


if __name__ == "__main__":
    main()
