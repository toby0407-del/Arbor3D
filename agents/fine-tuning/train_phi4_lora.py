"""Train a local Phi-4-mini LoRA adapter from the reviewed Arbor3D Q&A split."""

from __future__ import annotations

import argparse
from pathlib import Path

import torch
from datasets import load_dataset
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    BitsAndBytesConfig,
    Trainer,
    TrainingArguments,
    default_data_collator,
)


ROOT = Path(__file__).resolve().parent


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="microsoft/Phi-4-mini-instruct")
    parser.add_argument("--train", default=str(ROOT / "data" / "phi4-sft-train-900.jsonl"))
    parser.add_argument("--eval", default=str(ROOT / "data" / "phi4-sft-eval-100.jsonl"))
    parser.add_argument("--output", default=str(ROOT / "output" / "arbor3d-phi4-mini-lora"))
    parser.add_argument("--epochs", type=float, default=3.0)
    parser.add_argument("--max-length", type=int, default=1024)
    return parser.parse_args()


def main() -> None:
    args = arguments()
    if not torch.cuda.is_available():
        raise SystemExit("LoRA 訓練需要 CUDA NVIDIA GPU；CPU 僅適合執行量化後推論。")

    tokenizer = AutoTokenizer.from_pretrained(args.model, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    quantization = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.bfloat16,
        bnb_4bit_use_double_quant=True,
    )
    model = AutoModelForCausalLM.from_pretrained(
        args.model,
        trust_remote_code=True,
        quantization_config=quantization,
        device_map="auto",
    )
    model = prepare_model_for_kbit_training(model)
    model = get_peft_model(model, LoraConfig(
        r=16,
        lora_alpha=32,
        lora_dropout=0.05,
        bias="none",
        task_type="CAUSAL_LM",
        target_modules="all-linear",
    ))

    dataset = load_dataset("json", data_files={"train": args.train, "eval": args.eval})

    def tokenize(example: dict) -> dict:
        text = tokenizer.apply_chat_template(
            example["messages"], tokenize=False, add_generation_prompt=False,
        )
        encoded = tokenizer(
            text,
            truncation=True,
            max_length=args.max_length,
            padding="max_length",
        )
        encoded["labels"] = [
            token if mask else -100
            for token, mask in zip(encoded["input_ids"], encoded["attention_mask"], strict=True)
        ]
        return encoded

    tokenized = dataset.map(tokenize, remove_columns=dataset["train"].column_names)
    trainer = Trainer(
        model=model,
        args=TrainingArguments(
            output_dir=args.output,
            num_train_epochs=args.epochs,
            per_device_train_batch_size=1,
            per_device_eval_batch_size=1,
            gradient_accumulation_steps=8,
            gradient_checkpointing=True,
            learning_rate=2e-4,
            logging_steps=10,
            eval_strategy="epoch",
            save_strategy="epoch",
            load_best_model_at_end=True,
            bf16=True,
            report_to="none",
            remove_unused_columns=False,
        ),
        train_dataset=tokenized["train"],
        eval_dataset=tokenized["eval"],
        data_collator=default_data_collator,
    )
    trainer.train()
    trainer.save_model(args.output)
    tokenizer.save_pretrained(args.output)
    print(f"Saved LoRA adapter to {args.output}")


if __name__ == "__main__":
    main()
