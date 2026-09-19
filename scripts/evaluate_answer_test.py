"""Evaluate the local answer pipeline on the frozen held-out answer test set."""

from __future__ import annotations

import argparse
import json
import time
from collections import Counter
from pathlib import Path

from scripts.export_answer_training import examples_for_split
from src.pipeline.service import QueryPipeline
from src.preprocessing.text_normalization import normalized_key
from src.response.facts import facts_for, render_fact
from src.response.local_generator import (
    LocalAnswerGenerator,
    acceptable_answer,
    configured_model_path,
    local_generator_ready,
)
from src.retrieval.corpus import load_records


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TEST = ROOT / "data" / "evaluation" / "answer_generation_test.jsonl"
DEFAULT_OUTPUT = ROOT / "models" / "evaluation" / "answer_generation_test_results.json"


def load_cases(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def training_questions() -> set[str]:
    questions = set()
    for split in ("train", "dev"):
        for example in examples_for_split(split):
            payload = json.loads(example["prompt"][1]["content"])
            questions.add(normalized_key(payload["question"]))
    return questions


def validate_cases(cases: list[dict]) -> None:
    records = {record["query_topic_id"]: record for record in load_records() if record["query_topic_id"]}
    expected_topics = set(records)
    case_topics = {case["query_topic_id"] for case in cases}
    ids = [case["id"] for case in cases]
    questions = [normalized_key(case["question"]) for case in cases]
    overlap = set(questions) & training_questions()
    errors = []
    if len(ids) != len(set(ids)):
        errors.append("duplicate case IDs")
    if len(questions) != len(set(questions)):
        errors.append("duplicate test questions")
    if case_topics != expected_topics:
        errors.append(
            f"topic coverage mismatch: missing={sorted(expected_topics - case_topics)}, "
            f"extra={sorted(case_topics - expected_topics)}"
        )
    if overlap:
        errors.append(f"{len(overlap)} exact questions overlap train/dev")
    if errors:
        raise ValueError("; ".join(errors))


class RoutingOnlyGenerator:
    def generate(self, question: str, record: dict, language: str) -> str:
        raise RuntimeError("generation is evaluated separately")


def evaluate_case(
    case: dict,
    pipeline: QueryPipeline,
    generator: LocalAnswerGenerator,
    records: dict[str, dict],
) -> dict:
    started = time.perf_counter()
    result = pipeline.analyze(case["question"])
    understanding = result["understanding"]
    response = result["response"]
    actual_topic = understanding.get("resolved_topic_id") or understanding.get("query_topic_id")
    record = records[case["query_topic_id"]]
    generated = response.get("body", "")
    generation_accepted = case["expected_answer_basis"] == "curated_source_facts"
    actual_basis = response.get("answer_basis")
    if case["expected_answer_basis"] == "local_finetuned_model":
        try:
            generated = generator.generate(
                case["question"], record, case["expected_language"],
            )
            generation_accepted = acceptable_answer(
                generated, record, case["expected_language"],
            )
            actual_basis = (
                "local_finetuned_model" if generation_accepted
                else "rejected_model_output"
            )
        except Exception as exc:
            generated = f"GENERATION ERROR: {type(exc).__name__}: {exc}"
            generation_accepted = False
            actual_basis = "generation_error"
    elapsed = time.perf_counter() - started
    checks = {
        "service": understanding.get("service") == case["service"],
        "topic": actual_topic == case["query_topic_id"],
        "language": response.get("language") == case["expected_language"],
        "answer_state": response.get("state") == "answer",
        "answer_basis": generation_accepted,
        "privacy_clean": not result["privacy_present"],
        "official_source": bool(response.get("source")),
    }
    reference = " ".join(
        render_fact(unit, case["expected_language"]) for unit in facts_for(record)
    )
    return {
        **case,
        "passed": all(checks.values()),
        "checks": checks,
        "actual_service": understanding.get("service"),
        "actual_topic_id": actual_topic,
        "actual_language": response.get("language"),
        "actual_answer_basis": actual_basis,
        "answer": generated,
        "reference": reference,
        "latency_seconds": round(elapsed, 3),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--test-file", type=Path, default=DEFAULT_TEST)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()

    cases = load_cases(args.test_file)
    validate_cases(cases)
    language_counts = Counter(case["expected_language"] for case in cases)
    service_counts = Counter(case["service"] for case in cases)
    print(f"Held-out set valid: {len(cases)} cases; languages={dict(language_counts)}")
    print(f"Service coverage: {dict(service_counts)}")
    if args.validate_only:
        return
    if not local_generator_ready():
        raise RuntimeError("Local GGUF answer generator is not ready")

    selected = cases[:args.limit] if args.limit else cases
    records = {record["query_topic_id"]: record for record in load_records() if record["query_topic_id"]}
    pipeline = QueryPipeline(answer_generator=RoutingOnlyGenerator())
    model_path = configured_model_path()
    if model_path is None:
        raise RuntimeError("GGUF path could not be resolved")
    generator = LocalAnswerGenerator(model_path)
    results = []
    for index, case in enumerate(selected, start=1):
        result = evaluate_case(case, pipeline, generator, records)
        results.append(result)
        print(
            f"[{index:02d}/{len(selected):02d}] {case['id']} "
            f"{'PASS' if result['passed'] else 'FAIL'} "
            f"basis={result['actual_answer_basis']} latency={result['latency_seconds']:.1f}s"
        )

    check_totals = {
        name: sum(int(result["checks"][name]) for result in results)
        for name in next(iter(results))["checks"]
    }
    passed = sum(int(result["passed"]) for result in results)
    model_results = [
        result for result in results
        if result["expected_answer_basis"] == "local_finetuned_model"
    ]
    model_accepted = sum(
        int(result["checks"]["answer_basis"]) for result in model_results
    )
    exact_topic_routes = check_totals["topic"]
    report = {
        "test_file": str(args.test_file.relative_to(ROOT)),
        "held_out_from_train_dev": True,
        "evaluated": len(results),
        "passed": passed,
        "pass_rate": passed / len(results),
        "model_cases": len(model_results),
        "model_answers_accepted": model_accepted,
        "generation_acceptance_rate": model_accepted / len(model_results),
        "exact_topic_routes": exact_topic_routes,
        "exact_topic_route_rate": exact_topic_routes / len(results),
        "check_totals": check_totals,
        "average_latency_seconds": sum(result["latency_seconds"] for result in results) / len(results),
        "results": results,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Overall: {passed}/{len(results)} ({report['pass_rate']:.1%})")
    print(
        f"Generation acceptance: {model_accepted}/{len(model_results)} "
        f"({report['generation_acceptance_rate']:.1%})"
    )
    print(
        f"Exact topic routing: {exact_topic_routes}/{len(results)} "
        f"({report['exact_topic_route_rate']:.1%})"
    )
    print(f"Report: {args.output}")


if __name__ == "__main__":
    main()
