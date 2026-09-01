"""Build a GitHub-ready behavior acceptance case image from verified evidence files."""

from __future__ import annotations

import argparse
import html
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from build_consumer_answer import validate, verify_evidence_bundle


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_JSON = ROOT / "examples" / "consumer-answer.sample.json"
DEFAULT_MANIFEST = ROOT / "examples" / "neuriva-pubmed-search-manifest.json"
DEFAULT_RIS = ROOT / "examples" / "neuriva-pubmed-search.ris"
DEFAULT_SCREENING = ROOT / "examples" / "neuriva-pubmed-screening.csv"
DEFAULT_PNG = ROOT / "assets" / "behavior-acceptance-neuriva.png"
DEFAULT_SVG = ROOT / "assets" / "behavior-acceptance-neuriva.svg"

WIDTH = 1800
HEIGHT = 2240
MARGIN = 76

COLORS = {
    "navy": "#10233F",
    "navy_2": "#17345C",
    "ink": "#162033",
    "body": "#344054",
    "muted": "#667085",
    "line": "#D7DFEA",
    "paper": "#F4F7FB",
    "white": "#FFFFFF",
    "green": "#067647",
    "green_bg": "#ECFDF3",
    "blue": "#175CD3",
    "blue_bg": "#EFF8FF",
    "amber": "#B54708",
    "amber_bg": "#FFF6E5",
    "red": "#B42318",
    "red_bg": "#FEF3F2",
}


def find_font(bold: bool = False, mono: bool = False) -> str:
    if mono:
        candidates = [
            Path("C:/Windows/Fonts/consola.ttf"),
            Path("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"),
        ]
    else:
        candidates = [
            Path("C:/Windows/Fonts/msyhbd.ttc" if bold else "C:/Windows/Fonts/msyh.ttc"),
            Path("/System/Library/Fonts/PingFang.ttc"),
            Path(
                "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"
                if bold
                else "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
            ),
            Path(
                "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
                if bold
                else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
            ),
        ]
    for path in candidates:
        if path.exists():
            return str(path)
    raise FileNotFoundError("No suitable font found")


REGULAR_FONT = find_font()
BOLD_FONT = find_font(bold=True)
MONO_FONT = find_font(mono=True)


def font(size: int, bold: bool = False, mono: bool = False) -> ImageFont.FreeTypeFont:
    path = MONO_FONT if mono else (BOLD_FONT if bold else REGULAR_FONT)
    return ImageFont.truetype(path, size=size)


class Canvas:
    """Draw the same layout to a PNG and a text-preserving SVG."""

    def __init__(self, width: int = WIDTH, height: int = HEIGHT, *, aria_label: str = "Neuriva 行为验收实跑案例") -> None:
        self.width = width
        self.height = height
        self.image = Image.new("RGB", (width, height), COLORS["paper"])
        self.draw = ImageDraw.Draw(self.image)
        self.svg: list[str] = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
            f'viewBox="0 0 {width} {height}" role="img" '
            f'aria-label="{html.escape(aria_label, quote=True)}">',
            f'<rect width="{width}" height="{height}" fill="{COLORS["paper"]}"/>',
        ]

    def rounded_rect(
        self,
        box: tuple[int, int, int, int],
        radius: int,
        fill: str,
        outline: str | None = None,
        width: int = 1,
    ) -> None:
        self.draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)
        x1, y1, x2, y2 = box
        stroke = f' stroke="{outline}" stroke-width="{width}"' if outline else ""
        self.svg.append(
            f'<rect x="{x1}" y="{y1}" width="{x2 - x1}" height="{y2 - y1}" '
            f'rx="{radius}" fill="{fill}"{stroke}/>'
        )

    def line(self, xy: tuple[int, int, int, int], fill: str, width: int = 2) -> None:
        self.draw.line(xy, fill=fill, width=width)
        x1, y1, x2, y2 = xy
        self.svg.append(
            f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{fill}" stroke-width="{width}"/>'
        )

    def circle(self, box: tuple[int, int, int, int], fill: str) -> None:
        self.draw.ellipse(box, fill=fill)
        x1, y1, x2, y2 = box
        self.svg.append(
            f'<circle cx="{(x1 + x2) / 2}" cy="{(y1 + y2) / 2}" r="{(x2 - x1) / 2}" fill="{fill}"/>'
        )

    def text(
        self,
        xy: tuple[int, int],
        value: str,
        size: int,
        fill: str,
        bold: bool = False,
        mono: bool = False,
    ) -> None:
        x, y = xy
        text_font = font(size, bold=bold, mono=mono)
        self.draw.text((x, y), value, font=text_font, fill=fill)
        family = "Consolas, monospace" if mono else "Microsoft YaHei, PingFang SC, Noto Sans CJK SC, sans-serif"
        weight = 700 if bold else 400
        baseline = y + size
        self.svg.append(
            f'<text x="{x}" y="{baseline}" font-family="{family}" font-size="{size}" '
            f'font-weight="{weight}" fill="{fill}">{html.escape(value)}</text>'
        )

    def wrap(self, value: str, size: int, max_width: int, bold: bool = False, mono: bool = False) -> list[str]:
        text_font = font(size, bold=bold, mono=mono)
        lines: list[str] = []
        for paragraph in value.splitlines() or [""]:
            if not paragraph:
                lines.append("")
                continue
            current = ""
            for char in paragraph:
                candidate = current + char
                if current and self.draw.textlength(candidate, font=text_font) > max_width:
                    lines.append(current.rstrip())
                    current = char.lstrip()
                else:
                    current = candidate
            if current:
                lines.append(current.rstrip())
        return lines

    def paragraph(
        self,
        xy: tuple[int, int],
        value: str,
        size: int,
        fill: str,
        max_width: int,
        line_gap: int = 10,
        bold: bool = False,
        mono: bool = False,
        max_lines: int | None = None,
    ) -> int:
        x, y = xy
        lines = self.wrap(value, size, max_width, bold=bold, mono=mono)
        if max_lines is not None:
            lines = lines[:max_lines]
        for line in lines:
            self.text((x, y), line, size, fill, bold=bold, mono=mono)
            y += size + line_gap
        return y

    def save(self, png_path: Path, svg_path: Path) -> None:
        png_path.parent.mkdir(parents=True, exist_ok=True)
        svg_path.parent.mkdir(parents=True, exist_ok=True)
        self.image.save(png_path, format="PNG", optimize=True)
        self.svg.append("</svg>")
        svg_path.write_text("".join(self.svg), encoding="utf-8")


def section_title(canvas: Canvas, y: int, index: str, title: str, note: str) -> None:
    canvas.rounded_rect((MARGIN, y, MARGIN + 52, y + 52), 16, COLORS["navy"])
    canvas.text((MARGIN + 16, y + 5), index, 28, COLORS["white"], bold=True)
    canvas.text((MARGIN + 72, y - 1), title, 36, COLORS["ink"], bold=True)
    canvas.text((MARGIN + 430, y + 6), note, 24, COLORS["muted"])


def check_item(canvas: Canvas, x: int, y: int, text_value: str) -> None:
    canvas.circle((x, y + 3, x + 34, y + 37), COLORS["green"])
    canvas.line((x + 8, y + 21, x + 15, y + 28), COLORS["white"], 4)
    canvas.line((x + 15, y + 28, x + 27, y + 12), COLORS["white"], 4)
    canvas.text((x + 52, y), text_value, 25, COLORS["body"])


def build_case(data: dict) -> Canvas:
    research = data["research"]
    search = research["search"]
    outcomes = research["outcomes"]
    canvas = Canvas()

    # Header
    canvas.rounded_rect((0, 0, WIDTH, 258), 0, COLORS["navy"])
    canvas.rounded_rect((MARGIN, 38, MARGIN + 330, 86), 24, COLORS["navy_2"])
    canvas.text((MARGIN + 22, 43), "行为验收用例 4 · 实跑", 24, "#CDE3FF", bold=True)
    canvas.text((MARGIN, 108), "Neuriva 脑活素：从模糊提问到可复核结论", 54, COLORS["white"], bold=True)
    canvas.text((MARGIN, 184), "输入：\u201cNeuriva 脑活素有用吗？\u201d", 28, "#D8E5F6")
    canvas.rounded_rect((1435, 42, 1724, 96), 27, COLORS["green_bg"])
    canvas.text((1470, 50), "证据包校验通过", 25, COLORS["green"], bold=True)

    # First-screen result
    section_title(canvas, 304, "1", "第一屏先给决定", f"{data['first_screen_chars']} / 150 字")
    canvas.rounded_rect((MARGIN, 380, 520, 712), 26, COLORS["white"], COLORS["line"], 2)
    canvas.text((112, 420), "购买结论", 25, COLORS["muted"], bold=True)
    canvas.text((112, 476), "不太值得买。", 53, COLORS["red"], bold=True)
    canvas.rounded_rect((112, 566, 476, 630), 18, COLORS["red_bg"])
    canvas.text((142, 580), "不是没有信号，而是证据不够稳", 23, COLORS["red"], bold=True)
    canvas.text((112, 660), f"证据更新：{research['updated']}", 22, COLORS["muted"])

    labels = [
        ("对谁可能有用", data["for_whom"], COLORS["blue"], COLORS["blue_bg"]),
        ("效果上限", data["effect_ceiling"], COLORS["amber"], COLORS["amber_bg"]),
        ("安全红线", data["safety_red_line"], COLORS["red"], COLORS["red_bg"]),
    ]
    card_x1, card_x2 = 558, WIDTH - MARGIN
    row_y = 380
    for label, body, accent, background in labels:
        canvas.rounded_rect((card_x1, row_y, card_x2, row_y + 96), 20, COLORS["white"], COLORS["line"], 2)
        canvas.rounded_rect((card_x1 + 18, row_y + 18, card_x1 + 190, row_y + 78), 16, background)
        canvas.text((card_x1 + 38, row_y + 30), label, 24, accent, bold=True)
        canvas.paragraph((card_x1 + 222, row_y + 22), body, 25, COLORS["body"], card_x2 - card_x1 - 252, 8, max_lines=2)
        row_y += 118

    # Audit trail
    section_title(canvas, 770, "2", "后台证据审计链", "不是按相关性随机挑几篇")
    card_width = 392
    card_gap = 18
    card_y1, card_y2 = 850, 1044
    steps = [
        ("历史基座", "未发现合格的产品级系统综述", "因此从头做 PubMed 快速证据普查"),
        ("PubMed 检索", f"{search['searched_at']} · 全部命中", f"{search['records_found']} 条命中 = {search['records_exported']} 条导出"),
        ("PICOS 筛选", f"{search['records_screened']} 条题录 · {search['full_text_assessed']} 篇全文", "1 项人体 RCT 纳入；1 项体外研究排除"),
        ("逐结局 GRADE", "人体体验与电脑测试分开评级", "低 / 极低，不给整款产品贴总等级"),
    ]
    for idx, (title, main, note) in enumerate(steps):
        x1 = MARGIN + idx * (card_width + card_gap)
        x2 = x1 + card_width
        canvas.rounded_rect((x1, card_y1, x2, card_y2), 22, COLORS["white"], COLORS["line"], 2)
        canvas.rounded_rect((x1 + 22, card_y1 + 20, x1 + 70, card_y1 + 68), 15, COLORS["blue_bg"])
        canvas.text((x1 + 38, card_y1 + 26), str(idx + 1), 22, COLORS["blue"], bold=True)
        canvas.text((x1 + 86, card_y1 + 24), title, 26, COLORS["ink"], bold=True)
        canvas.paragraph((x1 + 24, card_y1 + 86), main, 23, COLORS["body"], card_width - 48, 8, max_lines=2)
        canvas.paragraph((x1 + 24, card_y1 + 146), note, 20, COLORS["muted"], card_width - 48, 6, max_lines=2)

    canvas.rounded_rect((MARGIN, 1074, WIDTH - MARGIN, 1268), 22, "#0F1F36")
    canvas.text((MARGIN + 28, 1095), "可复现 PubMed 检索式", 23, "#91CAFF", bold=True)
    canvas.paragraph((MARGIN + 28, 1138), search["query"], 22, "#F1F5F9", WIDTH - 2 * MARGIN - 56, 8, mono=True, max_lines=3)
    canvas.text((MARGIN + 28, 1224), "Query Translation、RIS SHA-256 与逐条筛选理由均保存在仓库证据包中。", 21, "#B7C7DB")

    # Outcome-level decision
    section_title(canvas, 1324, "3", "结局级裁决", "同一项试验，不同结局不能合成一句“有效”")
    outcome_width = (WIDTH - 2 * MARGIN - 28) // 2
    outcome_colors = [(COLORS["amber"], COLORS["amber_bg"]), (COLORS["blue"], COLORS["blue_bg"])]
    for idx, outcome in enumerate(outcomes):
        x1 = MARGIN + idx * (outcome_width + 28)
        x2 = x1 + outcome_width
        accent, background = outcome_colors[idx]
        canvas.rounded_rect((x1, 1402, x2, 1692), 24, COLORS["white"], COLORS["line"], 2)
        canvas.rounded_rect((x1 + 24, 1426, x1 + 168, 1482), 18, background)
        canvas.text((x1 + 50, 1437), f"GRADE {outcome['certainty']}", 22, accent, bold=True)
        canvas.paragraph((x1 + 24, 1500), outcome["outcome"], 31, COLORS["ink"], outcome_width - 48, 8, bold=True, max_lines=2)
        canvas.paragraph((x1 + 24, 1578), f"结果：{outcome['effect']}", 24, COLORS["body"], outcome_width - 48, 8, max_lines=2)
        canvas.paragraph((x1 + 24, 1640), outcome["why"], 19, COLORS["muted"], outcome_width - 48, 6, max_lines=2)

    # Acceptance checklist and limitations
    section_title(canvas, 1742, "4", "行为验收结果", "关键不变量全部可核查")
    canvas.rounded_rect((MARGIN, 1818, 1192, 2128), 24, COLORS["white"], COLORS["line"], 2)
    checks = [
        "明确购买判定置于第一句",
        "第一屏仅四项，共 91 字",
        "历史证据基座有记录",
        "PubMed 检索式可复现",
        "2 / 2 条命中完成筛查",
        "PICOS 纳排与排除理由齐全",
        "GRADE 按结局展示五个域",
        "HTML 只有三个一级展开入口",
    ]
    for idx, item in enumerate(checks):
        col = idx % 2
        row = idx // 2
        check_item(canvas, 112 + col * 532, 1854 + row * 62, item)

    canvas.rounded_rect((1220, 1818, WIDTH - MARGIN, 2128), 24, COLORS["amber_bg"])
    canvas.text((1252, 1850), "边界说明", 28, COLORS["amber"], bold=True)
    canvas.paragraph(
        (1252, 1904),
        search["limits"],
        23,
        COLORS["body"],
        WIDTH - MARGIN - 1252 - 28,
        10,
        max_lines=7,
    )
    canvas.text((1252, 2070), "定位：快速证据综合，不冒充发表级系统综述。", 20, COLORS["amber"], bold=True)

    # Footer
    canvas.line((MARGIN, 2170, WIDTH - MARGIN, 2170), COLORS["line"], 2)
    canvas.text((MARGIN, 2190), "来源：consumer-answer.sample.json · PubMed manifest · 原始 RIS · screening.csv", 20, COLORS["muted"])
    canvas.text((1372, 2190), f"生成日期 {research['updated']}", 20, COLORS["muted"])
    return canvas


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--ris", type=Path, default=DEFAULT_RIS)
    parser.add_argument("--screening", type=Path, default=DEFAULT_SCREENING)
    parser.add_argument("--png", type=Path, default=DEFAULT_PNG)
    parser.add_argument("--svg", type=Path, default=DEFAULT_SVG)
    args = parser.parse_args()

    raw = json.loads(args.input.read_text(encoding="utf-8"))
    validated = validate(raw)
    verify_evidence_bundle(validated, args.manifest, args.ris, args.screening)
    raw["first_screen_chars"] = validated["first_screen_chars"]
    canvas = build_case(raw)
    canvas.save(args.png, args.svg)
    print(
        json.dumps(
            {
                "status": "ok",
                "evidence_bundle_verified": True,
                "first_screen_chars": validated["first_screen_chars"],
                "png": str(args.png.resolve()),
                "svg": str(args.svg.resolve()),
                "size": f"{WIDTH}x{HEIGHT}",
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
