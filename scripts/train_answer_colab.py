"""Train a small QLoRA answer writer on Colab and export one local GGUF."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

from src.response.local_generator import acceptable_answer
from src.response.model_prompt import prompt_messages
from src.response.plans import render_plan_completion
from src.retrieval.lookup import GuidanceLookup


ROOT = Path(__file__).resolve().parents[1]
UNSLOTH_MODEL = "unsloth/Qwen3-4B-Instruct-2507"
RECIPE = "grounded_qwen_v3_all_intents"
CHALLENGES = ROOT / "knowledge_base" / "answer_challenges.json"


def _read_jsonl(path: Path) -> list[dict]:
    if not path.is_file():
        raise FileNotFoundError(f"Missing {path}; run scripts.export_answer_training first")
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if not rows or any(set(row) != {"prompt", "completion"} for row in rows):
        raise ValueError(f"Invalid answer training data: {path}")
    return rows


def challenge_rows() -> list[dict]:
    records = {
        (record["service"], record["query_topic_id"]): record
        for record in GuidanceLookup().records if record["query_topic_id"]
    }
    challenges = json.loads(CHALLENGES.read_text(encoding="utf-8"))
    rows = []
    for challenge in challenges:
        if set(challenge) != {"service", "query_topic_id", "language", "question"}:
            raise ValueError("Invalid answer challenge schema")
        record = records.get((challenge["service"], challenge["query_topic_id"]))
        if record is None or challenge["language"] not in {"en", "bn"}:
            raise ValueError(f"Invalid answer challenge route: {challenge}")
        language = challenge["language"]
        rows.append({
            "prompt": prompt_messages(challenge["question"], record, language),
            "completion": [{
                "role": "assistant",
                "content": render_plan_completion(record, language),
            }],
        })
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=ROOT / "data" / "answer_generation")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "models" / "answer_generator")
    parser.add_argument("--max-steps", type=int, default=264)
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
        model_name=UNSLOTH_MODEL, max_seq_length=2048, load_in_4bit=True,
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
            max_length=2048, completion_only_loss=True, packing=False,
            per_device_train_batch_size=1, per_device_eval_batch_size=1,
            gradient_accumulation_steps=8, max_steps=args.max_steps,
            learning_rate=2e-5, warmup_steps=3, weight_decay=0.01,
            lr_scheduler_type="cosine", optim="adamw_8bit",
            fp16=not torch.cuda.is_bf16_supported(), bf16=torch.cuda.is_bf16_supported(),
            logging_steps=10, save_strategy="no", eval_strategy="no",
            report_to="none", seed=3407,
        ),
    )
    train_metrics = trainer.train().metrics
    eval_metrics = trainer.evaluate()
    (args.output_dir / "metrics.json").write_text(
        json.dumps({
            "recipe": RECIPE,
            "configuration": {
                "max_steps": args.max_steps, "learning_rate": 2e-5,
                "lora_rank": 8, "max_sequence_length": 2048,
            },
            "train": train_metrics,
            "dev": eval_metrics,
        }, indent=2), encoding="utf-8",
    )
    model.save_pretrained(str(args.output_dir / "adapter"))
    tokenizer.save_pretrained(str(args.output_dir / "adapter"))

    FastLanguageModel.for_inference(model)
    sample_rows = challenge_rows()
    records = {(record["service"], record["title"]): record for record in GuidanceLookup().records}
    accepted_count = 0
    with (args.output_dir / "review_samples.jsonl").open("w", encoding="utf-8") as target:
        for row in sample_rows:
            inputs = tokenizer.apply_chat_template(
                row["prompt"], add_generation_prompt=True, tokenize=True,
                return_dict=True, return_tensors="pt",
            ).to("cuda")
            generated = model.generate(
                **inputs, max_new_tokens=384, do_sample=False, repetition_penalty=1.08,
            )
            prompt_length = inputs["input_ids"].shape[-1]
            answer = tokenizer.decode(generated[0][prompt_length:], skip_special_tokens=True).strip()
            payload = json.loads(row["prompt"][1]["content"])
            language = "bn" if payload["required_output_language"] == "Bengali" else "en"
            accepted = acceptable_answer(answer, records[(payload["service"], payload["topic"])], language)
            accepted_count += int(accepted)
            target.write(json.dumps({
                "question": payload["question"],
                "question_context": row["prompt"][1]["content"],
                "reference": row["completion"][0]["content"],
                "generated": answer,
                "automatic_gate": "pass" if accepted else "fail",
            }, ensure_ascii=False) + "\n")

    required_count = math.ceil(len(sample_rows) * 0.8)
    review_summary = {
        "recipe": RECIPE, "passed": accepted_count, "reviewed": len(sample_rows),
        "required_to_export": required_count,
    }
    (args.output_dir / "review_summary.json").write_text(
        json.dumps(review_summary, indent=2), encoding="utf-8",
    )
    print(f"Automatic review gate: {accepted_count}/{len(sample_rows)} passed")
    if accepted_count < required_count:
        raise RuntimeError(
            f"Answer quality gate failed ({accepted_count}/{len(sample_rows)}); GGUF was not exported. "
            "Inspect review_samples.jsonl."
        )

    if not args.skip_gguf:
        model.save_pretrained_gguf(
            str(args.output_dir / "gguf"), tokenizer, quantization_method="q4_k_m",
        )
        gguf_files = sorted(args.output_dir.glob("**/*Q4_K_M.gguf"))
        if not gguf_files:
            raise RuntimeError("GGUF export returned without a Q4_K_M file")
        print(f"GGUF: {gguf_files[-1]}")
    print(f"Training artifacts saved in {args.output_dir}")


if __name__ == "__main__":
    main()
