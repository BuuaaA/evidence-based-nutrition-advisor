"""Convert a PubMed RIS export into a screening CSV draft and readable inspection file."""

from __future__ import annotations

import argparse
import csv
import re
from pathlib import Path

from ris_dedup import fields, first, parse_records


HEADERS = [
    "record_id",
    "pmid",
    "doi",
    "title",
    "year",
    "title_abstract_decision",
    "title_abstract_reason",
    "full_text_status",
    "full_text_decision",
    "full_text_exclusion_reason",
    "study_id",
    "study_design",
    "key_outcomes",
    "notes",
]


def pmid(data: dict[str, list[str]]) -> str:
    identifiers = " ".join(data.get("ID", []) + data.get("AN", []) + data.get("N1", []))
    match = re.search(r"PMID\s*:?\s*(\d+)", identifiers, flags=re.I)
    return match.group(1) if match else ""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ris", type=Path)
    parser.add_argument("--csv", type=Path, required=True)
    parser.add_argument("--inspection", type=Path, required=True)
    args = parser.parse_args()

    records = parse_records(args.ris.read_text(encoding="utf-8-sig", errors="replace"))
    rows: list[dict[str, str]] = []
    sections: list[str] = [f"# Screening inspection: {args.ris.name}\n"]
    for index, record in enumerate(records, 1):
        data = fields(record)
        row = {header: "" for header in HEADERS}
        row.update(
            {
                "record_id": str(index),
                "pmid": pmid(data),
                "doi": first(data, "DO", "M1"),
                "title": first(data, "TI", "T1", "CT"),
                "year": first(data, "PY", "Y1", "DA")[:4],
            }
        )
        rows.append(row)
        sections.extend(
            [
                f"## {index}. PMID {row['pmid']} ({row['year']})",
                "",
                row["title"],
                "",
                first(data, "AB") or "[No abstract in RIS]",
                "",
            ]
        )

    args.csv.parent.mkdir(parents=True, exist_ok=True)
    with args.csv.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=HEADERS)
        writer.writeheader()
        writer.writerows(rows)
    args.inspection.write_text("\n".join(sections), encoding="utf-8")
    print(f"Wrote {len(rows)} records to {args.csv} and {args.inspection}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
