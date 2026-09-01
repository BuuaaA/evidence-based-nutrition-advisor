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
    "pmcid",
    "access_candidates",
    "full_text_access_attempts",
    "access_checked_at",
    "title",
    "year",
    "publication_types",
    "screening_priority",
    "triage_hints",
    "abstract",
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


def triage(title: str, abstract: str, publication_types: str) -> tuple[str, str]:
    """Prioritize reading without making an inclusion or exclusion decision."""
    text = " ".join((title, abstract, publication_types)).lower()
    hints: list[str] = []
    if any(term in text for term in ("randomized", "randomised", "clinical trial", "controlled trial")):
        hints.append("可能为人体对照试验")
    if any(term in text for term in ("systematic review", "meta-analysis", "meta analysis")):
        hints.append("可能为证据综合")
    if any(term in text for term in ("protocol", "study protocol")):
        hints.append("可能为方案文献")
    if any(term in text for term in ("mice", "mouse", "rats", "murine", "in vitro", "cell line")):
        hints.append("可能为非人体研究")
    priority = "high" if hints and hints[0] in ("可能为人体对照试验", "可能为证据综合") else "normal"
    return priority, "；".join(hints)


def pmid(data: dict[str, list[str]]) -> str:
    identifiers = " ".join(data.get("ID", []) + data.get("AN", []) + data.get("N1", []))
    match = re.search(r"PMID\s*:?\s*(\d+)", identifiers, flags=re.I)
    return match.group(1) if match else ""


def pmcid(data: dict[str, list[str]]) -> str:
    identifiers = " ".join(data.get("ID", []) + data.get("AN", []) + data.get("N1", []))
    match = re.search(r"PMCID\s*:?\s*(PMC\d+)", identifiers, flags=re.I)
    return match.group(1).upper() if match else ""


def access_candidates(record_pmid: str, record_doi: str, record_pmcid: str) -> str:
    candidates: list[str] = []
    if record_pmcid:
        candidates.append(f"https://pmc.ncbi.nlm.nih.gov/articles/{record_pmcid}/")
    if record_doi:
        candidates.append(f"https://doi.org/{record_doi}")
    if record_pmid:
        candidates.append(f"https://pubmed.ncbi.nlm.nih.gov/{record_pmid}/")
    return "; ".join(candidates)


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
        title = first(data, "TI", "T1", "CT")
        abstract = first(data, "AB")
        publication_types = "；".join(data.get("M3", []))
        record_pmid = pmid(data)
        record_doi = first(data, "DO", "M1")
        record_pmcid = pmcid(data)
        priority, hints = triage(title, abstract, publication_types)
        row = {header: "" for header in HEADERS}
        row.update(
            {
                "record_id": str(index),
                "pmid": record_pmid,
                "doi": record_doi,
                "pmcid": record_pmcid,
                "access_candidates": access_candidates(record_pmid, record_doi, record_pmcid),
                "title": title,
                "year": first(data, "PY", "Y1", "DA")[:4],
                "publication_types": publication_types,
                "screening_priority": priority,
                "triage_hints": hints,
                "abstract": abstract,
            }
        )
        rows.append(row)
        sections.extend(
            [
                f"## {index}. PMID {row['pmid']} ({row['year']})",
                "",
                row["title"],
                "",
                f"Priority: {priority}; hints: {hints or 'none'}",
                f"Access candidates: {row['access_candidates'] or 'none'}",
                "",
                abstract or "[No abstract in RIS]",
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
