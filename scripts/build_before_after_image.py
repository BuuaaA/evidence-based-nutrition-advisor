"""Build the README before/after comparison image with exact Chinese text."""

from __future__ import annotations

import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "assets" / "nac-traework-before-after.png"
DATA = ROOT / "examples" / "cases" / "nac-traework" / "comparison.json"

WIDTH = 1800
HEIGHT = 1180
MARGIN = 72
GAP = 36
CARD_TOP = 250
CARD_BOTTOM = 1082
CARD_WIDTH = (WIDTH - MARGIN * 2 - GAP) // 2


def find_font(bold: bool = False) -> str:
    candidates = [
        Path("C:/Windows/Fonts/msyhbd.ttc" if bold else "C:/Windows/Fonts/msyh.ttc"),
        Path("/System/Library/Fonts/PingFang.ttc"),
        Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc" if bold else "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
    ]
    for path in candidates:
        if path.exists():
            return str(path)
    raise FileNotFoundError("No CJK-capable font found. Install Microsoft YaHei, PingFang, or Noto Sans CJK.")


REGULAR_FONT = find_font(False)
BOLD_FONT = find_font(True)


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(BOLD_FONT if bold else REGULAR_FONT, size=size)


def text_width(draw: ImageDraw.ImageDraw, value: str, text_font: ImageFont.FreeTypeFont) -> float:
    return draw.textlength(value, font=text_font)


def wrap(draw: ImageDraw.ImageDraw, value: str, text_font: ImageFont.FreeTypeFont, max_width: int) -> list[str]:
    lines: list[str] = []
    for paragraph in value.splitlines() or [""]:
        if not paragraph:
            lines.append("")
            continue
        current = ""
        for char in paragraph:
            candidate = current + char
            if current and text_width(draw, candidate, text_font) > max_width:
                lines.append(current)
                current = char
            else:
                current = candidate
        if current:
            lines.append(current)
    return lines


def draw_wrapped(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int],
    value: str,
    text_font: ImageFont.FreeTypeFont,
    fill: str,
    max_width: int,
    line_gap: int = 12,
) -> int:
    x, y = xy
    line_height = text_font.size + line_gap
    for line in wrap(draw, value, text_font, max_width):
        draw.text((x, y), line, font=text_font, fill=fill)
        y += line_height
    return y


def draw_pill(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int],
    label: str,
    background: str,
    foreground: str,
) -> None:
    x, y = xy
    pill_font = font(26, True)
    width = int(text_width(draw, label, pill_font)) + 44
    draw.rounded_rectangle((x, y, x + width, y + 52), radius=26, fill=background)
    draw.text((x + 22, y + 9), label, font=pill_font, fill=foreground)


def draw_bullet(
    draw: ImageDraw.ImageDraw,
    x: int,
    y: int,
    label: str,
    value: str,
    accent: str,
    max_width: int,
) -> int:
    draw.ellipse((x, y + 10, x + 13, y + 23), fill=accent)
    label_font = font(27, True)
    body_font = font(27)
    draw.text((x + 29, y), label, font=label_font, fill="#162033")
    label_width = int(text_width(draw, label, label_font))
    value_x = x + 29 + label_width + 10
    first_line_width = max_width - (value_x - x)
    value_lines = wrap(draw, value, body_font, max_width)
    if value_lines and text_width(draw, value_lines[0], body_font) <= first_line_width:
        draw.text((value_x, y), value_lines[0], font=body_font, fill="#344054")
        y += body_font.size + 13
        value_lines = value_lines[1:]
    else:
        y += label_font.size + 12
    for line in value_lines:
        draw.text((x + 29, y), line, font=body_font, fill="#344054")
        y += body_font.size + 13
    return y + 14


def draw_compact_bullet(
    draw: ImageDraw.ImageDraw,
    x: int,
    y: int,
    label: str,
    value: str,
    accent: str,
    max_width: int,
) -> int:
    draw.ellipse((x, y + 9, x + 13, y + 22), fill=accent)
    draw.text((x + 29, y), label, font=font(24, True), fill="#162033")
    y += 38
    lines = wrap(draw, value, font(23), max_width - 29)
    for line in lines[:2]:
        draw.text((x + 29, y), line, font=font(23), fill="#344054")
        y += 34
    return y + 10


def main() -> None:
    data = json.loads(DATA.read_text(encoding="utf-8"))
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)

    image = Image.new("RGB", (WIDTH, HEIGHT), "#F4F7FB")
    draw = ImageDraw.Draw(image)

    draw.text((MARGIN, 42), "同一个问题，使用 Skill 前后有什么不同？", font=font(50, True), fill="#101828")
    draw.text((MARGIN, 112), f"问题：{data['question']}", font=font(32), fill="#475467")
    draw.text(
        (MARGIN, 165),
        f"测试环境：{data['platform']} · {data['model']} · {data['tested_at']}",
        font=font(25, True),
        fill="#175CD3",
    )
    draw.rounded_rectangle((MARGIN, 218, WIDTH - MARGIN, 224), radius=3, fill="#D0D5DD")

    left_x = MARGIN
    right_x = MARGIN + CARD_WIDTH + GAP
    for x in (left_x, right_x):
        draw.rounded_rectangle((x, CARD_TOP, x + CARD_WIDTH, CARD_BOTTOM), radius=28, fill="#FFFFFF", outline="#D8DEE9", width=2)

    before = data["before"]
    after = data["after"]

    # Baseline card: the saved TraeWork answer without the skill.
    draw_pill(draw, (left_x + 38, CARD_TOP + 34), before["label"], "#F2F4F7", "#344054")
    y = CARD_TOP + 112
    draw.text((left_x + 38, y), "结论大体合理，但证据链不完整", font=font(32, True), fill="#101828")
    y += 62
    draw.rounded_rectangle((left_x + 38, y, left_x + CARD_WIDTH - 38, y + 150), radius=20, fill="#F8FAFC", outline="#E4E7EC")
    draw.text((left_x + 62, y + 20), "购买方向", font=font(25, True), fill="#475467")
    draw_wrapped(
        draw,
        (left_x + 62, y + 62),
        before["verdict"],
        font(27),
        "#344054",
        CARD_WIDTH - 124,
        10,
    )
    y += 182
    draw.text((left_x + 38, y), "做对了什么", font=font(27, True), fill="#166534")
    y = draw_wrapped(draw, (left_x + 38, y + 44), before["strength"], font(25), "#344054", CARD_WIDTH - 76, 10)
    y += 24
    draw.rounded_rectangle((left_x + 38, y, left_x + CARD_WIDTH - 38, CARD_BOTTOM - 34), radius=20, fill="#FFF7ED")
    draw.text((left_x + 62, y + 22), f"检索：{before['search']}", font=font(26, True), fill="#9A3412")
    draw.text((left_x + 62, y + 67), "仍无法核查", font=font(25, True), fill="#9A3412")
    draw_wrapped(draw, (left_x + 62, y + 108), before["limit"], font(24), "#7C2D12", CARD_WIDTH - 124, 9)

    # Skill card: intake, direct evidence, complete screening, and GRADE.
    draw_pill(draw, (right_x + 38, CARD_TOP + 34), after["label"], "#DCFCE7", "#166534")
    y = CARD_TOP + 112
    draw.text((right_x + 38, y), "先确认目标，再生成可核查结论", font=font(32, True), fill="#101828")
    y += 60
    draw.rounded_rectangle((right_x + 38, y, right_x + CARD_WIDTH - 38, y + 92), radius=20, fill="#ECFDF3")
    draw.text((right_x + 62, y + 17), "购买结论", font=font(25, True), fill="#067647")
    draw.text((right_x + 200, y + 10), after["verdict"], font=font(33, True), fill="#05603A")
    y += 116
    inner_width = CARD_WIDTH - 92
    y = draw_compact_bullet(draw, right_x + 46, y, "证据前先确认", after["intake"], "#12B76A", inner_width)
    y = draw_compact_bullet(draw, right_x + 46, y, "直接人体结果", after["direct_result"], "#12B76A", inner_width)
    y = draw_compact_bullet(draw, right_x + 46, y, "检索与筛查", after["search"], "#175CD3", inner_width)
    y = draw_compact_bullet(draw, right_x + 46, y, "逐结局 GRADE", after["grade"], "#175CD3", inner_width)
    draw_compact_bullet(draw, right_x + 46, y, "安全红线", after["safety"], "#F04438", inner_width)

    footer = "同一问题、同一平台与模型；比较工作流与可核查性，不比较回答长度。安装后先确认购买目标，再形成 PICOS、全量筛查与逐结局 GRADE。"
    draw_wrapped(draw, (MARGIN, 1110), footer, font(22), "#667085", WIDTH - MARGIN * 2, 8)

    image.save(OUTPUT, format="PNG", optimize=True)
    print(f"Wrote {OUTPUT} ({image.width}x{image.height})")


if __name__ == "__main__":
    main()
