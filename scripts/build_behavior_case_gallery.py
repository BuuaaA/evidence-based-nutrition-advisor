"""Build deterministic result cards and the behavior-case HTML gallery."""

from __future__ import annotations

import html
import json
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from build_behavior_acceptance_case import COLORS, Canvas, font


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "examples" / "behavior-case-results.json"
ASSET_DIR = ROOT / "assets" / "behavior-cases"
GALLERY = ROOT / "examples" / "consumer-answer-demo.html"

WIDTH = 1800
HEIGHT = 1320
MARGIN = 72


def paragraph(
    canvas: Canvas,
    x: int,
    y: int,
    value: str,
    size: int,
    color: str,
    width: int,
    *,
    bold: bool = False,
    lines: int | None = None,
    gap: int = 8,
) -> int:
    return canvas.paragraph((x, y), value, size, color, width, gap, bold=bold, max_lines=lines)


def check(canvas: Canvas, x: int, y: int, value: str) -> None:
    canvas.circle((x, y + 3, x + 32, y + 35), COLORS["green"])
    canvas.line((x + 8, y + 19, x + 14, y + 26), COLORS["white"], 4)
    canvas.line((x + 14, y + 26, x + 25, y + 11), COLORS["white"], 4)
    paragraph(canvas, x + 48, y - 1, value, 23, COLORS["body"], 690, lines=2)


def build_card(case: dict, generated: str) -> Canvas:
    canvas = Canvas(
        WIDTH,
        HEIGHT,
        aria_label=f"行为验收用例 {case['id']}：{case['title']}",
    )
    case_id = int(case["id"])
    status = case["status"]
    status_color = COLORS["amber"] if "边界" in status else COLORS["green"]
    status_bg = COLORS["amber_bg"] if "边界" in status else COLORS["green_bg"]

    canvas.rounded_rect((0, 0, WIDTH, 248), 0, COLORS["navy"])
    canvas.rounded_rect((MARGIN, 34, MARGIN + 330, 84), 25, COLORS["navy_2"])
    canvas.text((MARGIN + 22, 41), f"行为验收用例 {case_id} · 实跑", 24, "#CDE3FF", bold=True)
    canvas.text((MARGIN, 106), case["title"], 50, COLORS["white"], bold=True)
    canvas.text((MARGIN, 180), f"输入：{case['prompt']}", 27, "#D8E5F6")
    canvas.rounded_rect((1450, 40, 1728, 96), 28, status_bg)
    canvas.text((1512, 53), status, 25, status_color, bold=True)

    canvas.rounded_rect((MARGIN, 286, WIDTH - MARGIN, 478), 24, COLORS["white"], COLORS["line"], 2)
    canvas.rounded_rect((MARGIN + 24, 310, MARGIN + 360, 366), 18, status_bg)
    canvas.text((MARGIN + 48, 321), case["verdict"], 25, status_color, bold=True)
    paragraph(canvas, MARGIN + 28, 390, case["result"], 29, COLORS["ink"], WIDTH - 2 * MARGIN - 56, lines=2, gap=10)

    canvas.text((MARGIN, 522), "证据与流程轨迹", 33, COLORS["ink"], bold=True)
    canvas.text((MARGIN + 310, 529), "每个数字都能回到仓库文件", 22, COLORS["muted"])
    card_gap = 18
    card_width = (WIDTH - 2 * MARGIN - 3 * card_gap) // 4
    for index, (label, value) in enumerate(case["trace"]):
        x1 = MARGIN + index * (card_width + card_gap)
        x2 = x1 + card_width
        canvas.rounded_rect((x1, 580, x2, 820), 22, COLORS["white"], COLORS["line"], 2)
        canvas.rounded_rect((x1 + 20, 600, x1 + 66, 646), 14, COLORS["blue_bg"])
        canvas.text((x1 + 35, 606), str(index + 1), 21, COLORS["blue"], bold=True)
        paragraph(canvas, x1 + 82, 602, label, 24, COLORS["ink"], card_width - 104, bold=True, lines=2)
        paragraph(canvas, x1 + 22, 676, value, 22, COLORS["body"], card_width - 44, lines=4, gap=8)

    canvas.text((MARGIN, 866), "验收点", 33, COLORS["ink"], bold=True)
    canvas.rounded_rect((MARGIN, 918, WIDTH - MARGIN, 1078), 22, COLORS["white"], COLORS["line"], 2)
    for index, item in enumerate(case["checks"]):
        col = index % 2
        row = index // 2
        check(canvas, MARGIN + 32 + col * 810, 946 + row * 62, item)

    canvas.rounded_rect((MARGIN, 1110, WIDTH - MARGIN, 1236), 22, COLORS["amber_bg"])
    canvas.text((MARGIN + 26, 1132), "边界说明", 24, COLORS["amber"], bold=True)
    paragraph(canvas, MARGIN + 166, 1128, case["boundary"], 23, COLORS["body"], WIDTH - 2 * MARGIN - 196, lines=3, gap=8)

    canvas.line((MARGIN, 1270, WIDTH - MARGIN, 1270), COLORS["line"], 2)
    canvas.text((MARGIN, 1287), "evidence-based-nutrition-advisor V1.0.1 · 行为验收结果卡", 19, COLORS["muted"])
    canvas.text((1450, 1287), f"更新 {generated}", 19, COLORS["muted"])
    return canvas


def build_contact_sheet(paths: list[Path]) -> Path:
    thumb_width, thumb_height = 600, 440
    columns = 4
    rows = math.ceil(len(paths) / columns)
    sheet = Image.new("RGB", (thumb_width * columns, thumb_height * rows), "#E8EEF6")
    for index, path in enumerate(paths):
        image = Image.open(path).convert("RGB")
        image.thumbnail((thumb_width - 24, thumb_height - 24), Image.Resampling.LANCZOS)
        x = (index % columns) * thumb_width + (thumb_width - image.width) // 2
        y = (index // columns) * thumb_height + (thumb_height - image.height) // 2
        sheet.paste(image, (x, y))
    output = ASSET_DIR / "contact-sheet.png"
    sheet.save(output, format="PNG", optimize=True)
    return output


def card_html(case: dict) -> str:
    slug = html.escape(case["slug"])
    detail = html.escape(case["detail"])
    evidence = html.escape(case["evidence"])
    open_attr = " open" if int(case["id"]) == 2 else ""
    status_class = "boundary" if "边界" in case["status"] else "pass"
    return f"""
      <article class="case" id="case-{case['id']}">
        <div class="case-copy">
          <p class="eyebrow">用例 {case['id']} · {html.escape(case['category'])}</p>
          <div class="title-row"><h2>{html.escape(case['title'])}</h2><span class="status {status_class}">{html.escape(case['status'])}</span></div>
          <p class="prompt">“{html.escape(case['prompt'])}”</p>
          <p class="verdict">{html.escape(case['verdict'])}</p>
          <p>{html.escape(case['result'])}</p>
          <p class="links"><a href="{detail}">查看详细结果</a><a href="{evidence}">查看运行证据</a><a href="../assets/behavior-cases/case-{int(case['id']):02d}-{slug}.svg">下载 SVG</a></p>
        </div>
        <details{open_attr}>
          <summary>展开结果说明图</summary>
          <a class="image-link" href="../assets/behavior-cases/case-{int(case['id']):02d}-{slug}.png">
            <img loading="lazy" src="../assets/behavior-cases/case-{int(case['id']):02d}-{slug}.png" alt="行为验收用例 {case['id']}：{html.escape(case['title'])}的结果说明图">
          </a>
        </details>
      </article>"""


def build_gallery(payload: dict) -> None:
    nav = "".join(
        f'<a href="#case-{case["id"]}">{case["id"]}. {html.escape(case["category"])}</a>'
        for case in payload["cases"]
    )
    cases = "\n".join(card_html(case).strip() for case in payload["cases"])
    document = f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <meta name="description" content="evidence-based-nutrition-advisor V1.0.1 的十四个行为验收实跑案例">
  <title>普通用户可视化示例｜evidence-based-nutrition-advisor V1.0.1</title>
  <style>
    :root{{--ink:#172033;--muted:#667085;--line:#d8e1ec;--paper:#f3f6fa;--navy:#10233f;--blue:#175cd3;--green:#067647;--amber:#b54708}}
    *{{box-sizing:border-box}} body{{margin:0;color:var(--ink);background:var(--paper);font-family:"Microsoft YaHei","PingFang SC",system-ui,sans-serif;line-height:1.72}}
    a{{color:var(--blue);text-underline-offset:3px}} .hero{{background:linear-gradient(135deg,#10233f,#173f70);color:#fff;padding:72px 24px 58px}}
    .hero-inner,.main{{max-width:1180px;margin:auto}} .kicker{{color:#b9d8ff;font-weight:700;letter-spacing:.08em}}
    h1{{font-size:clamp(2rem,5vw,3.6rem);line-height:1.16;margin:.3em 0}} .lead{{font-size:1.16rem;max-width:860px;color:#d9e6f5}}
    .hero-note{{margin-top:26px;padding:16px 18px;border:1px solid #57779e;border-radius:14px;background:#ffffff0d;color:#e8f1fb}}
    .nav{{display:flex;gap:9px;flex-wrap:wrap;margin-top:24px}} .nav a{{color:#e8f3ff;text-decoration:none;border:1px solid #6483a7;border-radius:999px;padding:6px 12px;font-size:.88rem}}
    .main{{padding:38px 18px 80px}} .intro{{background:#fff;border:1px solid var(--line);border-radius:18px;padding:24px 28px;margin-bottom:26px}}
    .case{{background:#fff;border:1px solid var(--line);border-radius:22px;overflow:hidden;margin:24px 0;box-shadow:0 12px 34px #3440540c}}
    .case-copy{{padding:30px 32px 22px}} .eyebrow{{color:var(--blue);font-weight:700;margin:0 0 7px}}
    .title-row{{display:flex;align-items:center;gap:14px;justify-content:space-between}} h2{{font-size:clamp(1.35rem,3vw,2rem);line-height:1.3;margin:0}}
    .status{{white-space:nowrap;border-radius:999px;padding:4px 11px;font-size:.86rem;font-weight:700}} .status.pass{{color:var(--green);background:#ecfdf3}} .status.boundary{{color:var(--amber);background:#fff6e5}}
    .prompt{{font-size:1.08rem;color:#475467;background:#f7f9fc;border-left:4px solid #98bce9;padding:9px 14px}}
    .verdict{{font-size:1.18rem;font-weight:800;color:#10233f;margin-bottom:0}} .links{{display:flex;gap:18px;flex-wrap:wrap;margin-bottom:0}}
    details{{border-top:1px solid var(--line);background:#f8fafc}} summary{{cursor:pointer;padding:17px 32px;font-weight:700;color:#344054}}
    .image-link{{display:block;padding:0 18px 20px}} img{{display:block;width:100%;height:auto;border:1px solid var(--line);border-radius:14px;background:#fff}}
    footer{{max-width:1180px;margin:auto;padding:0 18px 50px;color:var(--muted)}}
    @media(max-width:640px){{.hero{{padding-top:46px}}.case-copy{{padding:23px 20px}}.title-row{{align-items:flex-start;flex-direction:column}}summary{{padding-inline:20px}}}}
  </style>
</head>
<body>
  <header class="hero"><div class="hero-inner">
    <p class="kicker">EVIDENCE-BASED NUTRITION ADVISOR · V1.0.1</p>
    <h1>普通用户可视化示例</h1>
    <p class="lead">十四个行为验收用例的真实运行结果：既展示回答变得更可核查，也展示证据链不完整或安全门未通过时系统如何拒绝给出假确定性。</p>
    <div class="hero-note">这些是方法与交付示例，不是针对任何人的当前医疗建议。图卡由结构化案例数据确定性生成；详细页、检索清单和筛选记录可继续展开。</div>
    <nav class="nav" aria-label="案例导航">{nav}</nav>
  </div></header>
  <main class="main">
    <section class="intro"><strong>怎么看：</strong>{html.escape(payload['method_note'])} 首页代表案例是“补充氨糖软骨素能缓解关节疼痛吗？”，商品名案例仅保留在本画廊。</section>
    {cases}
  </main>
  <footer>evidence-based-nutrition-advisor V1.0.1 · 生成日期：{html.escape(payload['generated'])} · <a href="../tests/behavior-cases.md">查看完整验收规范</a> · <a href="../README.md">返回项目首页</a></footer>
</body>
</html>"""
    GALLERY.write_text(document, encoding="utf-8")


def main() -> None:
    payload = json.loads(DATA.read_text(encoding="utf-8"))
    cases = payload.get("cases", [])
    if [case.get("id") for case in cases] != list(range(1, 15)):
        raise ValueError("behavior-case-results.json must contain case ids 1 through 14")
    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    png_paths: list[Path] = []
    for case in cases:
        stem = f"case-{int(case['id']):02d}-{case['slug']}"
        png = ASSET_DIR / f"{stem}.png"
        svg = ASSET_DIR / f"{stem}.svg"
        build_card(case, payload["generated"]).save(png, svg)
        png_paths.append(png)
    contact = build_contact_sheet(png_paths)
    build_gallery(payload)
    print(json.dumps({"status": "ok", "cases": len(cases), "gallery": str(GALLERY), "contact_sheet": str(contact)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
