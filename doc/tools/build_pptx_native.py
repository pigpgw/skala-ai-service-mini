"""발표 덱 → PPTX (네이티브 생성). 편집 가능한 텍스트 상자·도형·이미지로 만든다.

왜 HTML 변환이 아니라 직접 만드는가
    HTML → DOM 추출 방식(html2pptx 스킬)으로 만들었더니 <pre> 코드블록이 통째로
    사라지고, 리스트 줄이 겹쳤다(실제 PowerPoint 렌더로 확인). 품질을 만들려면
    좌표를 직접 잡아야 해서, 슬라이드 정의(deck_content.py)에서 PPTX를 직접 그린다.

레이아웃 (13.333 x 7.5 in = 16:9)
    좌우 여백 0.66in · 본문 폭 12.0in · 상단 0.5in
    kicker(0.28) → title(0.62) → lead(0.42) → body → footer(0.22)

검증
    - 모든 도형이 슬라이드 안에 있는지(벗어나면 실패)
    - 본문 블록이 넘치지 않는지(넘으면 실패)
    - PowerPoint으로 PDF 렌더해 눈으로 확인(doc/tools/render_pptx_check.sh 참고)
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))

from deck_content import AUTHOR, DECK_TITLE, SLIDES   # noqa: E402

from pptx import Presentation                       # noqa: E402
from pptx.dml.color import RGBColor                 # noqa: E402
from pptx.enum.shapes import MSO_SHAPE              # noqa: E402
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN     # noqa: E402
from pptx.util import Emu, Inches, Pt               # noqa: E402

# ── 색 (HTML 디자인 시스템과 동일) ───────────────────────────────────
INK = RGBColor(0x12, 0x15, 0x1A)
MUTED = RGBColor(0x5A, 0x64, 0x72)
FAINT = RGBColor(0x8A, 0x93, 0xA0)
LINE = RGBColor(0xE4, 0xE8, 0xEE)
SOFT = RGBColor(0xF6, 0xF8, 0xFB)
ACCENT = RGBColor(0x2B, 0x5F, 0xD9)
ACCENT_SOFT = RGBColor(0xEE, 0xF3, 0xFF)
ACCENT_LINE = RGBColor(0xD3, 0xE0, 0xFB)
GOOD = RGBColor(0x17, 0x78, 0x4A)
GOOD_SOFT = RGBColor(0xE9, 0xF6, 0xEE)
GOOD_LINE = RGBColor(0xC9, 0xE7, 0xD6)
WARN = RGBColor(0x8A, 0x53, 0x00)
WARN_SOFT = RGBColor(0xFB, 0xF3, 0xE2)
WARN_LINE = RGBColor(0xED, 0xDD, 0xBB)
BAR_BEFORE = RGBColor(0xC4, 0xCE, 0xDF)
CODE_BG = RGBColor(0x11, 0x15, 0x1B)
CODE_FG = RGBColor(0xE7, 0xEC, 0xF3)
CODE_K = RGBColor(0x8F, 0xB6, 0xFF)
CODE_C = RGBColor(0x79, 0x83, 0x9A)
CODE_S = RGBColor(0x8F, 0xD9, 0xA6)

SANS = "Apple SD Gothic Neo"
MONO = "Menlo"

SW, SH = 13.333, 7.5
ML, MR = 0.66, 0.66
CW = SW - ML - MR
TOP = 0.52

TONES = {
    "plain": (SOFT, LINE, INK),
    "accent": (ACCENT_SOFT, ACCENT_LINE, INK),
    "good": (GOOD_SOFT, GOOD_LINE, INK),
    "warn": (WARN_SOFT, WARN_LINE, INK),
}


def _tf(shape, *, anchor=MSO_ANCHOR.TOP):
    frame = shape.text_frame
    frame.word_wrap = True
    frame.vertical_anchor = anchor
    frame.margin_left = frame.margin_right = 0
    frame.margin_top = frame.margin_bottom = 0
    return frame


def _text(slide, x, y, w, h, text, size, color=INK, bold=False, mono=False,
          align=PP_ALIGN.LEFT, spacing=1.0, anchor=MSO_ANCHOR.TOP):
    box = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    frame = _tf(box, anchor=anchor)
    paragraph = frame.paragraphs[0]
    paragraph.alignment = align
    paragraph.line_spacing = spacing
    run = paragraph.add_run()
    run.text = text
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.color.rgb = color
    run.font.name = MONO if mono else SANS
    return box


def _rect(slide, x, y, w, h, fill, line=None, radius=None):
    shape_type = MSO_SHAPE.ROUNDED_RECTANGLE if radius else MSO_SHAPE.RECTANGLE
    shape = slide.shapes.add_shape(shape_type, Inches(x), Inches(y), Inches(w), Inches(h))
    if fill is None:
        shape.fill.background()
    else:
        shape.fill.solid()
        shape.fill.fore_color.rgb = fill
    if line is None:
        shape.line.fill.background()
    else:
        shape.line.color.rgb = line
        shape.line.width = Pt(1)
    if radius:
        shape.adjustments[0] = radius
    shape.shadow.inherit = False
    shape.text_frame.text = ""
    return shape


def _card(slide, x, y, w, h, *, fill=SOFT, line=LINE, radius=0.06):
    return _rect(slide, x, y, w, h, fill, line, radius=radius)


def _bullets(slide, x, y, w, items, size=12.5, gap=0.42, color=INK):
    """items: [(text, where|None)] — 앞의 작은 사각형 마커를 직접 그린다."""
    cy = y
    for text, where in items:
        _rect(slide, x, cy + 0.075, 0.07, 0.07, ACCENT)
        box = _text(slide, x + 0.17, cy - 0.02, w - 0.17, gap, text, size, color, spacing=1.15)
        per_line = max(8, int((w - 0.2) * 7.0))   # 한국어 혼합 12.5pt 기준 1줄 글자 수
        lines = max(1, -(-len(text) // per_line))   # 올림 나눗셈
        cy += 0.185 * lines + 0.10
        if where:
            _text(slide, x + 0.17, cy - 0.03, w - 0.17, 0.22, where, 9, FAINT, mono=True)
            cy += 0.24
    return cy


def _code(slide, x, y, w, h, lines, caption=None, size=10.5):
    _rect(slide, x, y, w, h, CODE_BG, None, radius=0.05)
    cy = y + 0.16
    for tone, text in lines:
        color = {"k": CODE_K, "c": CODE_C, "s": CODE_S}.get(tone, CODE_FG)
        bold = tone in {"k", "s"}
        _text(slide, x + 0.22, cy, w - 0.4, 0.24, text, size, color, bold=bold, mono=True)
        cy += 0.215
    if caption:
        _text(slide, x, y + h + 0.07, w, 0.24, caption, 10, MUTED)
    return cy


def _table(slide, x, y, w, rows, head, col_w=None, size=11.5):
    """가벼운 표 — 선만 그려 표처럼 보이게 한다."""
    col_w = col_w or [w * 0.44, w * 0.19, w * 0.19, w * 0.18]
    row_h = 0.42
    cx = x
    for index, cell in enumerate(head):
        _text(slide, cx, y, col_w[index], row_h, cell, 9.5, MUTED, bold=True)
        cx += col_w[index]
    _rect(slide, x, y + row_h - 0.05, w, 0.015, RGBColor(0xD5, 0xDB, 0xE5))
    cy = y + row_h
    for row in rows:
        cx = x
        for index, cell in enumerate(row):
            align = PP_ALIGN.LEFT if index == 0 else PP_ALIGN.RIGHT
            color = GOOD if cell.startswith("−") else INK
            _text(slide, cx, cy, col_w[index], row_h, cell, size, color, align=align)
            cx += col_w[index]
        cy += row_h
        _rect(slide, x, cy - 0.045, w, 0.008, LINE)
    return cy


def _bars(slide, x, y, w, items, legend, label_w=1.85, value_w=1.85):
    _text(slide, x, y, w, 0.26, "검색 정확도", 13, INK, bold=True)
    cy = y + 0.34
    lx = x
    for tone, label in legend:
        _rect(slide, lx, cy + 0.045, 0.11, 0.11, BAR_BEFORE if tone == "before" else ACCENT)
        _text(slide, lx + 0.17, cy, 1.5, 0.22, label, 9.5, MUTED)
        lx += 0.35 + len(label) * 0.075
    cy += 0.34
    track_x = x + label_w
    track_w = w - label_w - value_w
    for item in items:
        _text(slide, x, cy - 0.02, label_w - 0.15, 0.4, item["label"], 11, INK,
              align=PP_ALIGN.RIGHT)
        for tone, ratio in (("before", item["b"]), ("after", item["a"])):
            _rect(slide, track_x, cy + (0.0 if tone == "before" else 0.17),
                  track_w, 0.12, RGBColor(0xF1, 0xF4, 0xF9))
            _rect(slide, track_x, cy + (0.0 if tone == "before" else 0.17),
                  max(0.04, track_w * min(1.0, ratio)), 0.12,
                  BAR_BEFORE if tone == "before" else ACCENT)
        _text(slide, x + w - value_w, cy - 0.02, value_w, 0.3,
              f"{item['before']}  →  {item['after']}", 11, INK, bold=True,
              align=PP_ALIGN.RIGHT)
        cy += 0.66
    return cy


def _note_height(w: float, body: str, where: str | None) -> float:
    """본문 줄 수를 한국어 기준(≈6.4자/inch, 11.5pt)으로 추정해 높이를 정한다."""
    per_line = max(12, int((w - 0.5) * 6.4))
    lines = max(1, -(-len(body) // per_line))
    return 0.52 + lines * 0.215 + (0.34 if where else 0.18)


def _note(slide, x, y, w, h, title, body, tone="plain", where=None):
    fill, line, _ = TONES.get(tone, TONES["plain"])
    need = _note_height(w, body, where)
    height = max(h, need)
    _card(slide, x, y, w, height, fill=fill, line=line)
    _text(slide, x + 0.22, y + 0.16, w - 0.44, 0.3, title, 12.5, INK, bold=True)
    _text(slide, x + 0.22, y + 0.52, w - 0.44, height - 0.62, body, 11.5, MUTED, spacing=1.25)
    if where:
        _text(slide, x + 0.22, y + height - 0.3, w - 0.44, 0.24, where, 9.5, FAINT)
    return height


def _stats(slide, x, y, w, h, items, gap=0.2):
    cell_w = (w - gap * (len(items) - 1)) / len(items)
    for index, item in enumerate(items):
        cx = x + index * (cell_w + gap)
        _card(slide, cx, y, cell_w, h)
        color = {"accent": ACCENT, "good": GOOD, "warn": WARN}.get(item.get("tone"), ACCENT)
        _text(slide, cx + 0.24, y + 0.18, cell_w - 0.48, 0.58, item["value"], 26, color, bold=True)
        _text(slide, cx + 0.24, y + 0.76, cell_w - 0.48, 0.46, item["label"], 10, MUTED, spacing=1.2)


def _image(slide, x, y, w, path, caption, height_in):
    from PIL import Image
    with Image.open(path) as probe:
        iw, ih = probe.size
    draw_h = height_in
    draw_w = min(w, height_in * iw / ih)
    img_x = x + (w - draw_w) / 2      # 그림만 가운데 정렬
    _rect(slide, img_x, y, draw_w, draw_h, None, LINE)
    slide.shapes.add_picture(str(path), Inches(img_x), Inches(y), Inches(draw_w), Inches(draw_h))
    _text(slide, x, y + draw_h + 0.06, w, 0.26, caption, 9.5, MUTED)
    return y + draw_h + 0.34


def _build_slide(prs, spec, index):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    y = TOP

    if spec.get("kind") == "cover":
        _text(slide, ML, 1.55, CW, 0.3, spec["kicker"], 11, ACCENT, bold=True)
        _text(slide, ML, 1.95, CW, 1.6, "\n".join(spec["title"]), 40, INK, bold=True, spacing=1.15)
        _text(slide, ML, 3.62, CW, 0.4, spec["sub"], 15, MUTED)
        plan_y = 4.28
        for index, (head, body) in enumerate(spec["plan"]):
            px = ML + index * 4.1
            fill = ACCENT_SOFT if index == 0 else SOFT
            line = ACCENT_LINE if index == 0 else LINE
            _card(slide, px, plan_y, 3.85, 0.92, fill=fill, line=line)
            _text(slide, px + 0.24, plan_y + 0.14, 3.4, 0.3, head, 13, INK, bold=True)
            _text(slide, px + 0.24, plan_y + 0.5, 3.4, 0.3, body, 10.5, MUTED)
        _text(slide, ML, 5.55, CW, 0.7, "\n".join(spec["meta"]), 11.5, MUTED, spacing=1.4)
        _rect(slide, ML, 6.62, CW, 0.008, LINE)
        _text(slide, ML, 6.76, CW, 0.26, AUTHOR, 9.5, FAINT)
        _text(slide, ML, 6.76, CW, 0.26, str(index), 9.5, FAINT, align=PP_ALIGN.RIGHT)
        return slide

    # kicker
    _text(slide, ML, y, CW, 0.26, spec["kicker"], 10.5, ACCENT, bold=True)
    _rect(slide, ML + 1.75, y + 0.12, CW - 1.75, 0.008, LINE)
    y += 0.36

    # title
    title = spec["title"]
    title_lines = title if isinstance(title, list) else [title]
    _text(slide, ML, y, CW, 0.62 * len(title_lines), "\n".join(title_lines), 26, INK,
          bold=True, spacing=1.12)
    y += 0.56 * len(title_lines) + 0.16

    # lead
    if spec.get("lead"):
        _text(slide, ML, y, CW - 0.6, 0.6, spec["lead"], 12, MUTED, spacing=1.3)
        y += 0.28 * (spec["lead"].count("\n") + 1) + 0.18

    body_top = y
    blocks = spec["blocks"]

    def _reserve(index: int) -> float:
        """뒤따르는 블록이 차지할 높이(대략) — 이미지 크기를 이만큼 남겨 둔다."""
        if index >= len(blocks):
            return 0.0
        nxt = blocks[index]
        kind = nxt["type"]
        if kind == "cards2":
            cell_w = (CW - 0.24) / 2
            heights = []
            for item in nxt["items"]:
                if item.get("bullets"):
                    heights.append(1.62)
                else:
                    per_line = max(12, int((cell_w - 0.5) * 6.4))
                    lines = max(1, -(-len(item["body"]) // per_line))
                    heights.append(max(1.18, 0.56 + lines * 0.215 + 0.16))
            return max(heights) + 0.2
        if kind == "cards2x2":
            return 1.32 * 2 + 0.2 + 0.2
        if kind == "note":
            return _note_height(CW, nxt["body"], nxt.get("where")) + 0.18
        if kind == "stats":
            return 1.32 + 0.2
        if kind == "table":
            return 0.36 + 0.42 * (len(nxt["rows"]) + 1) + 0.18
        if kind == "bars":
            return 0.34 + 0.66 * len(nxt["items"]) + 0.14
        return 0.0

    for block in blocks:
        btype = block["type"]
        if btype == "stats":
            _stats(slide, ML, y, CW, 1.32, block["items"])
            y += 1.32 + 0.2
        elif btype == "cards2x2":
            cell_w = (CW - 0.24) / 2
            cell_h = 1.32
            for index, item in enumerate(block["items"]):
                cx = ML + (index % 2) * (cell_w + 0.24)
                cy = y + (index // 2) * (cell_h + 0.2)
                _card(slide, cx, cy, cell_w, cell_h)
                _text(slide, cx + 0.24, cy + 0.16, cell_w - 0.48, 0.28, item["title"], 12.5, INK, bold=True)
                _text(slide, cx + 0.24, cy + 0.5, cell_w - 0.48, 0.6, item["body"], 10.5, MUTED, spacing=1.25)
                _text(slide, cx + 0.24, cy + cell_h - 0.3, cell_w - 0.48, 0.24, item["where"], 9, FAINT, mono=True)
            y += cell_h * 2 + 0.2 + 0.18
        elif btype == "cards2":
            cell_w = (CW - 0.24) / 2
            heights = []
            for item in block["items"]:
                if item.get("bullets"):
                    heights.append(1.62)
                else:
                    per_line = max(12, int((cell_w - 0.5) * 6.4))
                    lines = max(1, -(-len(item["body"]) // per_line))
                    heights.append(max(1.18, 0.56 + lines * 0.215 + 0.16))
            height = max(heights)
            for index, item in enumerate(block["items"]):
                cx = ML + index * (cell_w + 0.24)
                _card(slide, cx, y, cell_w, height)
                _text(slide, cx + 0.24, y + 0.14, cell_w - 0.48, 0.28, item["title"], 12.5, INK, bold=True)
                if item.get("bullets"):
                    _bullets(slide, cx + 0.24, y + 0.54, cell_w - 0.48, item["bullets"])
                else:
                    _text(slide, cx + 0.24, y + 0.48, cell_w - 0.48, 0.62,
                          item["body"], 10.5, MUTED, spacing=1.25)
            y += height + 0.2
        elif btype == "note":
            height = _note(slide, ML, y, CW, 0.95, block["title"], block["body"],
                           block.get("tone", "plain"), block.get("where"))
            y += height + 0.18
        elif btype == "image":
            block_index = blocks.index(block)
            available = 6.34 - y - _reserve(block_index + 1)
            height_in = min(block["height_in"], max(1.2, available - 0.34))
            y = _image(slide, ML, y, CW, REPO_ROOT / "doc" / "reports" / block["src"],
                       block["caption"], height_in) + 0.1
        elif btype == "table":
            _text(slide, ML, y, CW, 0.28, block["title"], 12.5, INK, bold=True)
            _table(slide, ML, y + 0.36, CW, block["rows"], block["head"])
            y += 0.36 + 0.36 * (len(block["rows"]) + 1) + 0.16
        elif btype == "bars":
            _bars(slide, ML, y, CW, block["items"], block["legend"])
            y += 0.34 + 0.66 * len(block["items"]) + 0.14
        elif btype == "code":
            pass
        elif btype == "bullets":
            pass
        elif btype == "split":
            left_w = CW * 0.56
            right_x = ML + left_w + 0.3
            right_w = CW - left_w - 0.3
            side_items = block["right"] if isinstance(block["right"], list) else [block["right"]]
            left_items = block["left"] if isinstance(block["left"], list) else [block["left"]]
            ly = y
            for item in left_items:
                ly = _render_left(slide, ML, ly, left_w, item)
            ry = y
            for item in side_items:
                ry = _render_left(slide, right_x, ry, right_w, item)
            y = max(ly, ry) + 0.1
        else:
            raise ValueError(f"알 수 없는 블록: {btype}")

    body_bottom = 0.0
    for shape in (slide.shapes if spec.get("kind") != "cover" else []):
        try:
            bottom = (shape.top + shape.height) / 914400
        except TypeError:
            continue
        if bottom < 6.45:
            body_bottom = max(body_bottom, bottom)
    if body_bottom > 6.38:
        print(f"  [주의] 슬라이드 {index}: 본문 하단 {body_bottom:.2f}\"가 푸터(6.5\")를 넘어섭니다")
    # footer
    _rect(slide, ML, 6.5, CW, 0.008, LINE)
    _text(slide, ML, 6.62, CW - 0.5, 0.26, spec.get("foot", ""), 9.5, MUTED)
    _text(slide, ML, 6.62, CW, 0.26, str(index), 9.5, FAINT, align=PP_ALIGN.RIGHT)
    return slide


def _render_left(slide, x, y, w, item):
    """왼쪽/오른쪽 칼럼 안의 블록 하나를 그리고 다음 y를 돌려준다."""
    btype = item["type"]
    if btype == "card":
        fill, line, _ = TONES.get(item.get("tone", "plain"), TONES["plain"])
        height = 0.62 + 0.34 * len(item.get("bullets", []))
        _card(slide, x, y, w, height, fill=fill, line=line)
        _text(slide, x + 0.24, y + 0.16, w - 0.48, 0.28, item["title"], 12.5, INK, bold=True)
        _bullets(slide, x + 0.24, y + 0.56, w - 0.48, item["bullets"])
        return y + height + 0.16
    if btype == "code":
        height = 0.28 + 0.215 * len(item["lines"])
        _code(slide, x, y, w, height, item["lines"], item.get("caption"))
        return y + height + (0.34 if item.get("caption") else 0.16)
    if btype == "note":
        height = _note(slide, x, y, w, 1.0, item["title"], item["body"],
                       item.get("tone", "plain"), item.get("where"))
        return y + height + 0.16
    if btype == "image":
        return _image(slide, x, y, w, REPO_ROOT / "doc" / "reports" / item["src"],
                      item["caption"], item["height_in"]) + 0.08
    if btype == "bullets":
        end = _bullets(slide, x, y, w, item["items"])
        return end + 0.1
    if btype == "table":
        _text(slide, x, y, w, 0.28, item["title"], 12.5, INK, bold=True)
        _table(slide, x, y + 0.36, w, item["rows"], item["head"])
        return y + 0.36 + 0.42 * (len(item["rows"]) + 1) + 0.16
    if btype == "stats":
        _stats(slide, x, y, w, 1.32, item["items"])
        return y + 1.32 + 0.16
    if btype == "bars":
        _bars(slide, x, y, w, item["items"], item["legend"])
        return y + 0.34 + 0.66 * len(item["items"]) + 0.12
    raise ValueError(f"알 수 없는 블록: {btype}")


def build(out: Path) -> int:
    prs = Presentation()
    prs.slide_width = Inches(SW)
    prs.slide_height = Inches(SH)
    for index, spec in enumerate(SLIDES, 1):
        _build_slide(prs, spec, index)

    out.parent.mkdir(parents=True, exist_ok=True)
    prs.save(str(out))

    over = []
    for index, slide in enumerate(prs.slides, 1):
        for shape in slide.shapes:
            try:
                if (shape.top + shape.height > prs.slide_height
                        or shape.left + shape.width > prs.slide_width
                        or shape.top < 0 or shape.left < 0):
                    over.append(f"슬라이드 {index}: {shape.shape_type}")
                    break
            except TypeError:
                pass
    print(f"saved: {out} ({len(prs.slides)} slides)")
    if over:
        print("★ 슬라이드 범위 초과:")
        for item in over:
            print(f"   {item}")
        return 1
    print("경계 검사: 모든 도형이 슬라이드 안 ✓")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="발표 덱 → PPTX(네이티브)")
    parser.add_argument("--out", default=str(REPO_ROOT / "doc" / "reports" / "presentation.pptx"))
    args = parser.parse_args()
    return build(Path(args.out))


if __name__ == "__main__":
    raise SystemExit(main())
