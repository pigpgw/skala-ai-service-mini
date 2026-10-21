"""발표 HTML → PPTX 변환기 (레이아웃 경계 보장).

왜 이 파일이 복잡한가
    PPTX는 좌표를 직접 지정해야 한다. 좌표를 고정한 채로 이미지를 붙이면
    슬라이드 밖으로 나가 PPT가 깨진다(실제로 3·5번 슬라이드가 넘쳤다).
    그래서 **남은 공간을 계산하고 그 안에서만** 그림을 배치한다.

레이아웃 규칙 (EMU, 1in = 914400)
    슬라이드 13.33in x 7.5in = 12192000 x 6858000
    좌우 여백 600000 · 제목 380000~1280000 · 본문 시작 1400000 · 하단 한계 6480000

검사
    생성 직후 모든 도형의 우·하단 좌표를 확인해 슬라이드를 넘으면 실패로 알린다
    (조용히 잘라내지 않는다 — 잘린 PPT는 "내용이 사라진 PPT"가 되므로).

사용
    .venv/bin/python doc/tools/build_pptx.py --source doc/reports/presentation.html \
        --out doc/reports/presentation.pptx
"""
from __future__ import annotations

import argparse
import html
import math
import re
from html.parser import HTMLParser
from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.util import Emu, Pt

INK = RGBColor(0x16, 0x19, 0x1D)
MUTED = RGBColor(0x5B, 0x64, 0x70)
ACCENT = RGBColor(0x2F, 0x5F, 0xD0)
GOOD = RGBColor(0x1F, 0x7A, 0x4D)
FONT = "Apple SD Gothic Neo"

# ── 레이아웃 상수 (EMU) ──────────────────────────────────────────────
SLIDE_W, SLIDE_H = 12_192_000, 6_858_000
MARGIN_X = 600_000
TITLE_Y, TITLE_H = 380_000, 900_000
CONTENT_TOP = 1_400_000
BOTTOM_LIMIT = 6_480_000          # 하단 안전 여백 포함
CONTENT_W = SLIDE_W - 2 * MARGIN_X
LINE_H = 330_000                  # 16pt 한 줄 높이
GAP = 140_000
ROW_H = 420_000                  # 표 한 행 높이
CAPTION_H = 300_000


class SlideParser(HTMLParser):
    """발표용 HTML에서 슬라이드별 (제목, 불릿, 표, 이미지, 캡션)를 뽑는다."""

    def __init__(self) -> None:
        super().__init__()
        self.slides: list[dict] = []
        self._current: dict | None = None
        self._stack: list[str] = []
        self._buffer: list[str] = []
        self._in_table = False
        self._table_rows: list[list[str]] = []
        self._row: list[str] = []
        self._in_caption = False

    def _text(self) -> str:
        return html.unescape(re.sub(r"\s+", " ", "".join(self._buffer)).strip())

    def _flush(self) -> None:
        if self._current is not None and self._buffer:
            self._current.setdefault("lead", "")
            self._current["lead"] = (self._current["lead"] + " " + self._text()).strip()
        self._buffer = []

    def handle_starttag(self, tag: str, attrs: list) -> None:
        self._stack.append(tag)
        classes = dict(attrs).get("class", "")
        if tag == "br" and self._current is not None:
            self._buffer.append(" · ")
        if tag == "img" and self._current is not None:
            src = dict(attrs).get("src")
            if src:
                self._current.setdefault("images", []).append(src)
        if tag == "div" and "cap" in classes and self._current is not None:
            self._in_caption = True
            self._buffer = []
        if tag == "section" and "slide" in classes:
            self._current = {"kicker": "", "title": "", "lead": "", "bullets": [],
                             "table": [], "images": [], "caption": ""}
            self.slides.append(self._current)
        elif tag in {"h1", "h2"} and self._current is not None:
            self._buffer = []
        elif tag == "p" and self._current is not None and not self._in_caption:
            self._buffer = []
        elif tag == "li" and self._current is not None:
            self._buffer = []
        elif tag == "table" and self._current is not None:
            self._in_table = True
            self._table_rows = []
        elif tag == "tr" and self._in_table:
            self._row = []
        elif tag in {"td", "th"} and self._in_table:
            self._buffer = []

    def handle_endtag(self, tag: str) -> None:
        if self._stack:
            self._stack.pop()
        if tag == "div" and self._in_caption:
            self._current["caption"] = self._text()
            self._in_caption = False
            self._buffer = []
        elif tag in {"h1", "h2"} and self._current is not None:
            self._current["title"] = self._text()
            self._buffer = []
        elif tag == "p" and self._current is not None and not self._in_caption:
            self._flush()
        elif tag == "li" and self._current is not None:
            text = self._text()
            if text:
                self._current["bullets"].append(text)
            self._buffer = []
        elif tag == "tr" and self._in_table:
            self._table_rows.append(self._row)
            self._row = []
        elif tag in {"td", "th"} and self._in_table:
            self._row.append(self._text())
            self._buffer = []
        elif tag == "table" and self._current is not None:
            self._current["table"] = self._table_rows
            self._in_table = False

    def handle_data(self, data: str) -> None:
        if self._current is not None:
            self._buffer.append(data)

    def handle_startendtag(self, tag: str, attrs: list) -> None:
        self.handle_starttag(tag, attrs)
        self.handle_endtag(tag)


def _strip_markup(text: str) -> str:
    text = re.sub(r"<code>(.*?)</code>", r"\1", text)
    text = re.sub(r"</strong>", " ", text)
    text = re.sub(r"<strong>(.*?)</strong>", r"\1", text)
    text = re.sub(r"<br\s*/?>", " · ", text)
    text = re.sub(r"<[^>]+>", "", text)
    return html.unescape(text).strip()


def _lines_for(text: str, width_chars: int) -> int:
    return max(1, math.ceil(len(text) / width_chars))


def build(source: Path, out: Path) -> int:
    parser = SlideParser()
    parser.feed(source.read_text(encoding="utf-8"))
    slides = parser.slides
    if not slides:
        raise SystemExit("슬라이드를 찾지 못했습니다")

    presentation = Presentation()
    presentation.slide_width = Emu(SLIDE_W)
    presentation.slide_height = Emu(SLIDE_H)
    blank = presentation.slide_layouts[6]
    overflows: list[str] = []

    for index, data in enumerate(slides):
        slide = presentation.slides.add_slide(blank)
        title = _strip_markup(data["title"])
        bullets = [_strip_markup(item) for item in data["bullets"]]
        rows = data.get("table") or []
        images = data.get("images") or []
        caption = _strip_markup(data.get("caption", ""))

        # ── 제목 ───────────────────────────────────────────────
        box = slide.shapes.add_textbox(Emu(MARGIN_X), Emu(TITLE_Y), Emu(CONTENT_W), Emu(TITLE_H))
        frame = box.text_frame
        frame.word_wrap = True
        paragraph = frame.paragraphs[0]
        run = paragraph.add_run()
        run.text = title
        run.font.size = Pt(30)
        run.font.bold = True
        run.font.color.rgb = INK
        run.font.name = FONT

        y = CONTENT_TOP
        font_size = 16
        width_chars = int(CONTENT_W / 210_000)      # 글자당 대략 폭(EMU)

        # ── 본문(표 또는 불릿) ─────────────────────────────────
        if rows:
            table_h = ROW_H * len(rows)
            table_shape = slide.shapes.add_table(
                len(rows), len(rows[0]), Emu(MARGIN_X), Emu(y), Emu(CONTENT_W), Emu(table_h))
            table = table_shape.table
            for r, row in enumerate(rows):
                for c, value in enumerate(row):
                    cell = table.cell(r, c)
                    cell.text = _strip_markup(value)
                    para = cell.text_frame.paragraphs[0]
                    para.font.size = Pt(13 if r == 0 else 14)
                    para.font.bold = r == 0
                    para.font.color.rgb = MUTED if r == 0 else INK
                    para.font.name = FONT
                    if c and r:
                        para.alignment = PP_ALIGN.RIGHT
            y += table_h + GAP
        else:
            for bullet in bullets:
                lines = _lines_for(bullet, width_chars)
                h = lines * LINE_H + GAP
                tb = slide.shapes.add_textbox(Emu(MARGIN_X), Emu(y), Emu(CONTENT_W), Emu(h))
                tf = tb.text_frame
                tf.word_wrap = True
                para = tf.paragraphs[0]
                run = para.add_run()
                run.text = "• " + bullet
                run.font.size = Pt(font_size)
                run.font.color.rgb = INK
                run.font.name = FONT
                para.space_after = Pt(6)
                y += h

        # ── 이미지: 남은 공간 안에서만 배치 ────────────────────
        if images:
            try:
                from PIL import Image
            except ImportError:
                Image = None
            for src in images:
                path = (source.parent / src).resolve()
                if not path.is_file():
                    print(f"  ! 이미지 없음: {src}")
                    continue
                if Image is not None:
                    with Image.open(path) as probe:
                        iw, ih = probe.size
                else:
                    iw, ih = 1600, 1000
                avail_h = BOTTOM_LIMIT - y - (CAPTION_H if caption else 0)
                if avail_h <= 400_000:
                    print(f"  ! 공간 부족으로 이미지 생략: {src}")
                    continue
                scale = min(CONTENT_W / iw, avail_h / ih)
                w, h = int(iw * scale), int(ih * scale)
                slide.shapes.add_picture(str(path), Emu(MARGIN_X), Emu(y), Emu(w), Emu(h))
                y += h + 60_000
                if caption:
                    tb = slide.shapes.add_textbox(Emu(MARGIN_X), Emu(y), Emu(CONTENT_W), Emu(CAPTION_H))
                    para = tb.text_frame.paragraphs[0]
                    run = para.add_run()
                    run.text = caption
                    run.font.size = Pt(12)
                    run.font.color.rgb = MUTED
                    run.font.name = FONT
                    y += CAPTION_H

        # ── 경계 검사 ──────────────────────────────────────────
        for shape in slide.shapes:
            try:
                bottom = shape.top + shape.height
                right = shape.left + shape.width
            except TypeError:
                continue
            if bottom > SLIDE_H or right > SLIDE_W:
                overflows.append(
                    f"슬라이드 {index + 1}: {shape.shape_type} 하단 {bottom} 우측 {right}")
                break

    out.parent.mkdir(parents=True, exist_ok=True)
    presentation.save(out)
    print(f"saved: {out} ({len(slides)} slides)")
    if overflows:
        print("★ 슬라이드 범위를 벗어난 도형:")
        for item in overflows:
            print(f"   {item}")
        return 1
    print("경계 검사: 모든 도형이 슬라이드 안 ✓")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="발표 HTML → PPTX (경계 보장)")
    parser.add_argument("--source", default="doc/reports/presentation.html")
    parser.add_argument("--out", default="doc/reports/presentation.pptx")
    args = parser.parse_args()
    return build(Path(args.source), Path(args.out))


if __name__ == "__main__":
    raise SystemExit(main())
