#!/usr/bin/env python3
"""Collect a small pre-evidence questionnaire through a one-shot localhost form."""

from __future__ import annotations

import argparse
import html
import json
import re
import secrets
import sys
import time
import urllib.parse
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path


MAX_BODY = 64 * 1024
ID_PATTERN = re.compile(r"^[a-z][a-z0-9_-]{0,39}$")


def fail(message: str) -> None:
    raise ValueError(message)


def clean_text(value: object, field: str, *, required: bool = True) -> str:
    text = str(value or "").strip()
    if required and not text:
        fail(f"{field} must be a non-empty string")
    if len(text) > 500:
        fail(f"{field} is too long")
    return text


def validate_questionnaire(raw: object) -> dict:
    if not isinstance(raw, dict):
        fail("questionnaire must be a JSON object")
    title = clean_text(raw.get("title"), "title")
    subtitle = clean_text(raw.get("subtitle"), "subtitle", required=False)
    questions = raw.get("questions")
    if not isinstance(questions, list) or not 1 <= len(questions) <= 5:
        fail("questions must contain 1 to 5 items")

    seen_ids: set[str] = set()
    normalized = []
    for index, question in enumerate(questions):
        if not isinstance(question, dict):
            fail(f"questions[{index}] must be an object")
        question_id = clean_text(question.get("id"), f"questions[{index}].id")
        if not ID_PATTERN.fullmatch(question_id) or question_id in seen_ids:
            fail(f"questions[{index}].id must be unique lowercase ASCII")
        seen_ids.add(question_id)
        question_type = str(question.get("type", "single")).strip()
        if question_type not in {"single", "multi"}:
            fail(f"questions[{index}].type must be single or multi")
        required = question.get("required", True)
        if not isinstance(required, bool):
            fail(f"questions[{index}].required must be a boolean")
        prompt = clean_text(question.get("prompt"), f"questions[{index}].prompt")
        why = clean_text(question.get("why"), f"questions[{index}].why", required=False)
        options = question.get("options")
        if not isinstance(options, list) or not 2 <= len(options) <= 7:
            fail(f"questions[{index}].options must contain 2 to 7 items")
        seen_values: set[str] = set()
        normalized_options = []
        for option_index, option in enumerate(options):
            if not isinstance(option, dict):
                fail(f"questions[{index}].options[{option_index}] must be an object")
            value = clean_text(
                option.get("value"), f"questions[{index}].options[{option_index}].value"
            )
            if not ID_PATTERN.fullmatch(value) or value in seen_values:
                fail(f"questions[{index}].options values must be unique lowercase ASCII")
            seen_values.add(value)
            exclusive = option.get("exclusive", False)
            if not isinstance(exclusive, bool):
                fail(f"questions[{index}].options[{option_index}].exclusive must be a boolean")
            normalized_options.append({
                "value": value,
                "label": clean_text(
                    option.get("label"), f"questions[{index}].options[{option_index}].label"
                ),
                "exclusive": exclusive,
            })
        if question_type == "single" and any(option["exclusive"] for option in normalized_options):
            fail(f"questions[{index}] single-choice options do not need exclusive=true")
        normalized.append({
            "id": question_id,
            "type": question_type,
            "required": required,
            "prompt": prompt,
            "why": why,
            "options": normalized_options,
        })
    return {"title": title, "subtitle": subtitle, "questions": normalized}


def build_page(questionnaire: dict, token: str, selected: dict[str, list[str]] | None = None) -> str:
    selected = selected or {}
    question_blocks = []
    for index, question in enumerate(questionnaire["questions"], start=1):
        input_type = "checkbox" if question["type"] == "multi" else "radio"
        selected_values = set(selected.get(question["id"], []))
        choices = "".join(
            '<label class="choice">'
            f'<input type="{input_type}" name="{html.escape(question["id"])}" '
            f'value="{html.escape(option["value"])}" '
            f'data-exclusive="{"true" if option["exclusive"] else "false"}" '
            f'{"checked" if option["value"] in selected_values else ""} '
            f'{"required" if question["type"] == "single" and question["required"] else ""}>'
            f'<span>{html.escape(option["label"])}</span></label>'
            for option in question["options"]
        )
        why = (
            f'<p class="why">为什么问：{html.escape(question["why"])}</p>'
            if question["why"] else ""
        )
        badge = "可多选" if question["type"] == "multi" else "单选"
        if not question["required"]:
            badge += " · 可跳过"
        question_blocks.append(
            f'<fieldset><legend><span>{index}</span>{html.escape(question["prompt"])}'
            f'<small>{badge}</small></legend>{why}<div class="choices">{choices}</div></fieldset>'
        )
    subtitle = (
        f'<p class="subtitle">{html.escape(questionnaire["subtitle"])}</p>'
        if questionnaire["subtitle"] else ""
    )
    return f"""<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(questionnaire['title'])}</title>
<style>
:root{{--ink:#17322c;--muted:#66736f;--line:#dbe4e1;--accent:#0b6b5d;--soft:#e8f4f1;--bg:#f1f5f3}}
*{{box-sizing:border-box}} body{{margin:0;background:var(--bg);color:var(--ink);font-family:"Microsoft YaHei","PingFang SC",system-ui,sans-serif}}
.backdrop{{min-height:100vh;display:grid;place-items:center;padding:22px}} .modal{{width:min(780px,100%);max-height:calc(100vh - 44px);overflow:auto;background:#fff;border:1px solid var(--line);border-radius:24px;box-shadow:0 24px 80px rgba(23,50,44,.14);padding:30px}}
.eyebrow{{font-size:12px;font-weight:750;letter-spacing:.12em;color:var(--accent)}} h1{{font-size:28px;line-height:1.3;margin:8px 0 7px}} .subtitle{{color:var(--muted);margin:0 0 22px;line-height:1.65}}
fieldset{{border:0;border-top:1px solid var(--line);padding:22px 0 5px;margin:0}} legend{{display:flex;align-items:center;flex-wrap:wrap;font-size:17px;font-weight:700;line-height:1.5;padding:0 8px 0 0}}
legend>span{{display:inline-grid;place-items:center;width:29px;height:29px;border-radius:10px;background:var(--soft);color:var(--accent);margin-right:10px}} legend small{{margin-left:auto;color:var(--muted);font-size:12px;font-weight:600}}
.why{{margin:8px 0 12px;color:var(--muted);font-size:14px}} .choices{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px}} .choice{{position:relative;cursor:pointer}}
.choice input{{position:absolute;opacity:0;pointer-events:none}} .choice span{{display:block;border:1px solid var(--line);border-radius:14px;padding:13px 15px;line-height:1.45;background:#fff;transition:.14s ease}}
.choice input:checked+span{{border-color:var(--accent);background:var(--soft);box-shadow:0 0 0 2px rgba(11,107,93,.10)}} .choice input:focus-visible+span{{outline:3px solid rgba(11,107,93,.22)}}
.actions{{position:sticky;bottom:-30px;display:flex;gap:10px;justify-content:flex-end;background:linear-gradient(transparent,#fff 20%);padding:32px 0 2px}} button{{border-radius:13px;padding:12px 17px;font:inherit;font-weight:700;cursor:pointer}} .skip{{border:1px solid var(--line);background:#fff;color:var(--muted)}} .submit{{border:1px solid var(--accent);background:var(--accent);color:#fff}}
.note{{font-size:13px;color:var(--muted);margin:18px 0 0}} @media(max-width:600px){{.modal{{padding:21px}}.choices{{grid-template-columns:1fr}}.actions{{bottom:-21px;flex-direction:column-reverse}}button{{width:100%}}}}
</style></head><body><div class="backdrop"><main class="modal" role="dialog" aria-modal="true" aria-labelledby="title">
<div class="eyebrow">个性化前的最少信息</div><h1 id="title">{html.escape(questionnaire['title'])}</h1>{subtitle}
<form method="post" action="/{token}/review">{''.join(question_blocks)}
<div class="actions"><button class="skip" name="action" value="skip" formaction="/{token}/submit" formnovalidate>跳过，先看一般结论</button><button class="submit" name="action" value="review">检查我的选择</button></div></form>
<p class="note">选择只发送到本机 127.0.0.1，不会上传到外部网站。提交前会显示摘要并允许修改。</p>
<script>
document.querySelectorAll('input[type="checkbox"]').forEach(function(input){{input.addEventListener('change',function(){{
  var group=document.querySelectorAll('input[name="'+this.name+'"]');
  if(this.checked&&this.dataset.exclusive==='true') group.forEach(function(x){{if(x!==input)x.checked=false}});
  if(this.checked&&this.dataset.exclusive!=='true') group.forEach(function(x){{if(x.dataset.exclusive==='true')x.checked=false}});
}})}});
</script></main></div></body></html>"""


def extract_answers(questionnaire: dict, fields: dict[str, list[str]]) -> tuple[dict, dict, dict[str, list[str]]]:
    answers: dict[str, str | list[str]] = {}
    labels: dict[str, str | list[str]] = {}
    selected: dict[str, list[str]] = {}
    for question in questionnaire["questions"]:
        option_map = {option["value"]: option for option in question["options"]}
        values = list(dict.fromkeys(fields.get(question["id"], [])))
        if any(value not in option_map for value in values):
            fail("提交包含无效选项，请返回问卷重试。")
        if question["required"] and not values:
            fail(f"请完成：{question['prompt']}")
        if question["type"] == "single" and len(values) > 1:
            fail(f"{question['prompt']} 只能选择一项。")
        if question["type"] == "multi":
            exclusive = [value for value in values if option_map[value]["exclusive"]]
            if exclusive and len(values) > 1:
                fail(f"{question['prompt']} 中的“均没有/不清楚”不能与其他项同时选择。")
            if values:
                answers[question["id"]] = values
                labels[question["id"]] = [option_map[value]["label"] for value in values]
        elif values:
            answers[question["id"]] = values[0]
            labels[question["id"]] = option_map[values[0]]["label"]
        selected[question["id"]] = values
    return answers, labels, selected


def review_page(questionnaire: dict, token: str, labels: dict, selected: dict[str, list[str]]) -> bytes:
    rows = []
    hidden = []
    for question in questionnaire["questions"]:
        value = labels.get(question["id"], "未选择（可跳过）")
        if isinstance(value, list):
            value = "、".join(value)
        rows.append(f"<dt>{html.escape(question['prompt'])}</dt><dd>{html.escape(value)}</dd>")
        for selected_value in selected.get(question["id"], []):
            hidden.append(
                f'<input type="hidden" name="{html.escape(question["id"])}" value="{html.escape(selected_value)}">'
            )
    return f"""<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>确认选择</title><style>
body{{margin:0;min-height:100vh;display:grid;place-items:center;background:#f1f5f3;color:#17322c;font:16px/1.65 system-ui,"Microsoft YaHei"}}main{{width:min(680px,calc(100% - 32px));background:#fff;border:1px solid #dbe4e1;border-radius:24px;padding:30px;box-shadow:0 24px 80px #17322c1c}}h1{{margin:0 0 7px}}p{{color:#66736f}}dl{{border-top:1px solid #dbe4e1}}dt{{margin-top:18px;color:#66736f;font-size:13px;font-weight:650}}dd{{margin:4px 0 18px;font-weight:700}}.actions{{display:flex;gap:10px;justify-content:flex-end;margin-top:24px}}button{{border-radius:13px;padding:12px 17px;font:inherit;font-weight:700;cursor:pointer}}.edit{{border:1px solid #dbe4e1;background:#fff;color:#66736f}}.submit{{border:1px solid #0b6b5d;background:#0b6b5d;color:#fff}}@media(max-width:560px){{.actions{{flex-direction:column-reverse}}}}
</style></head><body><main><p>提交前确认</p><h1>这些信息会用于本次证据判断</h1><dl>{''.join(rows)}</dl><form method="post">{''.join(hidden)}<div class="actions"><button class="edit" formaction="/{token}/edit">修改选择</button><button class="submit" name="action" value="submit" formaction="/{token}/submit">确认并生成建议</button></div></form></main></body></html>""".encode("utf-8")


def success_page(skipped: bool) -> bytes:
    message = "已选择跳过；当前任务将按一般情境继续。" if skipped else "选择已自动回传，并已触发当前任务继续。"
    return f"""<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>已收到</title><body style="margin:0;min-height:100vh;display:grid;place-items:center;background:#f1f5f3;font-family:system-ui"><main data-testid="intake-complete" style="background:white;border:1px solid #dbe4e1;border-radius:22px;padding:34px;box-shadow:0 20px 60px #17322c1c;max-width:560px"><p style="color:#0b6b5d;font-weight:700">已完成</p><h1 style="margin-top:0">信息已安全提交</h1><p>{html.escape(message)}</p><p><strong>无需再发送“已提交”。</strong>请保持当前任务打开，快速结果目标在3分钟内生成。</p><p style="color:#66736f">一次性本地服务现已关闭；可回到对话查看进度。</p></main></body></html>""".encode("utf-8")


def run_server(questionnaire: dict, response_path: Path, port: int, timeout: int) -> str:
    token = secrets.token_urlsafe(18)

    class Handler(BaseHTTPRequestHandler):
        def send_html(self, status: int, body: bytes) -> None:
            self.send_response(status)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Security-Policy", "default-src 'none'; style-src 'unsafe-inline'; script-src 'unsafe-inline'; form-action 'self'; base-uri 'none'")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            self.end_headers()
            self.wfile.write(body)

        def read_fields(self) -> dict[str, list[str]] | None:
            try:
                length = int(self.headers.get("Content-Length", "0"))
            except ValueError:
                length = 0
            if length < 1 or length > MAX_BODY:
                self.send_html(400, b"Invalid request")
                return None
            return urllib.parse.parse_qs(
                self.rfile.read(length).decode("utf-8"), keep_blank_values=False
            )

        def do_GET(self) -> None:  # noqa: N802
            if self.path.rstrip("/") != f"/{token}":
                self.send_html(404, b"Not found")
                return
            self.send_html(200, build_page(questionnaire, token).encode("utf-8"))

        def do_POST(self) -> None:  # noqa: N802
            if self.path not in {f"/{token}/review", f"/{token}/edit", f"/{token}/submit"}:
                self.send_html(404, b"Not found")
                return
            fields = self.read_fields()
            if fields is None:
                return
            skipped = fields.get("action", [""])[0] == "skip"
            if skipped and self.path == f"/{token}/submit":
                answers, labels, selected = {}, {}, {}
            else:
                try:
                    answers, labels, selected = extract_answers(questionnaire, fields)
                except ValueError as exc:
                    self.send_html(400, f"<meta charset='utf-8'><p>{html.escape(str(exc))}</p>".encode("utf-8"))
                    return
            if self.path == f"/{token}/review":
                self.send_html(200, review_page(questionnaire, token, labels, selected))
                return
            if self.path == f"/{token}/edit":
                self.send_html(200, build_page(questionnaire, token, selected).encode("utf-8"))
                return
            submitted_at = datetime.now(timezone.utc)
            payload = {
                "schema_version": "nutrition-intake-v2",
                "submitted_at_utc": submitted_at.isoformat(timespec="seconds"),
                "quick_result_deadline_utc": (submitted_at + timedelta(minutes=3)).isoformat(timespec="seconds"),
                "skipped": skipped,
                "answers": answers,
                "answer_labels": labels,
            }
            response_path.parent.mkdir(parents=True, exist_ok=True)
            response_path.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
            )
            self.server.completed = True  # type: ignore[attr-defined]
            self.send_html(200, success_page(skipped))

        def log_message(self, *_args: object) -> None:
            return

    server = HTTPServer(("127.0.0.1", port), Handler)
    server.timeout = 1
    server.completed = False  # type: ignore[attr-defined]
    url = f"http://127.0.0.1:{server.server_port}/{token}"
    print(json.dumps({"status": "waiting", "url": url, "response": str(response_path)}, ensure_ascii=False), flush=True)
    deadline = time.monotonic() + timeout
    while not server.completed and time.monotonic() < deadline:  # type: ignore[attr-defined]
        server.handle_request()
    server.server_close()
    if not server.completed:  # type: ignore[attr-defined]
        fail(f"questionnaire timed out after {timeout} seconds")
    return url


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Collect up to five clickable intake answers on localhost")
    parser.add_argument("questionnaire", type=Path, help="UTF-8 questionnaire JSON")
    parser.add_argument("--response", required=True, type=Path, help="temporary response JSON path")
    parser.add_argument("--port", type=int, default=0, help="localhost port; 0 chooses an available port")
    parser.add_argument("--timeout", type=int, default=900, help="seconds to wait, from 30 to 1800")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if not 0 <= args.port <= 65535:
        print("error: --port must be 0 to 65535", file=sys.stderr)
        return 2
    if not 30 <= args.timeout <= 1800:
        print("error: --timeout must be 30 to 1800", file=sys.stderr)
        return 2
    try:
        questionnaire = validate_questionnaire(json.loads(args.questionnaire.read_text(encoding="utf-8")))
        run_server(questionnaire, args.response, args.port, args.timeout)
        print(json.dumps({"status": "ok", "response": str(args.response)}, ensure_ascii=False), flush=True)
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "error", "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
