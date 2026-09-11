"""Reconcile stale readiness metadata and record the six-service freeze."""

from pathlib import Path
import argparse

import yaml


ROOT = Path(__file__).resolve().parents[2]
FILES = [
    "nid.yaml", "birth_registration.yaml", "passport.yaml",
    "tax.yaml", "police_gd.yaml", "driving_licence.yaml",
]
DESCRIPTIONS = {
    "NID": "Reviewed NID and voter-service taxonomy with 9 parent topics, 73 query-topic intents, complete inclusion/exclusion boundaries and a validated synthetic pre-training core.",
    "BIRTH_REGISTRATION": "Reviewed Birth Registration taxonomy with 8 parent topics, 30 query-topic intents and validated pilot and expanded datasets.",
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("stage", choices=["ready", "freeze"])
    args = parser.parse_args()
    if args.stage == "freeze" and not (ROOT / "contracts" / "labels.yaml").exists():
        raise FileNotFoundError("Build and validate contracts/labels.yaml before freezing")

    for filename in FILES:
        path = ROOT / "taxonomy" / filename
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        service = data["service_id"]
        if service in DESCRIPTIONS:
            data["description"] = DESCRIPTIONS[service]
        data["status"] = "contract_frozen" if args.stage == "freeze" else "contract_ready"
        data["freeze_status"] = {
            "shared_contract_frozen": args.stage == "freeze",
            "parent_topics_reviewed": True,
            "query_topics_defined": True,
            "inclusion_exclusion_rules_defined": True,
            "semantic_audit_passed": True,
            "pilot_dataset_created": True,
            "taxonomy_ready_for_shared_contract": True,
        }
        path.write_text(
            yaml.safe_dump(data, sort_keys=False, allow_unicode=True, width=92),
            encoding="utf-8",
        )
        print(service, data["status"], data["freeze_status"])


if __name__ == "__main__":
    main()
