#!/usr/bin/env python3
"""Validate and query local, versioned nutrition evidence packs.

The fast path is deliberately network-free. A fresh pack is a previously
completed L1 audit, not a model-memory answer. Live PubMed work is routed by
the skill only when this tool reports stale or missing.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


SCHEMA = "nutrition-evidence-pack-v1"
EXIT_STALE = 2
EXIT_MISSING = 3
EXIT_INVALID = 4

# Windows may otherwise encode redirected output as the active ANSI code page,
# which makes deterministic JSON consumption fail across hosts.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")


class PackError(ValueError):
    pass


def parse_day(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise PackError(f"invalid ISO date: {value}") from exc


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PackError(f"cannot read JSON {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise PackError(f"JSON root must be an object: {path}")
    return value


def required(obj: dict[str, Any], key: str, kind: type, where: str) -> Any:
    value = obj.get(key)
    if not isinstance(value, kind) or (kind is str and not value.strip()):
        raise PackError(f"{where}.{key} must be a non-empty {kind.__name__}")
    return value


def forbidden_keys(value: Any, path: str = "pack") -> list[str]:
    forbidden = {
        "user_name", "patient_name", "email", "phone", "address",
        "intake_summary", "health_profile", "medical_record", "patient_id",
    }
    found: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            if key in forbidden:
                found.append(f"{path}.{key}")
            found.extend(forbidden_keys(child, f"{path}.{key}"))
    elif isinstance(value, list):
        for i, child in enumerate(value):
            found.extend(forbidden_keys(child, f"{path}[{i}]"))
    return found


def load_index(index_path: Path) -> dict[str, Any]:
    index = read_json(index_path)
    if index.get("schema_version") != "nutrition-evidence-index-v1":
        raise PackError("unsupported evidence index schema")
    topics = required(index, "topics", list, "index")
    seen: set[str] = set()
    for i, entry in enumerate(topics):
        if not isinstance(entry, dict):
            raise PackError(f"index.topics[{i}] must be an object")
        topic_id = required(entry, "topic_id", str, f"index.topics[{i}]")
        required(entry, "pack", str, f"index.topics[{i}]")
        if topic_id in seen:
            raise PackError(f"duplicate topic_id: {topic_id}")
        seen.add(topic_id)
    return index


def validate_pack(pack: dict[str, Any], expected_id: str | None = None) -> None:
    if pack.get("schema_version") != SCHEMA:
        raise PackError("unsupported evidence pack schema")
    topic_id = required(pack, "topic_id", str, "pack")
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", topic_id):
        raise PackError("pack.topic_id must use lowercase letters, digits, and hyphens")
    if expected_id and topic_id != expected_id:
        raise PackError(f"topic id mismatch: expected {expected_id}, got {topic_id}")
    required(pack, "title", str, "pack")
    aliases = required(pack, "aliases", list, "pack")
    if not aliases or not all(isinstance(item, str) and item.strip() for item in aliases):
        raise PackError("pack.aliases must contain non-empty strings")
    scope = required(pack, "scope", dict, "pack")
    required(scope, "population", str, "pack.scope")
    required(scope, "intervention", str, "pack.scope")
    outcomes = required(scope, "outcomes", list, "pack.scope")
    if not outcomes:
        raise PackError("pack.scope.outcomes cannot be empty")
    searched = parse_day(required(pack, "searched_at", str, "pack"))
    valid_until = parse_day(required(pack, "valid_until", str, "pack"))
    if valid_until < searched:
        raise PackError("valid_until cannot precede searched_at")
    freshness_days = pack.get("freshness_days")
    if not isinstance(freshness_days, int) or freshness_days < 1:
        raise PackError("pack.freshness_days must be a positive integer")
    if valid_until > searched + timedelta(days=freshness_days):
        raise PackError("valid_until exceeds declared freshness_days")

    passport = required(pack, "evidence_passport", dict, "pack")
    required(passport, "audit_level", str, "pack.evidence_passport")
    required(passport, "database", str, "pack.evidence_passport")
    required(passport, "historical_base", str, "pack.evidence_passport")
    required(passport, "certainty_method", str, "pack.evidence_passport")
    required(passport, "certainty_summary", str, "pack.evidence_passport")
    required(passport, "coverage_limits", str, "pack.evidence_passport")
    for key in ("records_found", "records_exported", "records_screened"):
        value = passport.get(key)
        if not isinstance(value, int) or value < 0:
            raise PackError(f"pack.evidence_passport.{key} must be a non-negative integer")
    found = passport["records_found"]
    exported = passport["records_exported"]
    screened = passport["records_screened"]
    if not (found == exported == screened):
        raise PackError("fresh packs require complete export and screening counts")
    unavailable = passport.get("full_text_unavailable")
    if not isinstance(unavailable, int) or unavailable < 0:
        raise PackError("pack.evidence_passport.full_text_unavailable must be a non-negative integer")
    sources = required(passport, "sources", list, "pack.evidence_passport")
    if not sources:
        raise PackError("evidence passport must include at least one source")
    for i, source in enumerate(sources):
        if not isinstance(source, dict):
            raise PackError(f"source {i} must be an object")
        required(source, "label", str, f"source[{i}]")
        url = required(source, "url", str, f"source[{i}]")
        if urlparse(url).scheme not in {"http", "https"}:
            raise PackError(f"source {i} URL must use http or https")

    pubmed = required(pack, "pubmed", dict, "pack")
    required(pubmed, "base_query", str, "pack.pubmed")
    parse_day(required(pubmed, "last_search_end", str, "pack.pubmed"))
    decisions = required(pack, "decision_matrix", list, "pack")
    if not decisions:
        raise PackError("pack.decision_matrix cannot be empty")
    allowed_verdicts = {"priority", "conditional", "trial", "not_worth", "avoid", "uncertain"}
    for i, decision in enumerate(decisions):
        if not isinstance(decision, dict):
            raise PackError(f"pack.decision_matrix[{i}] must be an object")
        required(decision, "match", str, f"pack.decision_matrix[{i}]")
        verdict = required(decision, "verdict", str, f"pack.decision_matrix[{i}]")
        if verdict not in allowed_verdicts:
            raise PackError(f"unsupported verdict: {verdict}")
    required(pack, "safety_rules", list, "pack")
    boundaries = required(pack, "product_boundaries", list, "pack")
    if not boundaries:
        raise PackError("pack.product_boundaries cannot be empty")

    # Packs are reusable topic assets, never personal answers or health profiles.
    allowed = {
        "schema_version", "topic_id", "title", "aliases", "scope",
        "freshness_days", "searched_at", "valid_until", "evidence_passport",
        "pubmed", "safety_rules", "decision_matrix", "product_boundaries",
    }
    extras = set(pack).difference(allowed)
    if extras:
        raise PackError(f"unsupported top-level fields: {sorted(extras)}")
    personal = forbidden_keys(pack)
    if personal:
        raise PackError(f"personal fields are forbidden in evidence packs: {personal}")


def empty_index() -> dict[str, Any]:
    return {"schema_version": "nutrition-evidence-index-v1", "updated": None, "topics": []}


def register_pack(index_path: Path, source_path: Path) -> dict[str, Any]:
    pack = read_json(source_path)
    validate_pack(pack)
    index = load_index(index_path) if index_path.exists() else empty_index()
    index_path.parent.mkdir(parents=True, exist_ok=True)
    destination = index_path.parent / "packs" / pack["topic_id"] / "pack.json"
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary_pack = destination.with_suffix(".json.tmp")
    temporary_pack.write_text(json.dumps(pack, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary_pack.replace(destination)

    relative = destination.relative_to(index_path.parent).as_posix()
    entry = {
        "topic_id": pack["topic_id"],
        "title": pack["title"],
        "aliases": pack["aliases"],
        "pack": relative,
    }
    topics = [item for item in index["topics"] if item["topic_id"] != pack["topic_id"]]
    topics.append(entry)
    topics.sort(key=lambda item: item["topic_id"])
    index["topics"] = topics
    index["updated"] = date.today().isoformat()
    temporary_index = index_path.with_suffix(".json.tmp")
    temporary_index.write_text(json.dumps(index, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary_index.replace(index_path)
    return {"status": "registered", "topic_id": pack["topic_id"], "index": str(index_path), "pack": str(destination)}


def resolve_pack(index_path: Path, topic_id: str) -> tuple[dict[str, Any], Path]:
    index = load_index(index_path)
    entry = next((x for x in index["topics"] if x["topic_id"] == topic_id), None)
    if entry is None:
        raise KeyError(topic_id)
    pack_path = (index_path.parent / entry["pack"]).resolve()
    try:
        pack_path.relative_to(index_path.parent.resolve())
    except ValueError as exc:
        raise PackError("pack path escapes evidence-cache directory") from exc
    pack = read_json(pack_path)
    validate_pack(pack, topic_id)
    return pack, pack_path


def incremental_query(pack: dict[str, Any], as_of: date) -> dict[str, Any]:
    last_end = parse_day(pack["pubmed"]["last_search_end"])
    start = last_end + timedelta(days=1)
    if start > as_of:
        date_clause = None
        query = None
    else:
        date_clause = f'("{start.isoformat()}"[Date - Publication] : "{as_of.isoformat()}"[Date - Publication])'
        query = f'({pack["pubmed"]["base_query"]}) AND {date_clause}'
    return {
        "topic_id": pack["topic_id"],
        "last_search_end": last_end.isoformat(),
        "incremental_start": start.isoformat(),
        "incremental_end": as_of.isoformat(),
        "date_clause": date_clause,
        "query": query,
        "no_new_date_window": query is None,
    }


def lookup(index_path: Path, topic_id: str, as_of: date) -> tuple[dict[str, Any], int]:
    try:
        pack, pack_path = resolve_pack(index_path, topic_id)
    except KeyError:
        return {
            "status": "missing",
            "topic_id": topic_id,
            "route": "quick_l1",
            "reason": "No validated local evidence pack matches this topic.",
        }, EXIT_MISSING

    stale = as_of > parse_day(pack["valid_until"])
    result = {
        "status": "stale" if stale else "fresh",
        "topic_id": topic_id,
        "route": "quick_l1_then_incremental_audit" if stale else "cached_audited_l1",
        "pack_path": str(pack_path),
        "as_of": as_of.isoformat(),
        "searched_at": pack["searched_at"],
        "valid_until": pack["valid_until"],
        "scope": pack["scope"],
        "verdict_options": pack["decision_matrix"],
        "safety_rules": pack["safety_rules"],
        "product_boundaries": pack["product_boundaries"],
        "evidence_passport": pack["evidence_passport"],
        "incremental_update": incremental_query(pack, as_of),
        "instruction": (
            "Answer now from this validated pack after checking scope and product match; do not browse first."
            if not stale
            else "Do not make a fresh efficacy or purchase claim until the incremental update is complete."
        ),
    }
    return result, EXIT_STALE if stale else 0


def emit(value: Any) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--index",
        type=Path,
        help="Runtime index path. Defaults to evidence-cache/index.local.json next to the skill.",
    )
    sub = parser.add_subparsers(dest="command", required=True)
    p_lookup = sub.add_parser("lookup")
    p_lookup.add_argument("--topic", required=True)
    p_lookup.add_argument("--as-of", default=date.today().isoformat())
    p_inc = sub.add_parser("incremental-query")
    p_inc.add_argument("--topic", required=True)
    p_inc.add_argument("--as-of", default=date.today().isoformat())
    p_register = sub.add_parser("register")
    p_register.add_argument("--pack", type=Path, required=True)
    sub.add_parser("validate")
    sub.add_parser("list")
    args = parser.parse_args(argv)
    default_index = Path(__file__).resolve().parents[1] / "evidence-cache" / "index.local.json"
    index_path = args.index or default_index

    try:
        as_of = parse_day(args.as_of) if hasattr(args, "as_of") else date.today()
        if args.command == "validate":
            if not index_path.exists() and args.index is None:
                emit({"status": "valid", "topics": 0, "index": str(index_path)})
                return 0
            index = load_index(index_path)
            for entry in index["topics"]:
                resolve_pack(index_path, entry["topic_id"])
            emit({"status": "valid", "topics": len(index["topics"])})
            return 0
        if args.command == "list":
            index = load_index(index_path) if index_path.exists() else empty_index()
            emit({"topics": index["topics"]})
            return 0
        if args.command == "register":
            emit(register_pack(index_path, args.pack))
            return 0
        if args.command == "lookup":
            if not index_path.exists():
                emit({"status": "missing", "topic_id": args.topic, "route": "quick_l1", "reason": "Runtime evidence cache is empty."})
                return EXIT_MISSING
            result, code = lookup(index_path, args.topic, as_of)
            emit(result)
            return code
        pack, _ = resolve_pack(index_path, args.topic)
        emit(incremental_query(pack, as_of))
        return 0
    except PackError as exc:
        emit({"status": "invalid", "error": str(exc)})
        return EXIT_INVALID


if __name__ == "__main__":
    sys.exit(main())
