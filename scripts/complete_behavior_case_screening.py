"""Complete the three repository behavior-case screening logs after manual review."""

from __future__ import annotations

import csv
import re
from pathlib import Path

from ris_dedup import fields, first, parse_records
from ris_screening_draft import HEADERS, pmid


ROOT = Path(__file__).resolve().parents[1]

DECISIONS = {
    "glucosamine-chondroitin": {
        "42643227": {
            "decision": "exclude",
            "reason": "本记录是指定的历史证据基座本身，不作为截止日期后的独立更新证据重复计入",
        },
        "42558409": {
            "decision": "include",
            "reason": "更新期内的系统综述/网络Meta，包含氨糖软骨素对膝骨关节炎疼痛与功能结局",
            "full_text_status": "obtained",
            "full_text_decision": "include",
            "study_id": "GLUCO-NMA-2026",
            "study_design": "systematic_review_network_meta_analysis",
            "key_outcomes": "VAS pain; WOMAC pain/function; adverse events",
            "notes": "多数辅助比较为低或极低确定性；缺少直接头对头试验",
        },
    },
    "calcium-older-adults": {
        "42161415": {
            "decision": "exclude",
            "reason": "本记录是指定的历史证据基座本身，不作为截止日期后的独立更新证据重复计入",
        },
        "41221311": {
            "decision": "exclude",
            "reason": "虽在更新期发表，但检索截止到2023年5月，证据已被2026年基座综述覆盖",
        },
        "41063100": {
            "decision": "exclude",
            "reason": "人群为接受骨质疏松治疗的绝经后女性，不回答一般老年人是否常规补钙",
        },
        "40087804": {
            "decision": "exclude",
            "reason": "人群为正在接受抗骨吸收药物的绝经后骨质疏松患者，PICOS不匹配",
        },
    },
    "fish-oil": {
        "37264945": {
            "decision": "exclude",
            "reason": "本记录是指定的历史证据基座本身，不作为截止日期后的独立更新证据重复计入",
        },
    },
}

FISH_FULL_TEXT_CANDIDATES = {
    "42115081",
    "42497400",
    "41500861",
    "41676815",
    "41514392",
    "41156531",
    "39163858",
    "38830807",
    "37301827",
    "36982461",
    "36760560",
    "36641259",
    "35871058",
}


def default_exclusion(title: str, abstract: str) -> str:
    text = f"{title} {abstract}".casefold()
    if "protocol" in text or "baseline" in title.casefold():
        return "研究方案或基线报告，尚无可用于功效判断的结局数据"
    if any(term in text for term in (" rat ", " rats ", " mice ", " rabbit", "in vitro", "animal study")):
        return "非人体临床研究"
    if any(term in text for term in ("pediatric", "children", "childhood", "adolescent")):
        return "未成年人群，不符合本次成人PICOS"
    if any(term in text for term in ("cross-sectional", "cohort study", "registry", "observational study", "eligibility")):
        return "观察性或资格估算研究，不能回答本次随机干预功效问题"
    if any(term in title.casefold() for term in ("narrative review", "recent updates", "what is really new", "clinical perspectives", "guidelines")):
        return "叙述性综述或指南解读，不作为更新期直接功效证据"
    return "干预、目标人群、比较或关键结局与预定义PICOS不匹配"


def write_case(slug: str) -> None:
    case_dir = ROOT / "examples" / "cases" / slug
    records = parse_records((case_dir / "pubmed-search.ris").read_text(encoding="utf-8-sig", errors="replace"))
    rows: list[dict[str, str]] = []
    case_decisions = DECISIONS[slug]
    for index, record in enumerate(records, 1):
        data = fields(record)
        record_pmid = pmid(data)
        title = first(data, "TI", "T1", "CT")
        abstract = first(data, "AB")
        row = {header: "" for header in HEADERS}
        row.update(
            {
                "record_id": str(index),
                "pmid": record_pmid,
                "doi": first(data, "DO", "M1"),
                "title": title,
                "year": first(data, "PY", "Y1", "DA")[:4],
            }
        )
        decision = case_decisions.get(record_pmid)
        if slug == "fish-oil" and record_pmid in FISH_FULL_TEXT_CANDIDATES:
            decision = {
                "decision": "include",
                "reason": "题名摘要符合成人omega-3对甘油三酯/血脂的更新证据PICOS，进入全文环节",
                "full_text_status": "abstract_only",
                "full_text_decision": "exclude",
                "full_text_exclusion_reason": "本演示环境仅取得摘要，未纳入正式快速GRADE证据体",
                "study_design": "candidate_update_report",
                "notes": "保留为待全文核查记录；不据此声称完成正式GRADE",
            }
        if decision:
            row["title_abstract_decision"] = decision["decision"]
            row["title_abstract_reason"] = decision["reason"]
            row["full_text_status"] = decision.get("full_text_status", "")
            row["full_text_decision"] = decision.get("full_text_decision", "")
            row["full_text_exclusion_reason"] = decision.get("full_text_exclusion_reason", "")
            row["study_id"] = decision.get("study_id", "")
            row["study_design"] = decision.get("study_design", "")
            row["key_outcomes"] = decision.get("key_outcomes", "")
            row["notes"] = decision.get("notes", "")
        else:
            row["title_abstract_decision"] = "exclude"
            row["title_abstract_reason"] = default_exclusion(title, abstract)
        rows.append(row)

    with (case_dir / "screening.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=HEADERS)
        writer.writeheader()
        writer.writerows(rows)
    included = sum(row["full_text_decision"] == "include" for row in rows)
    abstract_only = sum(row["full_text_status"] == "abstract_only" for row in rows)
    print(f"{slug}: {len(rows)} screened, {included} included, {abstract_only} abstract-only candidates")


def main() -> int:
    for slug in ("fish-oil", "glucosamine-chondroitin", "calcium-older-adults"):
        write_case(slug)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
