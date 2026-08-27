#!/usr/bin/env python3
"""Merge RIS files and deduplicate conservatively.

Priority keys: DOI -> PMID -> normalized first author + year + title.
Records without enough metadata receive a content hash so unrelated empty records are never collapsed.
"""

from __future__ import annotations

import argparse
import hashlib
import re
import unicodedata
from pathlib import Path

FIELD_RE = re.compile(r"^([A-Z0-9]{2})  -\s?(.*)$")


def parse_records(text: str) -> list[list[str]]:
    records: list[list[str]] = []
    current: list[str] = []
    for raw in text.splitlines():
        line = raw.rstrip("\r\n")
        if line.startswith("TY  -"):
            if current:
                records.append(current)
            current = [line]
        elif current:
            current.append(line)
            if line.startswith("ER  -"):
                records.append(current)
                current = []
    if current:
        records.append(current)
    return records


def fields(record: list[str]) -> dict[str, list[str]]:
    result: dict[str, list[str]] = {}
    last_tag: str | None = None
    for line in record:
        match = FIELD_RE.match(line)
        if match:
            last_tag = match.group(1)
            result.setdefault(last_tag, []).append(match.group(2).strip())
        elif last_tag and line.strip():
            result[last_tag][-1] = f"{result[last_tag][-1]} {line.strip()}".strip()
    return result


def first(data: dict[str, list[str]], *tags: str) -> str:
    for tag in tags:
        values = data.get(tag)
        if values and values[0].strip():
            return values[0].strip()
    return ""


def normalize(value: str) -> str:
    value = unicodedata.normalize("NFKC", value).casefold()
    return "".join(char for char in value if char.isalnum())


def normalize_doi(value: str) -> str:
    value = value.strip().casefold()
    value = re.sub(r"^(?:doi:\s*|https?://(?:dx\.)?doi\.org/)", "", value)
    return value.rstrip(". ")


def record_key(record: list[str]) -> str:
    data = fields(record)
    doi = normalize_doi(first(data, "DO", "M1"))
    if doi:
        return f"doi:{doi}"

    identifiers = " ".join(data.get("ID", []) + data.get("AN", []) + data.get("N1", []))
    pmid = re.search(r"PMID\s*:?\s*(\d+)", identifiers, flags=re.I)
    if pmid:
        return f"pmid:{pmid.group(1)}"

    title = normalize(first(data, "TI", "T1", "CT"))
    year_match = re.search(r"(?:19|20)\d{2}", first(data, "PY", "Y1", "DA"))
    year = year_match.group(0) if year_match else ""
    author = normalize(first(data, "AU", "A1"))
    if title and (year or author):
        return f"fallback:{author[:32]}|{year}|{title[:160]}"

    digest = hashlib.sha256("\n".join(record).encode("utf-8", errors="replace")).hexdigest()
    return f"content:{digest}"


def main() -> None:
    parser = argparse.ArgumentParser(description="合并 RIS 并按 DOI、PMID、作者年份标题保守去重")
    parser.add_argument("files", nargs="+", help="输入 RIS 文件")
    parser.add_argument("--out", default="merged.ris")
    args = parser.parse_args()

    seen: set[str] = set()
    kept: list[list[str]] = []
    duplicates = 0
    stats: list[tuple[str, int, int]] = []

    for filename in args.files:
        records = parse_records(Path(filename).read_text(encoding="utf-8-sig", errors="replace"))
        added = 0
        for record in records:
            key = record_key(record)
            if key in seen:
                duplicates += 1
                continue
            seen.add(key)
            kept.append(record)
            added += 1
        stats.append((filename, len(records), added))

    output = "\n\n".join("\n".join(record) for record in kept)
    if output:
        output += "\n"
    Path(args.out).write_text(output, encoding="utf-8")

    print("各文件：输入 / 新增保留")
    for filename, total, added in stats:
        print(f"  {filename}: {total} / {added}")
    print(f"合计保留 {len(kept)} 条，去除重复 {duplicates} 条 -> {args.out}")


if __name__ == "__main__":
    main()

