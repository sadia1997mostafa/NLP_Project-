"""Train a small QLoRA answer writer on Colab and export one local GGUF."""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
UNSLOTH_MODEL = "unsloth/Qwen3-4B-Instruct-2507"


def _read_jsonl(path: Path) -> list[dict]:
    if not path.is_file():
        raise FileNotFoundError(f"Missing {path}; run scripts.export_answer_training first")
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if not rows or any(set(row) != {"prompt", "completion"} for row in rows):
        raise ValueError(f"Invalid answer training data: {path}")
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=ROOT / "data" / "answer_generation")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "models" / "answer_generator")
    parser.add_argument("--max-steps", type=int, default=60)
    parser.add_argument("--skip-gguf", action="store_true", help="Keep the adapter only")
    args = parser.parse_args()
    if args.max_steps < 1:
        parser.error("--max-steps must be positive")
    train_rows = _read_jsonl(args.data_dir / "train.jsonl")
    dev_rows = _read_jsonl(args.data_dir / "dev.jsonl")

    import torch
    if not torch.cuda.is_available():
        raise RuntimeError("A CUDA GPU is required; select GPU in Colab Runtime settings")
    from unsloth import FastLanguageModel
    from datasets import Dataset
    from trl import SFTConfig, SFTTrainer

    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=UNSLOTH_MODEL, max_seq_length=1024, load_in_4bit=True,
    )
    model = FastLanguageModel.get_peft_model(
        model, r=8, lora_alpha=16, lora_dropout=0, bias="none",
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
        use_gradient_checkpointing="unsloth", random_state=3407,
    )
    args.output_dir.mkdir(parents=True, exist_ok=True)
    trainer = SFTTrainer(
        model=model,
        processing_class=tokenizer,
        train_dataset=Dataset.from_list(train_rows),
        eval_dataset=Dataset.from_list(dev_rows),
        args=SFTConfig(
            output_dir=str(args.output_dir / "checkpoints"),
            max_length=1024, completion_only_loss=True, packing=False,
            per_device_train_batch_size=1, per_device_eval_batch_size=1,
            gradient_accumulation_steps=8, max_steps=args.max_steps,
            learning_rate=1e-4, warmup_steps=5, optim="adamw_8bit",
            fp16=not torch.cuda.is_bf16_supported(), bf16=torch.cuda.is_bf16_supported(),
            logging_steps=10, save_strategy="no", eval_strategy="no",
            report_to="none", seed=3407,
        ),
    )
    train_metrics = trainer.train().metrics
    eval_metrics = trainer.evaluate()
    (args.output_dir / "metrics.json").write_text(
        json.dumps({"train": train_metrics, "dev": eval_metrics}, indent=2), encoding="utf-8",
    )
    model.save_pretrained(str(args.output_dir / "adapter"))
    tokenizer.save_pretrained(str(args.output_dir / "adapter"))

    FastLanguageModel.for_inference(model)
    sample_rows = random.Random(3407).sample(dev_rows, min(12, len(dev_rows)))
    with (args.output_dir / "review_samples.jsonl").open("w", encoding="utf-8") as target:
        for row in sample_rows:
            inputs = tokenizer.apply_chat_template(
                row["prompt"], add_generation_prompt=True, return_tensors="pt",
            ).to("cuda")
            generated = model.generate(inputs, max_new_tokens=220, do_sample=False)
            answer = tokenizer.decode(generated[0][inputs.shape[-1]:], skip_special_tokens=True).strip()
            target.write(json.dumps({
                "question_context": row["prompt"][1]["content"],
                "reference": row["completion"][0]["content"],
                "generated": answer,
            }, ensure_ascii=False) + "\n")

    if not args.skip_gguf:
        model.save_pretrained_gguf(
            str(args.output_dir / "gguf"), tokenizer, quantization_method="q4_k_m",
        )
    print(f"Training artifacts saved in {args.output_dir}")


if __name__ == "__main__":
    main()
