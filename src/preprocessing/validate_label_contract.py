"""Validate exact agreement between the shared contract and taxonomies."""

from pathlib import Path
import sys

import yaml


ROOT = Path(__file__).resolve().parents[2]
FILES = ["nid.yaml", "birth_registration.yaml", "passport.yaml", "tax.yaml", "police_gd.yaml", "driving_licence.yaml"]
EXPECTED_SERVICES = {"NID", "BIRTH_REGISTRATION", "PASSPORT", "TAX", "POLICE_GD", "DRIVING_LICENCE"}


def main() -> None:
    errors = []
    contract = yaml.safe_load((ROOT / "contracts" / "labels.yaml").read_text(encoding="utf-8"))
    taxonomies = {
        data["service_id"]: data
        for data in [yaml.safe_load((ROOT / "taxonomy" / name).read_text(encoding="utf-8")) for name in FILES]
    }
    if set(contract.get("services", {})) != EXPECTED_SERVICES: errors.append("Contract service set mismatch")
    if contract.get("priority_labels") != ["Low", "Medium", "High"]: errors.append("Priority labels mismatch")
    if contract.get("status") != "frozen" or contract.get("freeze", {}).get("shared_contract_frozen") is not True: errors.append("Contract is not frozen")
    parents = leaves = 0
    all_parent_ids = []
    all_leaf_ids = []
    for service, taxonomy in taxonomies.items():
        entry = contract.get("services", {}).get(service, {})
        contract_parents = entry.get("parent_topics", {})
        taxonomy_parents = taxonomy["parent_topics"]
        if set(contract_parents) != set(taxonomy_parents): errors.append(f"{service}: parent set mismatch")
        for parent_id, parent in taxonomy_parents.items():
            parents += 1; all_parent_ids.append(parent_id)
            expected_leaves = parent["query_topics"]
            actual_leaves = contract_parents.get(parent_id, {}).get("query_topics", {})
            if set(actual_leaves) != set(expected_leaves): errors.append(f"{parent_id}: query-topic set mismatch")
            for leaf_id, leaf in expected_leaves.items():
                leaves += 1; all_leaf_ids.append(leaf_id)
                if actual_leaves.get(leaf_id, {}).get("display_name") != leaf["display_name"]: errors.append(f"{leaf_id}: display-name mismatch")
        if taxonomy.get("freeze_status", {}).get("shared_contract_frozen") is not True: errors.append(f"{service}: taxonomy freeze flag is not true")
    if len(all_parent_ids) != len(set(all_parent_ids)): errors.append("Duplicate parent IDs across services")
    if len(all_leaf_ids) != len(set(all_leaf_ids)): errors.append("Duplicate leaf IDs across services")
    print("=" * 72); print("SIX-SERVICE LABEL CONTRACT VALIDATION"); print("=" * 72)
    print("Contract version/status:", contract.get("contract_version"), "/", contract.get("status"))
    print("Services:", len(contract.get("services", {}))); print("Parents:", parents); print("Query topics:", leaves)
    print("Priorities:", contract.get("priority_labels")); print("Frozen:", contract.get("freeze", {}).get("shared_contract_frozen"))
    if errors:
        print("RESULT: FAIL"); [print("ERROR:", error) for error in errors]; sys.exit(1)
    print("RESULT: PASS")


if __name__ == "__main__": main()
