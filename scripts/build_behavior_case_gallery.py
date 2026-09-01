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

# Hallmark · shared editorial palette. Canvas reads this mapping at render time,
# so updating it here keeps PNG and text-preserving SVG output in sync.
COLORS.update(
    {
        "navy": "#F4F1E9",
        "navy_2": "#E7ECE7",
        "ink": "#1A2823",
        "body": "#34433D",
        "muted": "#65716C",
        "line": "#C9D0C8",
        "paper": "#F4F1E9",
        "white": "#FBFAF5",
        "green": "#0B6657",
        "green_bg": "#E4F0EB",
        "blue": "#0B6657",
        "blue_bg": "#E7F0EC",
        "amber": "#9B4E18",
        "amber_bg": "#F8EEDC",
        "red": "#963C34",
        "red_bg": "#F7E8E4",
    }
)


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
    canvas.rounded_rect((x, y + 8, x + 18, y + 26), 0, COLORS["green"])
    canvas.line((x + 4, y + 17, x + 8, y + 21), COLORS["white"], 3)
    canvas.line((x + 8, y + 21, x + 15, y + 12), COLORS["white"], 3)
    paragraph(canvas, x + 34, y - 1, value, 23, COLORS["body"], 700, lines=2)


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

    canvas.rounded_rect((0, 0, WIDTH, HEIGHT), 0, COLORS["paper"])
    canvas.text((MARGIN, 38), f"EVIDENCE REVIEW FILE · {case_id:02d} / 14", 19, COLORS["muted"], mono=True)
    canvas.text((WIDTH - 300, 38), f"UPDATED {generated}", 19, COLORS["muted"], mono=True)
    canvas.line((MARGIN, 78, WIDTH - MARGIN, 78), COLORS["ink"], 3)
    canvas.line((MARGIN, 86, WIDTH - MARGIN, 86), COLORS["line"], 1)
    canvas.text((MARGIN, 116), case["title"], 46, COLORS["ink"], bold=True)
    canvas.text((MARGIN, 184), f"输入：{case['prompt']}", 26, COLORS["body"])
    canvas.rounded_rect((1450, 112, 1728, 166), 0, status_bg)
    canvas.text((1510, 125), status, 24, status_color, bold=True)

    canvas.line((MARGIN, 250, WIDTH - MARGIN, 250), COLORS["line"], 2)
    canvas.text((MARGIN, 282), case["verdict"], 29, status_color, bold=True)
    paragraph(canvas, MARGIN, 342, case["result"], 30, COLORS["ink"], WIDTH - 2 * MARGIN, lines=2, gap=10)
    canvas.line((MARGIN, 450, WIDTH - MARGIN, 450), COLORS["line"], 2)

    canvas.text((MARGIN, 492), "证据与流程轨迹", 33, COLORS["ink"], bold=True)
    canvas.text((MARGIN + 320, 499), "每一项都能回到仓库文件", 22, COLORS["muted"])
    card_gap = 0
    card_width = (WIDTH - 2 * MARGIN) // 4
    for index, (label, value) in enumerate(case["trace"]):
        x1 = MARGIN + index * (card_width + card_gap)
        x2 = x1 + card_width
        canvas.line((x1, 552, x2, 552), COLORS["ink"], 2)
        canvas.line((x1, 790, x2, 790), COLORS["line"], 2)
        if index:
            canvas.line((x1, 552, x1, 790), COLORS["line"], 2)
        canvas.text((x1 + 18, 574), f"0{index + 1}", 19, COLORS["green"], mono=True)
        paragraph(canvas, x1 + 18, 616, label, 24, COLORS["ink"], card_width - 36, bold=True, lines=2)
        paragraph(canvas, x1 + 18, 678, value, 21, COLORS["body"], card_width - 36, lines=4, gap=7)

    canvas.text((MARGIN, 838), "验收点", 33, COLORS["ink"], bold=True)
    canvas.line((MARGIN, 890, WIDTH - MARGIN, 890), COLORS["ink"], 2)
    for index, item in enumerate(case["checks"]):
        col = index % 2
        row = index // 2
        check(canvas, MARGIN + 18 + col * 820, 920 + row * 62, item)
    canvas.line((MARGIN, 1050, WIDTH - MARGIN, 1050), COLORS["line"], 2)

    canvas.rounded_rect((MARGIN, 1090, MARGIN + 142, 1134), 0, status_bg)
    canvas.text((MARGIN + 16, 1098), "边界说明", 22, status_color, bold=True)
    paragraph(canvas, MARGIN, 1154, case["boundary"], 23, COLORS["body"], WIDTH - 2 * MARGIN, lines=3, gap=8)

    canvas.line((MARGIN, 1268, WIDTH - MARGIN, 1268), COLORS["ink"], 2)
    canvas.text((MARGIN, 1285), "evidence-based-nutrition-advisor V1.0.1 · ACCEPTANCE FILE", 18, COLORS["muted"], mono=True)
    return canvas


def build_contact_sheet(paths: list[Path]) -> Path:
    thumb_width, thumb_height = 600, 440
    columns = 4
    rows = math.ceil(len(paths) / columns)
    sheet = Image.new("RGB", (thumb_width * columns, thumb_height * rows), COLORS["paper"])
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
    detail_label = html.escape(case.get("detail_label", "查看详细结果"))
    evidence_label = html.escape(case.get("evidence_label", "查看运行证据"))
    open_attr = " open" if int(case["id"]) == 2 else ""
    status_class = "boundary" if "边界" in case["status"] else "pass"
    return f"""
      <article class="case" id="case-{case['id']}">
        <div class="case-copy">
          <p class="case-index">{int(case['id']):02d} / 14 · {html.escape(case['category'])}</p>
          <div class="title-row"><h2>{html.escape(case['title'])}</h2><span class="status {status_class}">{html.escape(case['status'])}</span></div>
          <p class="prompt">“{html.escape(case['prompt'])}”</p>
          <p class="verdict">{html.escape(case['verdict'])}</p>
          <p>{html.escape(case['result'])}</p>
          <p class="links"><a href="{detail}">{detail_label}</a><a href="{evidence}">{evidence_label}</a><a href="../assets/behavior-cases/case-{int(case['id']):02d}-{slug}.svg">下载 SVG</a></p>
        </div>
        <details{open_attr}>
          <summary>展开结果说明图</summary>
          <a class="image-link" href="../assets/behavior-cases/case-{int(case['id']):02d}-{slug}.png">
            <img loading="lazy" width="1800" height="1320" src="../assets/behavior-cases/case-{int(case['id']):02d}-{slug}.png" alt="行为验收用例 {case['id']}：{html.escape(case['title'])}的结果说明图">
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
    /* Hallmark · genre: editorial · macrostructure: Catalogue · theme: Newsprint · enrichment: none · nav: N6 · footer: Ft4 · contrast: pass · slop: pass · pre-emit critique: P5 H5 E5 S5 R5 V5 */
    :root{{
      --color-paper:oklch(96% .012 92);--color-paper-2:oklch(98% .008 92);--color-ink:oklch(22% .018 165);
      --color-body:oklch(34% .014 165);--color-muted:oklch(42% .012 165);--color-rule:oklch(80% .014 150);
      --color-accent:oklch(45% .105 170);--color-accent-soft:oklch(92% .028 170);--color-warn:oklch(48% .105 55);--color-warn-soft:oklch(93% .034 70);
      --font-display:"Noto Serif CJK SC","Songti SC",serif;--font-body:"IBM Plex Sans","Noto Sans CJK SC","PingFang SC","Microsoft YaHei",sans-serif;
      --font-mono:"IBM Plex Mono","SFMono-Regular",monospace;--space-3xs:.125rem;--space-2xs:.25rem;--space-xs:.5rem;--space-sm:.75rem;--space-md:1rem;--space-lg:1.5rem;--space-xl:2.5rem;--space-2xl:4rem;
      --text-xs:.8rem;--text-sm:.9rem;--text-base:1rem;--text-md:1.25rem;--text-lg:1.5625rem;--text-xl:1.953rem;--rule-hair:1px;
    }}
    *{{box-sizing:border-box}}html,body{{overflow-x:clip}}body{{margin:0;color:var(--color-ink);background:var(--color-paper);font:var(--text-base)/1.68 var(--font-body)}}
    a{{color:var(--color-accent);text-underline-offset:.2em}}a:focus-visible,summary:focus-visible{{outline:3px solid var(--color-accent);outline-offset:3px}}
    .hero-inner,.main,footer{{width:min(76rem,calc(100% - 2rem));margin-inline:auto}}
    .hero{{padding-block:var(--space-lg) var(--space-xl)}}.kicker{{margin:0;text-align:start;color:var(--color-muted);font:700 var(--text-xs)/1.4 var(--font-body);letter-spacing:.08em}}
    h1{{margin:var(--space-sm) 0 0;text-align:center;font:700 clamp(2.15rem,7vw,4.5rem)/1.02 var(--font-display);letter-spacing:-.035em;overflow-wrap:anywhere}}
    .lead{{max-width:64ch;margin:var(--space-lg) auto 0;text-align:center;font-size:var(--text-md);color:var(--color-body)}}
    .hero-note{{max-width:76ch;margin:var(--space-lg) auto 0;padding-block:var(--space-md);border-block:var(--rule-hair) solid var(--color-rule);color:var(--color-muted)}}
    .nav{{display:flex;justify-content:center;gap:var(--space-sm) var(--space-lg);flex-wrap:wrap;margin-top:var(--space-lg);padding-block:var(--space-sm);border-bottom:4px double var(--color-ink)}}
    .nav a{{white-space:nowrap;color:var(--color-body);font:var(--text-xs)/1.4 var(--font-body);text-decoration:none}}.nav a:hover{{text-decoration:underline}}
    .main{{padding-block:var(--space-xl) var(--space-2xl)}}.intro{{max-width:72ch;margin-bottom:var(--space-lg);font-size:var(--text-md)}}
    .quick-card{{display:grid;gap:var(--space-md);align-items:center;margin-bottom:var(--space-2xl);padding-block:var(--space-lg);border-block:2px solid var(--color-ink)}}
    .quick-card p{{margin:0;max-width:68ch}}.quick-card a{{width:max-content;min-height:44px;padding:var(--space-sm) var(--space-md);border:1px solid var(--color-accent);white-space:nowrap;text-decoration:none;font-weight:700}}
    .catalogue{{display:grid;gap:var(--space-xl)}}.case{{min-width:0;border-top:2px solid var(--color-ink);border-bottom:var(--rule-hair) solid var(--color-rule)}}
    .case-copy{{padding-block:var(--space-lg)}}.case-index{{margin:0 0 var(--space-md);color:var(--color-muted);font:700 var(--text-xs)/1.4 var(--font-mono);font-variant-numeric:tabular-nums}}
    .title-row{{display:grid;gap:var(--space-sm)}}h2{{min-width:0;margin:0;font:700 clamp(1.45rem,4vw,2rem)/1.18 var(--font-display);letter-spacing:-.02em;overflow-wrap:anywhere}}
    .status{{display:inline-flex;align-items:center;gap:var(--space-xs);width:max-content;white-space:nowrap;font-size:var(--text-sm);font-weight:700}}.status::before{{content:"";width:.65rem;height:.65rem;background:currentColor}}.status.pass{{color:var(--color-accent)}}.status.boundary{{color:var(--color-warn)}}
    .prompt{{margin-block:var(--space-lg);padding-block:var(--space-sm);border-block:var(--rule-hair) solid var(--color-rule);color:var(--color-body)}}
    .verdict{{margin-bottom:0;color:var(--color-ink);font-size:var(--text-md);font-weight:800}}.links{{display:flex;gap:var(--space-sm) var(--space-lg);flex-wrap:wrap;margin-bottom:0}}.links a{{white-space:nowrap}}
    details{{border-top:var(--rule-hair) solid var(--color-rule)}}summary{{display:flex;align-items:center;min-height:48px;cursor:pointer;color:var(--color-body);font-weight:700}}
    .image-link{{display:block;padding-bottom:var(--space-md)}}img{{display:block;width:100%;height:auto;border:var(--rule-hair) solid var(--color-rule);background:var(--color-paper-2)}}
    footer{{padding-block:0 var(--space-xl);border-top:4px double var(--color-ink);color:var(--color-muted);font:var(--text-xs)/1.6 var(--font-mono)}}footer a{{white-space:nowrap}}
    @media(min-width:40rem){{.quick-card{{grid-template-columns:minmax(0,1fr) auto}}.title-row{{grid-template-columns:minmax(0,1fr) auto;align-items:start}}}}
    @media(min-width:64rem){{.catalogue{{grid-template-columns:repeat(2,minmax(0,1fr));gap:var(--space-2xl) var(--space-xl)}}}}
  </style>
</head>
<body>
  <header class="hero"><div class="hero-inner">
    <p class="kicker">EVIDENCE-BASED NUTRITION ADVISOR · V1.0.1</p>
    <h1>证据验收档案</h1>
    <p class="lead">十四个实跑用例，记录系统在信息不足、证据链中断和安全门未通过时如何作答、升级或停止。</p>
    <div class="hero-note">本页用于展示方法与交付结构，不提供个人医疗建议。所有图卡由结构化案例数据生成，详细答案、检索清单和筛选记录均可回查。</div>
    <nav class="nav" aria-label="案例导航">{nav}</nav>
  </div></header>
  <main class="main">
    <section class="intro"><strong>怎么看：</strong>{html.escape(payload['method_note'])} 首页代表案例是“补充氨糖软骨素能缓解关节疼痛吗？”，商品名案例仅保留在本画廊。</section>
    <section class="quick-card" aria-label="普通用户快速证据卡示例">
      <p><strong>先看普通用户默认交付：</strong>L1-Quick 只显示三类已核验来源，不展示全量筛查或 GRADE；卡片带有“申请完整审计”按钮。</p>
      <a href="consumer-answer-quick-demo.html">打开快速证据卡</a>
    </section>
    <div class="catalogue">{cases}</div>
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
