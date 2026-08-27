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
from datetime import datetime, timezone
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
            normalized_options.append({
                "value": value,
                "label": clean_text(
                    option.get("label"), f"questions[{index}].options[{option_index}].label"
                ),
            })
        normalized.append({
            "id": question_id,
            "prompt": prompt,
            "why": why,
            "options": normalized_options,
        })
    return {"title": title, "subtitle": subtitle, "questions": normalized}


def build_page(questionnaire: dict, token: str) -> str:
    question_blocks = []
    for index, question in enumerate(questionnaire["questions"], start=1):
        choices = "".join(
            '<label class="choice">'
            f'<input type="radio" name="{html.escape(question["id"])}" '
            f'value="{html.escape(option["value"])}" required>'
            f'<span>{html.escape(option["label"])}</span></label>'
            for option in question["options"]
        )
        why = (
            f'<p class="why">为什么问：{html.escape(question["why"])}</p>'
            if question["why"] else ""
        )
        question_blocks.append(
            f'<fieldset><legend><span>{index}</span>{html.escape(question["prompt"])}</legend>'
            f'{why}<div class="choices">{choices}</div></fieldset>'
        )
    subtitle = (
        f'<p class="subtitle">{html.escape(questionnaire["subtitle"])}</p>'
        if questionnaire["subtitle"] else ""
    )
    return f"""<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(questionnaire['title'])}</title>
<style>
:root{{--ink:#172033;--muted:#667085;--line:#d7dfea;--accent:#175cd3;--soft:#eff8ff;--bg:#eef2f7}}
*{{box-sizing:border-box}} body{{margin:0;background:var(--bg);color:var(--ink);font-family:"Microsoft YaHei","PingFang SC",system-ui,sans-serif}}
.backdrop{{min-height:100vh;display:grid;place-items:center;padding:22px}} .modal{{width:min(760px,100%);max-height:calc(100vh - 44px);overflow:auto;background:#fff;border:1px solid var(--line);border-radius:22px;box-shadow:0 24px 80px rgba(23,32,51,.22);padding:26px}}
.eyebrow{{font-size:13px;font-weight:700;letter-spacing:.08em;color:var(--accent)}} h1{{font-size:26px;line-height:1.35;margin:7px 0 6px}} .subtitle{{color:var(--muted);margin:0 0 20px;line-height:1.6}}
fieldset{{border:0;border-top:1px solid var(--line);padding:20px 0 4px;margin:0}} legend{{font-size:17px;font-weight:700;line-height:1.5;padding:0 8px 0 0}} legend span{{display:inline-grid;place-items:center;width:28px;height:28px;border-radius:9px;background:var(--soft);color:var(--accent);margin-right:9px}}
.why{{margin:7px 0 11px;color:var(--muted);font-size:14px}} .choices{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:9px}} .choice{{position:relative;cursor:pointer}}
.choice input{{position:absolute;opacity:0;pointer-events:none}} .choice span{{display:block;border:1px solid var(--line);border-radius:13px;padding:12px 14px;line-height:1.4;background:#fff}}
.choice input:checked+span{{border-color:var(--accent);background:var(--soft);box-shadow:0 0 0 2px rgba(23,92,211,.10)}} .choice input:focus-visible+span{{outline:3px solid rgba(23,92,211,.25)}}
.actions{{position:sticky;bottom:-26px;display:flex;gap:10px;justify-content:flex-end;background:linear-gradient(transparent,#fff 18%);padding:28px 0 2px}} button{{border-radius:12px;padding:11px 16px;font:inherit;font-weight:700;cursor:pointer}} .skip{{border:1px solid var(--line);background:#fff;color:var(--muted)}} .submit{{border:1px solid var(--accent);background:var(--accent);color:#fff}}
.note{{font-size:13px;color:var(--muted);margin:16px 0 0}} @media(max-width:600px){{.modal{{padding:20px}}.choices{{grid-template-columns:1fr}}.actions{{bottom:-20px}}}}
</style></head><body><div class="backdrop"><main class="modal" role="dialog" aria-modal="true" aria-labelledby="title">
<div class="eyebrow">生成证据前 · 最多 5 项</div><h1 id="title">{html.escape(questionnaire['title'])}</h1>{subtitle}
<form method="post" action="/{token}/submit">{''.join(question_blocks)}
<div class="actions"><button class="skip" name="action" value="skip" formnovalidate>跳过，先看一般结论</button><button class="submit" name="action" value="submit">按这些信息生成证据</button></div></form>
<p class="note">选择只发送到本机 127.0.0.1，不会上传到外部网站。Agent 读取后应删除临时回答文件。</p>
</main></div></body></html>"""


def success_page(skipped: bool) -> bytes:
    message = "已选择跳过；将按一般情境生成证据。" if skipped else "已收到选择；可以回到对话，Agent 将继续生成证据。"
    return f"""<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>已收到</title><body style="margin:0;min-height:100vh;display:grid;place-items:center;background:#eef2f7;font-family:system-ui"><main style="background:white;border-radius:20px;padding:32px;box-shadow:0 20px 60px #17203322;max-width:560px"><h1 style="margin-top:0">完成</h1><p>{html.escape(message)}</p></main></body></html>""".encode("utf-8")


def run_server(questionnaire: dict, response_path: Path, port: int, timeout: int) -> str:
    token = secrets.token_urlsafe(18)
    page = build_page(questionnaire, token).encode("utf-8")
    option_maps = {
        question["id"]: {option["value"]: option["label"] for option in question["options"]}
        for question in questionnaire["questions"]
    }

    class Handler(BaseHTTPRequestHandler):
        def send_html(self, status: int, body: bytes) -> None:
            self.send_response(status)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Security-Policy", "default-src 'none'; style-src 'unsafe-inline'; form-action 'self'; base-uri 'none'")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self) -> None:  # noqa: N802
            if self.path.rstrip("/") != f"/{token}":
                self.send_html(404, b"Not found")
                return
            self.send_html(200, page)

        def do_POST(self) -> None:  # noqa: N802
            if self.path != f"/{token}/submit":
                self.send_html(404, b"Not found")
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
            except ValueError:
                length = 0
            if length < 1 or length > MAX_BODY:
                self.send_html(400, b"Invalid request")
                return
            fields = urllib.parse.parse_qs(self.rfile.read(length).decode("utf-8"), keep_blank_values=False)
            skipped = fields.get("action", [""])[0] == "skip"
            answers: dict[str, str] = {}
            labels: dict[str, str] = {}
            if not skipped:
                for question_id, option_map in option_maps.items():
                    value = fields.get(question_id, [""])[0]
                    if value not in option_map:
                        self.send_html(400, "请完成全部选择。".encode("utf-8"))
                        return
                    answers[question_id] = value
                    labels[question_id] = option_map[value]
            payload = {
                "schema_version": "nutrition-intake-v1",
                "submitted_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "skipped": skipped,
                "answers": answers,
                "answer_labels": labels,
            }
            response_path.parent.mkdir(parents=True, exist_ok=True)
            response_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
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
