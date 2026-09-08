"""Train a real LoRA adapter on domain Q&A content (med or law).

Not a model-quality exercise -- this project studies the serving-layer side
channel, not fine-tuning quality. The bar is "a real, non-trivial,
domain-distinguishable adapter", not benchmark-grade accuracy.
"""
import argparse

import torch
from datasets import Dataset
from peft import LoraConfig, get_peft_model
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    DataCollatorForLanguageModeling,
    Trainer,
    TrainingArguments,
)

from med_law_data import MED_QA, LAW_QA

TARGET_MODULES = ["q_proj", "k_proj", "v_proj", "o_proj"]


def build_dataset(pairs, tokenizer, max_len=256):
    texts = [f"Q: {q}\nA: {a}{tokenizer.eos_token}" for q, a in pairs]
    enc = tokenizer(texts, truncation=True, max_length=max_len, padding="max_length")
    ds = Dataset.from_dict(enc)
    return ds


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="meta-llama/Llama-3.2-1B")
    ap.add_argument("--domain", choices=["med", "law"], required=True)
    ap.add_argument("--rank", type=int, required=True)
    ap.add_argument("--epochs", type=int, default=10)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    data = MED_QA if args.domain == "med" else LAW_QA
    print(f"Training {args.domain} adapter (rank={args.rank}) on {len(data)} Q&A pairs")

    tokenizer = AutoTokenizer.from_pretrained(args.base)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    model = AutoModelForCausalLM.from_pretrained(args.base, dtype=torch.bfloat16)
    lora_config = LoraConfig(
        r=args.rank,
        lora_alpha=args.rank * 2,
        target_modules=TARGET_MODULES,
        lora_dropout=0.05,
        bias="none",
        task_type="CAUSAL_LM",
    )
    model = get_peft_model(model, lora_config)
    model.print_trainable_parameters()

    ds = build_dataset(data, tokenizer)
    collator = DataCollatorForLanguageModeling(tokenizer=tokenizer, mlm=False)

    training_args = TrainingArguments(
        output_dir=f"/tmp/train_{args.domain}",
        num_train_epochs=args.epochs,
        per_device_train_batch_size=4,
        learning_rate=2e-4,
        logging_steps=5,
        save_strategy="no",
        report_to=[],
        bf16=True,
    )

    trainer = Trainer(model=model, args=training_args, train_dataset=ds, data_collator=collator)
    trainer.train()

    model.save_pretrained(args.out)
    print(f"Saved {args.domain} adapter to {args.out}")


if __name__ == "__main__":
    main()
