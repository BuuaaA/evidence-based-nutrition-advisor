#!/usr/bin/env python3
"""Search PubMed with E-utilities and export complete citation metadata plus abstracts to RIS.

Examples:
  python pubmed_search.py --query '(fish oils[mh] OR fish oil[tiab] OR omega-3[tiab])' --out hits.ris --manifest search.json
  python pubmed_search.py --count '(phosphatidylserine[tiab] OR phosphatidyl serine[tiab])'
  python pubmed_search.py --mesh 'phosphatidylserine'

The script deliberately uses EFetch for PubMed records. ESummary returns document summaries
and should not be relied on for abstract text.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
TOOL = "evidence_based_nutrition_advisor"
USER_AGENT = "evidence-based-nutrition-advisor/2.0 (NCBI E-utilities)"
PUBMED_ESEARCH_LIMIT = 10_000


def _params(args: argparse.Namespace, extra: dict[str, object]) -> dict[str, object]:
    params: dict[str, object] = {"tool": TOOL, **extra}
    if getattr(args, "email", None):
        params["email"] = args.email
    if getattr(args, "api_key", None):
        params["api_key"] = args.api_key
    return params


def _request(endpoint: str, params: dict[str, object], *, as_json: bool = False):
    data = urllib.parse.urlencode(params).encode("utf-8")
    req = urllib.request.Request(
        f"{BASE}/{endpoint}", data=data, headers={"User-Agent": USER_AGENT}
    )
    with urllib.request.urlopen(req, timeout=90) as response:
        raw = response.read()
    if as_json:
        return json.loads(raw.decode("utf-8"))
    return raw


def _pause(args: argparse.Namespace) -> None:
    time.sleep(0.11 if args.api_key else 0.34)


def _text(node: ET.Element | None) -> str:
    if node is None:
        return ""
    return " ".join("".join(node.itertext()).split())


def _year(article: ET.Element) -> str:
    candidates = [
        article.find(".//ArticleDate/Year"),
        article.find(".//JournalIssue/PubDate/Year"),
        article.find(".//DateCompleted/Year"),
        article.find(".//DateRevised/Year"),
    ]
    for node in candidates:
        value = _text(node)
        if re.fullmatch(r"\d{4}", value):
            return value
    medline_date = _text(article.find(".//JournalIssue/PubDate/MedlineDate"))
    match = re.search(r"(?:19|20)\d{2}", medline_date)
    return match.group(0) if match else ""


def _authors(article: ET.Element) -> list[str]:
    result: list[str] = []
    for author in article.findall(".//Article/AuthorList/Author"):
        collective = _text(author.find("CollectiveName"))
        if collective:
            result.append(collective)
            continue
        last = _text(author.find("LastName"))
        initials = _text(author.find("Initials"))
        fore = _text(author.find("ForeName"))
        if last:
            result.append(f"{last}, {initials or fore}".strip().rstrip(","))
    return result


def _abstract(article: ET.Element) -> str:
    sections: list[str] = []
    for item in article.findall(".//Article/Abstract/AbstractText"):
        body = _text(item)
        if not body:
            continue
        label = (item.attrib.get("Label") or item.attrib.get("NlmCategory") or "").strip()
        sections.append(f"{label}: {body}" if label else body)
    return " ".join(sections)


def _doi(article: ET.Element) -> str:
    for item in article.findall(".//PubmedData/ArticleIdList/ArticleId"):
        if item.attrib.get("IdType", "").lower() == "doi":
            return _text(item)
    for item in article.findall(".//Article/ELocationID"):
        if item.attrib.get("EIdType", "").lower() == "doi":
            return _text(item)
    return ""


def parse_pubmed_xml(raw: bytes) -> list[dict[str, object]]:
    root = ET.fromstring(raw)
    records: list[dict[str, object]] = []
    for article in root.findall(".//PubmedArticle"):
        pmid = _text(article.find(".//MedlineCitation/PMID"))
        records.append(
            {
                "pmid": pmid,
                "title": _text(article.find(".//Article/ArticleTitle")),
                "authors": _authors(article),
                "journal": _text(article.find(".//Article/Journal/Title")),
                "year": _year(article),
                "volume": _text(article.find(".//Article/Journal/JournalIssue/Volume")),
                "issue": _text(article.find(".//Article/Journal/JournalIssue/Issue")),
                "pages": _text(article.find(".//Article/Pagination/MedlinePgn")),
                "doi": _doi(article),
                "abstract": _abstract(article),
            }
        )
    return records


def _ris_value(value: object) -> str:
    return " ".join(str(value or "").replace("\x00", "").split())


def to_ris(records: list[dict[str, object]]) -> str:
    lines: list[str] = []
    for item in records:
        lines.append("TY  - JOUR")
        for author in item.get("authors", []):
            lines.append(f"AU  - {_ris_value(author)}")
        fields = [
            ("TI", item.get("title")),
            ("JO", item.get("journal")),
            ("PY", item.get("year")),
            ("VL", item.get("volume")),
            ("IS", item.get("issue")),
            ("SP", item.get("pages")),
            ("DO", item.get("doi")),
            ("AB", item.get("abstract")),
        ]
        for tag, value in fields:
            cleaned = _ris_value(value)
            if cleaned:
                lines.append(f"{tag}  - {cleaned}")
        if item.get("pmid"):
            lines.append(f"ID  - PMID:{_ris_value(item['pmid'])}")
            lines.append(f"UR  - https://pubmed.ncbi.nlm.nih.gov/{_ris_value(item['pmid'])}/")
        lines.append("ER  - ")
        lines.append("")
    return "\n".join(lines)


def cmd_count(args: argparse.Namespace) -> None:
    data = _request(
        "esearch.fcgi",
        _params(args, {"db": "pubmed", "retmode": "json", "retmax": 0, "term": args.count}),
        as_json=True,
    )
    result = data["esearchresult"]
    print(f"命中：{result.get('count', '0')} 条")
    print("Query Translation：")
    print(result.get("querytranslation", ""))
    warnings = result.get("warninglist") or {}
    if warnings:
        print("Warnings：", json.dumps(warnings, ensure_ascii=False))


def cmd_mesh(args: argparse.Namespace) -> None:
    data = _request(
        "esearch.fcgi",
        _params(
            args,
            {"db": "mesh", "retmode": "json", "retmax": 20, "term": f'"{args.mesh}"[MeSH Terms]'},
        ),
        as_json=True,
    )
    result = data["esearchresult"]
    ids = result.get("idlist", [])
    print(f"MeSH 精确检索命中：{result.get('count', '0')} 条")
    if not ids:
        return
    _pause(args)
    detail = _request(
        "esummary.fcgi",
        _params(args, {"db": "mesh", "retmode": "json", "id": ",".join(ids)}),
        as_json=True,
    )
    for uid in ids:
        item = detail.get("result", {}).get(uid, {})
        print(f"- {item.get('name', '')} (UID {uid})")
        entries = [x.get("entryterm") for x in item.get("entrytermlist", [])[:8] if x.get("entryterm")]
        if entries:
            print("  Entry terms: " + "; ".join(entries))


def cmd_search(args: argparse.Namespace) -> None:
    search = _request(
        "esearch.fcgi",
        _params(
            args,
            {
                "db": "pubmed",
                "retmode": "json",
                "retmax": 0,
                "usehistory": "y",
                "sort": args.sort,
                "term": args.query,
            },
        ),
        as_json=True,
    )["esearchresult"]
    total = int(search.get("count", 0))
    if total > PUBMED_ESEARCH_LIMIT:
        raise ValueError(
            f"PubMed 命中 {total} 条，超过 ESearch 可保证完整取得的 {PUBMED_ESEARCH_LIMIT} 条边界。"
            "请使用 EDirect，或按日期分段为每段不超过 10000 条并核对 PMID 去重后再合并；"
            "当前脚本不会把可能不完整的结果标为全量导出。"
        )
    limit = total if args.retmax is None else min(total, args.retmax)
    if limit < total and not args.allow_truncated:
        raise ValueError(
            f"检索命中 {total} 条，但 --retmax 只允许导出 {limit} 条。"
            "快速证据综合不得静默截断；请缩窄 PICOS/检索式，或显式加入 --allow-truncated 并将结果标为初步。"
        )
    print(f"总命中 {total} 条；计划导出 {limit} 条。", file=sys.stderr)
    print(f"Query Translation: {search.get('querytranslation', '')}", file=sys.stderr)
    records: list[dict[str, object]] = []
    if limit:
        query_key = search.get("querykey")
        webenv = search.get("webenv")
        if not query_key or not webenv:
            raise RuntimeError("NCBI 未返回 History Server 标识，无法继续 EFetch。")

        for start in range(0, limit, args.batch_size):
            batch = min(args.batch_size, limit - start)
            _pause(args)
            raw = _request(
                "efetch.fcgi",
                _params(
                    args,
                    {
                        "db": "pubmed",
                        "query_key": query_key,
                        "WebEnv": webenv,
                        "retstart": start,
                        "retmax": batch,
                        "retmode": "xml",
                    },
                ),
            )
            parsed = parse_pubmed_xml(raw)
            records.extend(parsed)
            print(f"已获取 {len(records)}/{limit} 条。", file=sys.stderr)

    ris_text = to_ris(records)
    ris_bytes = ris_text.encode("utf-8")
    Path(args.out).write_bytes(ris_bytes)
    abstracts = sum(bool(item.get("abstract")) for item in records)
    manifest = {
        "schema_version": "pubmed-search-v1",
        "database": "PubMed",
        "searched_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "query": args.query,
        "query_translation": search.get("querytranslation", ""),
        "total_hits": total,
        "exported_records": len(records),
        "retrieved_all_hits": len(records) == total,
        "explicit_truncation": limit < total,
        "sort": args.sort,
        "abstracts_available": abstracts,
        "warnings": search.get("warninglist") or {},
        "ris_sha256": hashlib.sha256(ris_bytes).hexdigest(),
    }
    Path(args.manifest).write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"完成：{args.out}；记录 {len(records)}，含摘要 {abstracts}。", file=sys.stderr)
    print(f"检索清单：{args.manifest}", file=sys.stderr)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="PubMed 检索、MeSH 查询与含摘要 RIS 导出")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--query", help="完整 PubMed 检索式并导出 RIS")
    mode.add_argument("--count", help="只返回命中数与 Query Translation")
    mode.add_argument("--mesh", help="在 MeSH 数据库核实主题词")
    parser.add_argument("--out", default="pubmed.ris")
    parser.add_argument("--manifest", help="检索审计 JSON；--query 模式必填")
    parser.add_argument(
        "--retmax",
        type=int,
        default=None,
        help="显式限制导出数；默认导出全部命中，截断时还需 --allow-truncated",
    )
    parser.add_argument(
        "--allow-truncated",
        action="store_true",
        help="允许显式截断；此时不能把结果称为完整快速证据综合",
    )
    parser.add_argument("--batch-size", type=int, default=200, choices=range(1, 501), metavar="1-500")
    parser.add_argument("--sort", default="pub date", help="NCBI ESearch 排序，例如 pub date")
    parser.add_argument("--email", help="按 NCBI 建议提供联系人邮箱")
    parser.add_argument("--api-key", help="NCBI API key；不要写入 Skill 或记忆")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    if args.retmax is not None and args.retmax < 1:
        parser.error("--retmax 必须大于 0")
    if args.query:
        if not args.manifest:
            parser.error("--query 模式必须提供 --manifest 以保存可复现检索记录")
    try:
        if args.query:
            cmd_search(args)
        elif args.count:
            cmd_count(args)
        else:
            cmd_mesh(args)
        return 0
    except (OSError, RuntimeError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "error", "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
