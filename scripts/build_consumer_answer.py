#!/usr/bin/env python3
"""Build the expandable consumer evidence-adjudication HTML and optional SVG."""

from __future__ import annotations

import argparse
import csv
import hashlib
import html
import json
import re
import sys
import textwrap
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "templates" / "consumer-answer.template.html"
VERDICTS = {
    "priority": ("值得优先考虑。", "#16704a"),
    "conditional": ("只对特定人群值得。", "#265d97"),
    "trial": ("可以试，但别期待太高。", "#7a5812"),
    "not_worth": ("不太值得买。", "#9e332d"),
    "avoid": ("不建议自行使用。", "#9e332d"),
    "insufficient": ("暂不能可靠判断。", "#7a5812"),
}
CERTAINTY_METHODS = {
    "source_grade": "引用来源已有 GRADE",
    "rapid_grade": "基于快速证据综合的 GRADE 评级",
    "provisional_grade": "基于当前可得证据的暂定 GRADE",
    "grade_informed": "GRADE-informed 快速判断",
}
EVIDENCE_BASE_APPROACHES = {
    "existing_review_plus_pubmed_update": "现有系统综述 + PubMed 更新检索",
    "de_novo_pubmed": "无合格综述基座，从头 PubMed 快速证据普查",
}
REQUIRED = ("title", "verdict", "for_whom", "effect_ceiling", "safety_red_line", "why", "suitability", "research")
GRADE_DOMAINS = (
    "risk_of_bias",
    "inconsistency",
    "indirectness",
    "imprecision",
    "dissemination_bias",
)


def fail(message: str) -> None:
    raise ValueError(message)


def clean_text(value, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        fail(f"{field} must be a non-empty string")
    return value.strip()


def string_list(value, field: str, limit: int | None = None) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list) or not all(isinstance(x, str) and x.strip() for x in value):
        fail(f"{field} must be a list of non-empty strings")
    items = [x.strip() for x in value]
    if limit is not None and len(items) > limit:
        fail(f"{field} may contain at most {limit} items")
    return items


def object_rows(value, field: str, keys: tuple[str, ...], limit: int) -> list[dict[str, str]]:
    if value is None:
        return []
    if not isinstance(value, list) or len(value) > limit:
        fail(f"{field} must be a list containing at most {limit} objects")
    rows = []
    for index, item in enumerate(value):
        if not isinstance(item, dict):
            fail(f"{field}[{index}] must be an object")
        rows.append({key: clean_text(item.get(key, ""), f"{field}[{index}].{key}") for key in keys})
    return rows


def nonnegative_int(value, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        fail(f"{field} must be a non-negative integer")
    return value


def grade_outcomes(value, field: str = "research.outcomes") -> list[dict[str, str]]:
    if not isinstance(value, list) or not value or len(value) > 7:
        fail(f"{field} must contain 1 to 7 outcome objects")
    rows = []
    for index, item in enumerate(value):
        if not isinstance(item, dict):
            fail(f"{field}[{index}] must be an object")
        domains = item.get("grade_domains")
        if not isinstance(domains, dict):
            fail(f"{field}[{index}].grade_domains must be an object")
        normalized_domains = {
            key: clean_text(domains.get(key, ""), f"{field}[{index}].grade_domains.{key}")
            for key in GRADE_DOMAINS
        }
        rows.append({
            "outcome": clean_text(item.get("outcome", ""), f"{field}[{index}].outcome"),
            "effect": clean_text(item.get("effect", ""), f"{field}[{index}].effect"),
            "certainty": clean_text(item.get("certainty", ""), f"{field}[{index}].certainty"),
            "why": clean_text(item.get("why", ""), f"{field}[{index}].why"),
            "grade_domains": normalized_domains,
        })
    return rows


def safe_url(value: str) -> str | None:
    try:
        parsed = urlparse(value)
    except ValueError:
        return None
    return value if parsed.scheme in {"http", "https"} and parsed.netloc else None


def visible_char_count(*parts: str) -> int:
    return len(re.sub(r"\s+", "", "".join(parts)))


def ul(items: list[str]) -> str:
    if not items:
        return ""
    return "<ul>" + "".join(f"<li>{html.escape(item)}</li>" for item in items) + "</ul>"


def paragraph(value: str) -> str:
    return f"<p>{html.escape(value)}</p>" if value else ""


def validate(data: dict) -> dict:
    if not isinstance(data, dict):
        fail("input must be a JSON object")
    missing = [field for field in REQUIRED if field not in data]
    if missing:
        fail("missing required fields: " + ", ".join(missing))

    title = clean_text(data["title"], "title")
    verdict_key = clean_text(data["verdict"], "verdict")
    if verdict_key not in VERDICTS:
        fail("verdict must be one of: " + ", ".join(VERDICTS))
    verdict, verdict_color = VERDICTS[verdict_key]
    for_whom = clean_text(data["for_whom"], "for_whom")
    effect_ceiling = clean_text(data["effect_ceiling"], "effect_ceiling")
    safety_red_line = clean_text(data["safety_red_line"], "safety_red_line")
    first_screen_chars = visible_char_count(verdict, for_whom, effect_ceiling, safety_red_line)
    if first_screen_chars > 150:
        fail(f"first-screen copy is {first_screen_chars} characters; maximum is 150")

    why = data["why"]
    suitability = data["suitability"]
    research = data["research"]
    if not all(isinstance(section, dict) for section in (why, suitability, research)):
        fail("why, suitability, and research must be JSON objects")

    why_summary = clean_text(why.get("summary", ""), "why.summary")
    key_points = string_list(why.get("key_points"), "why.key_points")
    better_options = string_list(why.get("better_options"), "why.better_options")
    may_fit = string_list(suitability.get("may_fit"), "suitability.may_fit")
    avoid_or_check = string_list(suitability.get("avoid_or_check"), "suitability.avoid_or_check")
    intake_summary = string_list(
        suitability.get("intake_summary"), "suitability.intake_summary", limit=5
    )
    remaining_value = suitability.get("remaining_uncertainties")
    remaining_field = "suitability.remaining_uncertainties"
    if remaining_value is None:
        remaining_value = suitability.get("questions")  # Backward compatibility.
        remaining_field = "suitability.questions"
    remaining_uncertainties = string_list(remaining_value, remaining_field, limit=5)
    assumption = str(suitability.get("assumption", "")).strip()
    user_match = str(suitability.get("user_match", "")).strip()

    picos_value = research.get("picos")
    if picos_value is None:
        picos_value = research.get("pico", "")  # Backward compatibility for older inputs.
    picos = clean_text(picos_value, "research.picos")
    effect = clean_text(research.get("effect", ""), "research.effect")
    certainty = clean_text(research.get("certainty", ""), "research.certainty")
    certainty_method = clean_text(research.get("certainty_method", ""), "research.certainty_method")
    certainty_scope = clean_text(research.get("certainty_scope", ""), "research.certainty_scope")
    if certainty_method not in CERTAINTY_METHODS:
        fail("research.certainty_method must be one of: " + ", ".join(CERTAINTY_METHODS))
    if certainty_method == "grade_informed" and not re.search(
        r"无法正式评级|未正式评级|非正式判断", certainty
    ):
        fail(
            "GRADE-informed output must say it is not formally rated instead of presenting a four-level GRADE certainty"
        )
    updated = clean_text(research.get("updated", ""), "research.updated")
    certainty_reasons = string_list(research.get("certainty_reasons"), "research.certainty_reasons")
    adjudication = object_rows(
        research.get("adjudication"),
        "research.adjudication",
        ("source", "finding", "why_differs", "weight"),
        limit=6,
    )
    outcomes = grade_outcomes(research.get("outcomes"))

    evidence_base = research.get("evidence_base")
    if not isinstance(evidence_base, dict):
        fail("research.evidence_base must be an object")
    evidence_base_approach = clean_text(
        evidence_base.get("approach", ""), "research.evidence_base.approach"
    )
    if evidence_base_approach not in EVIDENCE_BASE_APPROACHES:
        fail(
            "research.evidence_base.approach must be existing_review_plus_pubmed_update or de_novo_pubmed"
        )
    evidence_base_summary = clean_text(
        evidence_base.get("summary", ""), "research.evidence_base.summary"
    )
    evidence_base_appraisal = clean_text(
        evidence_base.get("appraisal", ""), "research.evidence_base.appraisal"
    )
    evidence_base_search_end = clean_text(
        evidence_base.get("search_end", ""), "research.evidence_base.search_end"
    )

    search = research.get("search")
    if not isinstance(search, dict):
        fail("research.search must be an object")
    search_database = clean_text(search.get("database", ""), "research.search.database")
    if search_database.lower() != "pubmed":
        fail("research.search.database must be PubMed for the minimum consumer efficacy workflow")
    search_query = clean_text(search.get("query", ""), "research.search.query")
    search_translation = clean_text(
        search.get("query_translation", ""), "research.search.query_translation"
    )
    searched_at = clean_text(search.get("searched_at", ""), "research.search.searched_at")
    search_limits = clean_text(search.get("limits", ""), "research.search.limits")
    search_counts = {
        key: nonnegative_int(search.get(key), f"research.search.{key}")
        for key in (
            "records_found",
            "records_exported",
            "records_screened",
            "full_text_assessed",
            "reports_included",
            "studies_included",
        )
    }
    if not (
        search_counts["records_found"] >= search_counts["records_exported"]
        >= search_counts["records_screened"] >= search_counts["full_text_assessed"]
        >= search_counts["reports_included"] >= search_counts["studies_included"]
    ):
        fail("research.search counts must form a non-increasing screening flow")
    complete_retrieval = search.get("complete_retrieval")
    screening_complete = search.get("screening_complete")
    if not isinstance(complete_retrieval, bool) or not isinstance(screening_complete, bool):
        fail("research.search.complete_retrieval and screening_complete must be booleans")
    if complete_retrieval and search_counts["records_found"] != search_counts["records_exported"]:
        fail("complete_retrieval requires records_found to equal records_exported")
    if screening_complete and search_counts["records_exported"] != search_counts["records_screened"]:
        fail("screening_complete requires records_exported to equal records_screened")
    if (not complete_retrieval or not screening_complete) and verdict_key not in {"insufficient", "avoid"}:
        fail("incomplete PubMed retrieval or screening requires verdict insufficient or avoid")
    if certainty_method == "rapid_grade" and (not complete_retrieval or not screening_complete):
        fail("rapid_grade requires complete PubMed retrieval and screening")

    evidence_access = research.get("evidence_access")
    full_text_unavailable = 0
    access_impact = ""
    upload_prompt = ""
    if evidence_access is not None:
        if not isinstance(evidence_access, dict):
            fail("research.evidence_access must be an object")
        full_text_unavailable = nonnegative_int(
            evidence_access.get("full_text_unavailable"),
            "research.evidence_access.full_text_unavailable",
        )
        access_impact = clean_text(
            evidence_access.get("impact", ""), "research.evidence_access.impact"
        )
        upload_prompt = clean_text(
            evidence_access.get("upload_prompt", ""),
            "research.evidence_access.upload_prompt",
        )
    if certainty_method == "provisional_grade":
        if evidence_access is None or full_text_unavailable < 1:
            fail("provisional_grade requires at least one unavailable full text")
        if not complete_retrieval or not screening_complete:
            fail("provisional_grade requires complete PubMed retrieval and title/abstract screening")
        if "暂定" not in certainty or any("暂定" not in row["certainty"] for row in outcomes):
            fail("provisional_grade certainty labels must explicitly say they are provisional")
    elif full_text_unavailable and certainty_method != "grade_informed":
        fail("unavailable full texts require provisional_grade or grade_informed")

    eligibility = research.get("eligibility")
    if not isinstance(eligibility, dict):
        fail("research.eligibility must be an object")
    inclusion = string_list(eligibility.get("inclusion"), "research.eligibility.inclusion")
    exclusion = string_list(eligibility.get("exclusion"), "research.eligibility.exclusion")
    if not inclusion or not exclusion:
        fail("research.eligibility must include non-empty inclusion and exclusion criteria")
    exclusion_log = object_rows(
        eligibility.get("exclusion_log"),
        "research.eligibility.exclusion_log",
        ("reason", "count"),
        limit=12,
    )
    funding = str(research.get("funding", research.get("conflicts", ""))).strip()
    what_would_change = string_list(research.get("what_would_change"), "research.what_would_change", limit=4)
    sources = research.get("sources", [])
    if not isinstance(sources, list) or not 2 <= len(sources) <= 5:
        fail("research.sources must contain 2 to 5 sources")
    normalized_sources = []
    for index, source in enumerate(sources):
        if not isinstance(source, dict):
            fail(f"research.sources[{index}] must be an object")
        label = clean_text(source.get("label", ""), f"research.sources[{index}].label")
        url = str(source.get("url", "")).strip()
        normalized_sources.append({
            "label": label,
            "url": safe_url(url),
            "role": str(source.get("role", "")).strip(),
            "year": str(source.get("year", "")).strip(),
        })

    return {
        "title": title,
        "verdict": verdict,
        "verdict_color": verdict_color,
        "for_whom": for_whom,
        "effect_ceiling": effect_ceiling,
        "safety_red_line": safety_red_line,
        "first_screen_chars": first_screen_chars,
        "why_summary": why_summary,
        "key_points": key_points,
        "better_options": better_options,
        "may_fit": may_fit,
        "avoid_or_check": avoid_or_check,
        "intake_summary": intake_summary,
        "remaining_uncertainties": remaining_uncertainties,
        "assumption": assumption,
        "user_match": user_match,
        "picos": picos,
        "effect": effect,
        "certainty": certainty,
        "certainty_method": certainty_method,
        "certainty_method_label": CERTAINTY_METHODS.get(certainty_method, ""),
        "certainty_scope": certainty_scope,
        "updated": updated,
        "certainty_reasons": certainty_reasons,
        "adjudication": adjudication,
        "outcomes": outcomes,
        "evidence_base_approach": evidence_base_approach,
        "evidence_base_approach_label": EVIDENCE_BASE_APPROACHES[evidence_base_approach],
        "evidence_base_summary": evidence_base_summary,
        "evidence_base_appraisal": evidence_base_appraisal,
        "evidence_base_search_end": evidence_base_search_end,
        "search_database": search_database,
        "search_query": search_query,
        "search_translation": search_translation,
        "searched_at": searched_at,
        "search_limits": search_limits,
        "search_counts": search_counts,
        "complete_retrieval": complete_retrieval,
        "screening_complete": screening_complete,
        "full_text_unavailable": full_text_unavailable,
        "access_impact": access_impact,
        "upload_prompt": upload_prompt,
        "unavailable_records": [],
        "inclusion": inclusion,
        "exclusion": exclusion,
        "exclusion_log": exclusion_log,
        "funding": funding,
        "what_would_change": what_would_change,
        "sources": normalized_sources,
        "meta": str(research.get("meta", "")).strip(),
        "grade": str(research.get("grade", "")).strip(),
        "rob": str(research.get("rob", "")).strip(),
    }


def build_why(d: dict) -> str:
    blocks = ["<h2>为什么</h2>", paragraph(d["why_summary"])]
    if d["key_points"]:
        blocks += ["<h3>决定结论的事实</h3>", ul(d["key_points"])]
    if d["better_options"]:
        blocks += ["<h3>更优先的路径</h3>", ul(d["better_options"])]
    return "".join(blocks)


def build_suitability(d: dict) -> str:
    blocks = ["<h2>适不适合我</h2>"]
    if d["intake_summary"]:
        blocks += ["<h3>本次已采用的信息</h3>", ul(d["intake_summary"])]
    if d["assumption"]:
        blocks += ["<h3>当前暂定情境</h3>", paragraph(d["assumption"])]
    if d["user_match"]:
        blocks += ["<h3>与研究人群的匹配度</h3>", paragraph(d["user_match"])]
    if d["may_fit"]:
        blocks += ["<h3>可能匹配</h3>", ul(d["may_fit"])]
    if d["avoid_or_check"]:
        blocks += ["<h3>避免或先确认</h3>", ul(d["avoid_or_check"])]
    if d["remaining_uncertainties"]:
        blocks += ["<h3>仍可能改变建议的信息</h3>", ul(d["remaining_uncertainties"])]
    return "".join(blocks)


def table(headers: tuple[str, ...], rows: list[tuple[str, ...]]) -> str:
    head = "".join(f'<th scope="col">{html.escape(value)}</th>' for value in headers)
    body = "".join(
        "<tr>" + "".join(f"<td>{html.escape(value)}</td>" for value in row) + "</tr>"
        for row in rows
    )
    return f'<div class="table-wrap"><table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>'


def nested(label: str, value: str) -> str:
    if not value:
        return ""
    return (
        '<details class="nested"><summary>' + html.escape(label) + "</summary>"
        '<div class="inner">' + paragraph(value) + "</div></details>"
    )


def build_research(d: dict) -> str:
    sources = []
    for source in d["sources"]:
        label = html.escape(source["label"])
        if source["url"]:
            label = f'<a href="{html.escape(source["url"], quote=True)}" target="_blank" rel="noopener noreferrer">{label}</a>'
        suffix = " · ".join(x for x in (html.escape(source["role"]), html.escape(source["year"])) if x)
        sources.append(f"<li>{label}{' — ' + suffix if suffix else ''}</li>")
    blocks = [
        "<h2>证据怎么裁决</h2>",
        "<p>这里评价的是整组证据如何共同支持结论，不用单篇论文或期刊名代替裁决。</p>",
        '<div class="research-grid">',
        f"<div><strong>PICOS 与随访</strong>{html.escape(d['picos'])}</div>",
        f"<div><strong>检索或更新</strong>{html.escape(d['updated'])}</div>",
        "</div>",
    ]
    if d["adjudication"]:
        rows = [
            (row["source"], row["finding"], row["why_differs"], row["weight"])
            for row in d["adjudication"]
        ]
        blocks += [
            "<h3>来源为何看似矛盾</h3>",
            table(("来源或观点", "得出的结论", "为何不同", "本次权重"), rows),
        ]
    if d["outcomes"]:
        rows = [
            (
                row["outcome"],
                row["effect"],
                row["certainty"],
                "；".join((
                    f"偏倚风险：{row['grade_domains']['risk_of_bias']}",
                    f"不一致性：{row['grade_domains']['inconsistency']}",
                    f"间接性：{row['grade_domains']['indirectness']}",
                    f"不精确性：{row['grade_domains']['imprecision']}",
                    f"传播偏倚：{row['grade_domains']['dissemination_bias']}",
                    f"结论：{row['why']}",
                )),
            )
            for row in d["outcomes"]
        ]
        blocks += [
            "<h3>按关键结局综合判断</h3>",
            table(("关键结局", "实际效应", "证据体确定性", "GRADE 五域与理由"), rows),
        ]
    flow = d["search_counts"]
    if d["full_text_unavailable"]:
        missing_rows = [
            (record.get("pmid", ""), record.get("title", ""))
            for record in d["unavailable_records"]
        ]
        blocks += [
            "<h3>全文获取情况</h3>",
            '<div class="access-warning">',
            f"<strong>{d['full_text_unavailable']} 篇候选文献尚未取得全文</strong>",
            paragraph(d["access_impact"]),
            paragraph(d["upload_prompt"]),
            "</div>",
        ]
        if missing_rows:
            blocks += [
                nested(
                    "查看尚缺全文的记录",
                    "；".join(
                        f"PMID {pmid}：{title}" if pmid else title
                        for pmid, title in missing_rows
                    ),
                )
            ]
    blocks += [
        "<h3>历史证据基座</h3>",
        '<div class="research-grid">',
        f"<div><strong>采用方式</strong>{html.escape(d['evidence_base_approach_label'])}</div>",
        f"<div><strong>原综述检索截止</strong>{html.escape(d['evidence_base_search_end'])}</div>",
        "</div>",
        paragraph(d["evidence_base_summary"]),
        paragraph(d["evidence_base_appraisal"]),
        "<h3>可复现的 PubMed 检索</h3>",
        '<div class="research-grid">',
        f"<div><strong>数据库与日期</strong>{html.escape(d['search_database'])} · {html.escape(d['searched_at'])}</div>",
        f"<div><strong>完整导出 / 完整筛查</strong>{'是' if d['complete_retrieval'] else '否'} / {'是' if d['screening_complete'] else '否'}</div>",
        "</div>",
        nested("完整检索式", d["search_query"]),
        nested("PubMed Query Translation", d["search_translation"]),
        "<h3>筛选流程</h3>",
        table(
            ("命中", "导出", "题录筛查", "全文评估", "纳入报告", "纳入研究"),
            [tuple(str(flow[key]) for key in (
                "records_found", "records_exported", "records_screened",
                "full_text_assessed", "reports_included", "studies_included"
            ))],
        ),
        paragraph(d["search_limits"]),
        "<h3>PICOS 纳入与排除</h3>",
        "<h4>纳入标准</h4>", ul(d["inclusion"]),
        "<h4>排除标准</h4>", ul(d["exclusion"]),
    ]
    if d["exclusion_log"]:
        blocks += [
            "<h4>实际排除记录</h4>",
            table(
                ("排除原因", "数量"),
                [(row["reason"], row["count"]) for row in d["exclusion_log"]],
            ),
        ]
    blocks += [
        "<h3>证据体总览</h3>",
        '<div class="research-grid">',
        f"<div><strong>实际效应</strong>{html.escape(d['effect'])}</div>",
        f"<div><strong>证据体确定性</strong>{html.escape(d['certainty'])}</div>",
        "</div>",
    ]
    if d["certainty_method_label"]:
        blocks += [
            "<h3>确定性评价方法</h3>",
            '<div class="research-grid">',
            f"<div><strong>评价路径</strong>{html.escape(d['certainty_method_label'])}</div>",
            f"<div><strong>范围与流程简化</strong>{html.escape(d['certainty_scope'])}</div>",
            "</div>",
        ]
    if d["certainty_reasons"]:
        blocks += ["<h3>主要不确定性</h3>", ul(d["certainty_reasons"])]
    if d["what_would_change"]:
        blocks += ["<h3>什么会改变结论</h3>", ul(d["what_would_change"])]
    if d["funding"]:
        blocks += ["<h3>资金与利益冲突</h3>", paragraph(d["funding"])]
    blocks += ["<h3>决定性来源</h3>", '<ol class="sources">' + "".join(sources) + "</ol>"]
    blocks += [nested("Meta 分析", d["meta"]), nested("GRADE", d["grade"]), nested("偏倚风险（RoB）", d["rob"])]
    return "".join(blocks)


def build_html(d: dict) -> str:
    template = TEMPLATE.read_text(encoding="utf-8")
    replacements = {
        "__TITLE__": html.escape(d["title"]),
        "__VERDICT__": html.escape(d["verdict"]),
        "__VERDICT_COLOR__": d["verdict_color"],
        "__FOR_WHOM__": html.escape(d["for_whom"]),
        "__EFFECT_CEILING__": html.escape(d["effect_ceiling"]),
        "__SAFETY_RED_LINE__": html.escape(d["safety_red_line"]),
        "__WHY_HTML__": build_why(d),
        "__SUITABILITY_HTML__": build_suitability(d),
        "__RESEARCH_HTML__": build_research(d),
        "__ACCESS_DIALOG__": build_access_dialog(d),
        "__UPDATED__": html.escape(d["updated"]),
    }
    for marker, value in replacements.items():
        template = template.replace(marker, value)
    if re.search(r"__[A-Z0-9_]+__", template):
        fail("unresolved template marker remains")
    return template


def build_access_dialog(d: dict) -> str:
    if not d["full_text_unavailable"]:
        return ""
    record_list = ul([
        f"PMID {record.get('pmid', '')}：{record.get('title', '')}".strip("：")
        for record in d["unavailable_records"]
    ])
    return (
        '<dialog open class="access-dialog" data-testid="full-text-dialog" aria-labelledby="access-dialog-title">'
        '<form method="dialog"><button class="dialog-close" aria-label="关闭提示">稍后处理</button></form>'
        '<p class="dialog-kicker">暂定评级提醒</p>'
        '<h2 id="access-dialog-title">'
        f"还有 {d['full_text_unavailable']} 篇候选文献未取得全文"
        "</h2>"
        + paragraph(d["access_impact"])
        + paragraph(d["upload_prompt"])
        + ('<details><summary>查看缺失记录</summary>' + record_list + '</details>' if record_list else '')
        + "</dialog>"
    )


def verify_evidence_bundle(d: dict, manifest_path: Path, ris_path: Path, screening_path: Path) -> dict:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("schema_version") != "pubmed-search-v1":
        fail("PubMed manifest schema_version must be pubmed-search-v1")
    checks = {
        "database": d["search_database"],
        "query": d["search_query"],
        "query_translation": d["search_translation"],
        "total_hits": d["search_counts"]["records_found"],
        "exported_records": d["search_counts"]["records_exported"],
        "retrieved_all_hits": d["complete_retrieval"],
    }
    for key, expected in checks.items():
        if manifest.get(key) != expected:
            fail(f"PubMed manifest {key} does not match research.search")
    if str(manifest.get("searched_at_utc", ""))[:10] != d["searched_at"]:
        fail("PubMed manifest searched_at_utc does not match research.search.searched_at")

    ris_bytes = ris_path.read_bytes()
    if hashlib.sha256(ris_bytes).hexdigest() != manifest.get("ris_sha256"):
        fail("PubMed RIS SHA256 does not match the search manifest")

    with screening_path.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    required_columns = {
        "record_id", "pmid", "title_abstract_decision", "full_text_status", "full_text_decision",
        "full_text_exclusion_reason", "study_id",
    }
    if not rows or not required_columns.issubset(set(rows[0])):
        fail("screening log is empty or missing required columns")
    if any(row["title_abstract_decision"] not in {"include", "exclude"} for row in rows):
        fail("every screening row must have title_abstract_decision include or exclude")
    if len(rows) != d["search_counts"]["records_screened"]:
        fail("screening log row count does not match records_screened")
    ris_pmids = set(re.findall(rb"^ID  - PMID:(\d+)[ \t\r]*$", ris_bytes, flags=re.MULTILINE))
    screening_pmids = {row["pmid"].strip().encode("ascii") for row in rows if row["pmid"].strip()}
    if len(ris_pmids) != d["search_counts"]["records_exported"] or ris_pmids != screening_pmids:
        fail("screening log PMIDs do not match the complete PubMed RIS export")
    # `abstract_only` records reached the next screening stage but no full text was
    # obtained; do not inflate the reported full-text assessment count.
    full_text_rows = [
        row for row in rows
        if row["full_text_status"].strip() and row["full_text_status"].strip() != "abstract_only"
    ]
    if len(full_text_rows) != d["search_counts"]["full_text_assessed"]:
        fail("screening log full-text count does not match full_text_assessed")
    abstract_only_rows = [
        row for row in rows if row["full_text_status"].strip() == "abstract_only"
    ]
    if len(abstract_only_rows) != d["full_text_unavailable"]:
        fail("screening log abstract-only count does not match full_text_unavailable")
    included_reports = [row for row in rows if row["full_text_decision"] == "include"]
    if len(included_reports) != d["search_counts"]["reports_included"]:
        fail("screening log included-report count does not match reports_included")
    included_studies = {row["study_id"].strip() for row in included_reports if row["study_id"].strip()}
    if len(included_studies) != d["search_counts"]["studies_included"]:
        fail("screening log unique study count does not match studies_included")
    return {
        "unavailable_records": [
            {"pmid": row["pmid"].strip(), "title": row.get("title", "").strip()}
            for row in abstract_only_rows
        ]
    }


def wrap_svg(text: str, width: int = 25) -> list[str]:
    return textwrap.wrap(text, width=width, break_long_words=True, break_on_hyphens=False) or [""]


def svg_text(lines: list[str], x: int, y: int, size: int, color: str, weight: int = 400, gap: int | None = None) -> tuple[str, int]:
    gap = gap or int(size * 1.5)
    parts = []
    for line in lines:
        parts.append(f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{weight}" fill="{color}">{html.escape(line)}</text>')
        y += gap
    return "".join(parts), y


def build_svg(d: dict) -> str:
    parts = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="1080" height="1350" viewBox="0 0 1080 1350" role="img">',
        '<rect width="1080" height="1350" fill="#f5f7fb"/>',
        '<rect x="70" y="65" width="940" height="1220" rx="34" fill="#ffffff" stroke="#dfe4ec" stroke-width="2"/>',
    ]
    text, _ = svg_text(["营养证据卡", d["title"]], 120, 135, 26, "#667085", 500, 48)
    parts.append(text)
    text, _ = svg_text(wrap_svg(d["verdict"], 16), 120, 265, 64, d["verdict_color"], 750, 80)
    parts.append(text)
    cards = [
        ("对谁可能有用", d["for_whom"], 390, "#edf5ff", "#265d97"),
        ("效果上限", d["effect_ceiling"], 650, "#f7f8fa", "#172033"),
        ("安全红线", d["safety_red_line"], 910, "#fff2f0", "#9e332d"),
    ]
    for label, value, y, bg, color in cards:
        parts.append(f'<rect x="110" y="{y}" width="860" height="210" rx="24" fill="{bg}" stroke="#dfe4ec"/>')
        label_svg, _ = svg_text([label], 150, y + 58, 24, "#667085", 650)
        value_svg, _ = svg_text(wrap_svg(value, 22), 150, y + 112, 30, color, 600, 48)
        parts += [label_svg, value_svg]
    footer = f"证据更新：{d['updated']}　完整研究与来源请查看可展开 HTML"
    footer_svg, _ = svg_text(wrap_svg(footer, 38), 120, 1225, 21, "#667085", 400, 32)
    parts += [footer_svg, "</svg>"]
    return "".join(parts)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input_json", help="UTF-8 consumer answer JSON")
    parser.add_argument("--html", required=True, help="Output self-contained HTML path")
    parser.add_argument("--pubmed-manifest", required=True, help="PubMed search manifest JSON")
    parser.add_argument("--pubmed-ris", required=True, help="Unmodified RIS exported by pubmed_search.py")
    parser.add_argument("--screening-log", required=True, help="Completed rapid screening CSV")
    parser.add_argument("--svg", help="Optional one-image SVG path; generate only after user opt-in")
    args = parser.parse_args()
    try:
        raw = json.loads(Path(args.input_json).read_text(encoding="utf-8"))
        data = validate(raw)
        bundle = verify_evidence_bundle(
            data,
            Path(args.pubmed_manifest),
            Path(args.pubmed_ris),
            Path(args.screening_log),
        )
        data.update(bundle)
        html_path = Path(args.html)
        html_path.parent.mkdir(parents=True, exist_ok=True)
        html_path.write_text(build_html(data), encoding="utf-8")
        result = {
            "status": "ok",
            "html": str(html_path.resolve()),
            "first_screen_chars": data["first_screen_chars"],
            "evidence_bundle_verified": True,
        }
        if args.svg:
            svg_path = Path(args.svg)
            svg_path.parent.mkdir(parents=True, exist_ok=True)
            svg_path.write_text(build_svg(data), encoding="utf-8")
            result["svg"] = str(svg_path.resolve())
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(json.dumps({"status": "error", "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
