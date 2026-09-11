import csv
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]

CSV_PATH = (
    ROOT
    / "data"
    / "annotations"
    / "birth_registration_expanded_v0_2.csv"
)


REPAIRS = {
    "BRQ_0136":
        "birth registration office niye na, online apply process ta ki?",

    "BRQ_0144":
        "birth registration er address field na, office selection ta kivabe korbo?",

    "BRQ_0152":
        "local office na, birth registration embassy diye apply korte chai",

    "BRQ_0182":
        "birth registration applicant relation option e konta select korbo?",

    "BRQ_0190":
        "birth registration er required kagojpotro gula ki ki?",

    "BRQ_0204":
        "birth registration er otp sms ashche na, ki kori?",

    "BRQ_0208":
        "birth registration verification code receive kori nai, etai problem",

    "BRQ_0212":
        "birth registration otp code diyeo accept kortese na keno?",

    "BRQ_0214":
        "birth registration er otp ase but verification fail hocche",

    "BRQ_0220":
        "birth registration form submit dile data final hoye jabe?",

    "BRQ_0236":
        "birth registration e name spelling vul, correct korbo kivabe?",

    "BRQ_0246":
        "birth registration er DOB ta correct korte hobe",

    "BRQ_0254":
        "birth registration er gender info ta change korte chai",

    "BRQ_0260":
        "birth registration e mother name spelling thik korbo kivabe?",

    "BRQ_0276":
        "birth registration er present address ta correct korte chai",

    "BRQ_0284":
        "birth registration application approve hoise kina check korbo kivabe?",

    "BRQ_0292":
        "onek din holo birth registration application update nai",

    "BRQ_0304":
        "amar application na, birth registration er normal time limit ta ki?",

    "BRQ_0308":
        "submitted birth registration application form er copy chai",

    "BRQ_0316":
        "birth certificate abar print korte chai",

    "BRQ_0332":
        "birth registration verify korle no result ase",

    "BRQ_0342":
        "birth certificate cancel application kothay submit korbo?",

    "BRQ_0350":
        "birth certificate reprint korte fee koto lage?",

    "BRQ_0352":
        "birth registration correction process na, correction fee amount jante chai",
}


def main():
    if not CSV_PATH.exists():
        raise FileNotFoundError(
            f"Dataset not found: {CSV_PATH}"
        )

    with CSV_PATH.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as handle:
        reader = csv.DictReader(handle)
        fieldnames = reader.fieldnames
        rows = list(reader)

    if not fieldnames:
        raise RuntimeError(
            "CSV header was not found."
        )

    row_lookup = {}

    for row in rows:
        row_id = row["id"]

        if row_id in row_lookup:
            raise RuntimeError(
                f"Duplicate row ID: {row_id}"
            )

        row_lookup[row_id] = row

    missing = (
        set(REPAIRS)
        - set(row_lookup)
    )

    if missing:
        raise RuntimeError(
            "Repair targets missing from dataset: "
            + ", ".join(sorted(missing))
        )

    print("=" * 72)
    print(
        "BIRTH REGISTRATION v0.2 "
        "SERVICE-CONTEXT REPAIR"
    )
    print("=" * 72)

    changed = 0

    for row_id, new_text in REPAIRS.items():
        row = row_lookup[row_id]

        old_text = row["text"]

        if old_text == new_text:
            print(
                f"{row_id}: already repaired"
            )
            continue

        row["text"] = new_text
        changed += 1

        print()
        print(row_id)
        print(f"OLD: {old_text}")
        print(f"NEW: {new_text}")

    if changed not in {0, 24}:
        raise RuntimeError(
            "Expected either 24 repairs "
            f"or an already-repaired dataset; "
            f"changed {changed} rows."
        )

    normalized_texts = [
        " ".join(
            row["text"]
            .strip()
            .lower()
            .split()
        )
        for row in rows
    ]

    if len(normalized_texts) != len(
        set(normalized_texts)
    ):
        raise RuntimeError(
            "Repair introduced duplicate "
            "normalized query text."
        )

    temp_path = CSV_PATH.with_suffix(
        ".csv.tmp"
    )

    with temp_path.open(
        "w",
        encoding="utf-8-sig",
        newline="",
    ) as handle:

        writer = csv.DictWriter(
            handle,
            fieldnames=fieldnames,
        )

        writer.writeheader()
        writer.writerows(rows)

    temp_path.replace(CSV_PATH)

    print()
    print("=" * 72)
    print(f"Rows repaired: {changed}")
    print(f"Repair targets: {len(REPAIRS)}")
    print(f"Total dataset rows: {len(rows)}")
    print(
        "STATUS: SERVICE-CONTEXT "
        "REPAIR COMPLETED"
    )
    print("=" * 72)


if __name__ == "__main__":
    main()