"""Generate the shared label contract from the six reviewed taxonomies."""

from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]
TAXONOMIES = [
    "nid.yaml", "birth_registration.yaml", "passport.yaml",
    "tax.yaml", "police_gd.yaml", "driving_licence.yaml",
]
DISPLAY_NAMES = {
    "NID": "NID", "BIRTH_REGISTRATION": "Birth Registration",
    "PASSPORT": "Passport", "TAX": "Tax", "POLICE_GD": "Police GD",
    "DRIVING_LICENCE": "Driving Licence",
}


def main() -> None:
    services = {}
    for filename in TAXONOMIES:
        taxonomy = yaml.safe_load((ROOT / "taxonomy" / filename).read_text(encoding="utf-8"))
        service_id = taxonomy["service_id"]
        parents = {}
        for parent_id, parent in taxonomy["parent_topics"].items():
            parents[parent_id] = {
                "display_name": parent["display_name"],
                "query_topics": {
                    leaf_id: {"display_name": leaf["display_name"]}
                    for leaf_id, leaf in parent["query_topics"].items()
                },
            }
        services[service_id] = {
            "display_name": DISPLAY_NAMES[service_id],
            "taxonomy_version": taxonomy["taxonomy_version"],
            "parent_topics": parents,
        }
    contract = {
        "contract_version": "2.0.0",
        "status": "frozen",
        "services": services,
        "priority_labels": ["Low", "Medium", "High"],
        "freeze": {
            "shared_contract_frozen": True,
            "source": "Generated deterministically from six reviewed taxonomy YAML files.",
        },
    }
    path = ROOT / "contracts" / "labels.yaml"
    path.write_text(
        yaml.safe_dump(contract, sort_keys=False, allow_unicode=True, width=100),
        encoding="utf-8",
    )
    print("Contract written:", path)
    print("Services:", len(services))
    print("Parents:", sum(len(x["parent_topics"]) for x in services.values()))
    print("Query topics:", sum(len(p["query_topics"]) for x in services.values() for p in x["parent_topics"].values()))


if __name__ == "__main__":
    main()
