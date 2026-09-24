"""Build the README before/after comparison image with exact Chinese text."""

from __future__ import annotations

import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "assets" / "glucosamine-chondroitin-before-after.png"
DATA = ROOT / "examples" / "cases" / "glucosamine-chondroitin" / "answer.json"

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


def main() -> None:
    data = json.loads(DATA.read_text(encoding="utf-8"))
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)

    image = Image.new("RGB", (WIDTH, HEIGHT), "#F4F7FB")
    draw = ImageDraw.Draw(image)

    draw.text((MARGIN, 58), "同一个问题，使用 Skill 前后有什么不同？", font=font(50, True), fill="#101828")
    draw.text((MARGIN, 132), "问题：补充氨糖软骨素能缓解关节疼痛吗？", font=font(34), fill="#475467")
    draw.rounded_rectangle((MARGIN, 194, WIDTH - MARGIN, 200), radius=3, fill="#D0D5DD")

    left_x = MARGIN
    right_x = MARGIN + CARD_WIDTH + GAP
    for x in (left_x, right_x):
        draw.rounded_rectangle((x, CARD_TOP, x + CARD_WIDTH, CARD_BOTTOM), radius=28, fill="#FFFFFF", outline="#D8DEE9", width=2)

    # Baseline card: a representative ordinary-answer structure, not a benchmark run.
    draw_pill(draw, (left_x + 38, CARD_TOP + 34), "未调用 Skill · 常见回答形态", "#F2F4F7", "#344054")
    y = CARD_TOP + 112
    draw.text((left_x + 38, y), "方向正确，但信息停在概括层", font=font(32, True), fill="#101828")
    y += 62
    baseline = (
        "氨糖和软骨素可能对部分骨关节炎患者的关节疼痛有一定帮助，但研究结果并不一致，效果通常比较有限，"
        "也不是每个人都会有效。\n\n"
        "如果想尝试，可以选择成分和剂量清楚的产品，连续服用一段时间观察；如果没有改善就停止。"
        "正在服用抗凝药、有慢性病或疼痛严重的人，最好先咨询医生。运动、控制体重和规范治疗通常更重要。"
    )
    y = draw_wrapped(draw, (left_x + 38, y), baseline, font(28), "#344054", CARD_WIDTH - 76, 14)
    y += 30
    draw.rounded_rectangle((left_x + 38, y, left_x + CARD_WIDTH - 38, y + 174), radius=20, fill="#FFF7ED")
    draw.text((left_x + 62, y + 22), "尚未展开", font=font(27, True), fill="#9A3412")
    draw_wrapped(
        draw,
        (left_x + 62, y + 67),
        "证据究竟针对哪类关节痛 · 效果是否达到临床重要阈值\n检索式与全量筛查 · 逐结局 GRADE · 可核查来源",
        font(26),
        "#7C2D12",
        CARD_WIDTH - 124,
        12,
    )

    # Skill card: first-screen decision plus traceability.
    draw_pill(draw, (right_x + 38, CARD_TOP + 34), "调用 evidence-based-nutrition-advisor", "#DCFCE7", "#166534")
    y = CARD_TOP + 112
    draw.text((right_x + 38, y), "先交付决定，再展开证据", font=font(32, True), fill="#101828")
    y += 60
    draw.rounded_rectangle((right_x + 38, y, right_x + CARD_WIDTH - 38, y + 92), radius=20, fill="#ECFDF3")
    draw.text((right_x + 62, y + 17), "购买结论", font=font(25, True), fill="#067647")
    draw.text((right_x + 200, y + 10), "只对特定人群值得", font=font(35, True), fill="#05603A")
    y += 126
    inner_width = CARD_WIDTH - 92
    y = draw_bullet(draw, right_x + 46, y, "对谁可能有用", data["for_whom"], "#12B76A", inner_width)
    y = draw_bullet(draw, right_x + 46, y, "效果上限", data["effect_ceiling"], "#12B76A", inner_width)
    y = draw_bullet(draw, right_x + 46, y, "安全红线", data["safety_red_line"], "#F04438", inner_width)
    draw.rounded_rectangle((right_x + 38, CARD_BOTTOM - 176, right_x + CARD_WIDTH - 38, CARD_BOTTOM - 34), radius=20, fill="#F0F9FF")
    draw.text((right_x + 62, CARD_BOTTOM - 158), "为什么", font=font(25, True), fill="#026AA2")
    draw_wrapped(
        draw,
        (right_x + 170, CARD_BOTTOM - 158),
        data["why"]["summary"],
        font(24),
        "#075985",
        CARD_WIDTH - 246,
        8,
    )
    draw.text((right_x + 62, CARD_BOTTOM - 88), "可继续展开", font=font(23, True), fill="#026AA2")
    draw_wrapped(
        draw,
        (right_x + 210, CARD_BOTTOM - 88),
        "PubMed检索 · 全量筛查 · PICOS · 逐结局GRADE",
        font(23),
        "#075985",
        CARD_WIDTH - 272,
        10,
    )

    footer = "同一问题的交付结构对比，不是模型能力基准。左侧是常见短答形态；右侧来自已保存检索式、全量筛选、PICOS 与逐结局 GRADE 的仓库案例。"
    draw_wrapped(draw, (MARGIN, 1110), footer, font(23), "#667085", WIDTH - MARGIN * 2, 8)

    image.save(OUTPUT, format="PNG", optimize=True)
    print(f"Wrote {OUTPUT} ({image.width}x{image.height})")


if __name__ == "__main__":
    main()
