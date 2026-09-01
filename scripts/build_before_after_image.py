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


def draw_label(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int],
    label: str,
    background: str,
    foreground: str,
) -> None:
    x, y = xy
    label_font = font(24, True)
    width = int(text_width(draw, label, label_font)) + 34
    draw.rectangle((x, y, x + width, y + 46), fill=background)
    draw.text((x + 17, y + 7), label, font=label_font, fill=foreground)


def draw_bullet(
    draw: ImageDraw.ImageDraw,
    x: int,
    y: int,
    label: str,
    value: str,
    accent: str,
    max_width: int,
    font_size: int = 27,
) -> int:
    draw.ellipse((x, y + 10, x + 13, y + 23), fill=accent)
    label_font = font(font_size, True)
    body_font = font(font_size)
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

    image = Image.new("RGB", (WIDTH, HEIGHT), "#F4F1E9")
    draw = ImageDraw.Draw(image)

    draw.text((MARGIN, 42), "EVIDENCE DELIVERY · BEFORE / AFTER", font=font(20, True), fill="#65716C")
    draw.text((MARGIN, 82), "同一个问题，两种交付结构", font=font(50, True), fill="#1A2823")
    draw.text((MARGIN, 154), "补充氨糖软骨素能缓解关节疼痛吗？", font=font(32), fill="#45524D")
    draw.line((MARGIN, 208, WIDTH - MARGIN, 208), fill="#1A2823", width=3)
    draw.line((MARGIN, 216, WIDTH - MARGIN, 216), fill="#C9D0C8", width=1)

    left_x = MARGIN
    right_x = MARGIN + CARD_WIDTH + GAP
    draw.rectangle((left_x, CARD_TOP, left_x + CARD_WIDTH, CARD_BOTTOM), fill="#EAE7DF")
    draw.rectangle((right_x, CARD_TOP, right_x + CARD_WIDTH, CARD_BOTTOM), fill="#FBFAF5")
    divider_x = left_x + CARD_WIDTH + GAP // 2
    draw.line((divider_x, CARD_TOP, divider_x, CARD_BOTTOM), fill="#AEB8B0", width=2)

    # Baseline card: a representative ordinary-answer structure, not a benchmark run.
    draw_label(draw, (left_x + 38, CARD_TOP + 34), "常见短答", "#D8DCD6", "#34433D")
    y = CARD_TOP + 112
    draw.text((left_x + 38, y), "方向正确，但信息停在概括层", font=font(32, True), fill="#101828")
    y += 62
    baseline = (
        "氨糖和软骨素可能对部分骨关节炎患者的关节疼痛有一定帮助，但研究结果并不一致，效果通常比较有限，"
        "个体感受也会有差异。\n\n"
        "如果想尝试，可以选择成分和剂量清楚的产品，连续服用一段时间观察；如果没有改善就停止。"
        "正在服用抗凝药、有慢性病或疼痛严重的人，最好先咨询医生。运动、控制体重和规范治疗通常更重要。"
    )
    y = draw_wrapped(draw, (left_x + 38, y), baseline, font(28), "#344054", CARD_WIDTH - 76, 14)
    y += 30
    draw.rectangle((left_x + 38, y, left_x + CARD_WIDTH - 38, y + 174), fill="#F5E9DA")
    draw.text((left_x + 62, y + 22), "尚未展开", font=font(27, True), fill="#9A3412")
    draw_wrapped(
        draw,
        (left_x + 62, y + 67),
        "证据针对哪类关节痛 · 效果是否值得在意\n核验了哪些来源 · 哪些信息会改变建议 · 如何继续审计",
        font(26),
        "#7C2D12",
        CARD_WIDTH - 124,
        12,
    )

    # Skill card: the current ordinary-user quick path.
    draw_label(draw, (right_x + 38, CARD_TOP + 34), "普通用户默认路径", "#E4F0EB", "#0B6657")
    y = CARD_TOP + 112
    draw.text((right_x + 38, y), "先交付决定，再展开证据", font=font(32, True), fill="#101828")
    y += 54
    draw.rectangle((right_x + 38, y, right_x + CARD_WIDTH - 38, y + 62), fill="#E7F0EC")
    draw.text((right_x + 62, y + 14), "L1-Quick · 快速核验完成，未正式评级", font=font(24, True), fill="#0B6657")
    y += 82
    draw.rectangle((right_x + 38, y, right_x + CARD_WIDTH - 38, y + 92), fill="#EDF3EC")
    draw.text((right_x + 62, y + 17), "购买结论", font=font(25, True), fill="#067647")
    draw.text((right_x + 200, y + 10), "只对特定人群值得", font=font(35, True), fill="#05603A")
    y += 126
    inner_width = CARD_WIDTH - 92
    y = draw_bullet(draw, right_x + 46, y, "对谁可能有用", data["for_whom"], "#12B76A", inner_width, 25)
    y = draw_bullet(draw, right_x + 46, y, "效果上限", data["effect_ceiling"], "#12B76A", inner_width, 25)
    y = draw_bullet(draw, right_x + 46, y, "安全红线", data["safety_red_line"], "#F04438", inner_width, 25)
    draw.rectangle((right_x + 38, CARD_BOTTOM - 180, right_x + CARD_WIDTH - 38, CARD_BOTTOM - 96), fill="#E7F0EC")
    draw.text((right_x + 62, CARD_BOTTOM - 162), "证据护照", font=font(24, True), fill="#0B6657")
    draw_wrapped(
        draw,
        (right_x + 208, CARD_BOTTOM - 162),
        "本地标准 · 可靠指南/综述 · 权威安全资料",
        font(22),
        "#31554D",
        CARD_WIDTH - 270,
        8,
    )
    draw.rectangle((right_x + 38, CARD_BOTTOM - 78, right_x + CARD_WIDTH - 38, CARD_BOTTOM - 28), outline="#0B6657", width=3)
    button_label = "申请完整审计"
    button_font = font(25, True)
    button_width = text_width(draw, button_label, button_font)
    draw.text((right_x + (CARD_WIDTH - button_width) / 2, CARD_BOTTOM - 69), button_label, font=button_font, fill="#0B6657")

    footer = "这张图比较交付结构，不衡量模型能力。普通问题默认停在快速核验；用户申请或风险需要更高保证时，才进入全量筛查与逐结局 GRADE。"
    draw_wrapped(draw, (MARGIN, 1110), footer, font(23), "#65716C", WIDTH - MARGIN * 2, 8)

    image.save(OUTPUT, format="PNG", optimize=True)
    print(f"Wrote {OUTPUT} ({image.width}x{image.height})")


if __name__ == "__main__":
    main()
