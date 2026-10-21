"""발표 슬라이드 HTML → PPTX 변환기.

왜 HTML을 읽는가
    슬라이드 본체를 HTML 한 벌로 두고, PDF(Chrome)와 PPTX(여기) 두 형식을
    같은 내용에서 뽑습니다. 내용을 두 곳에 적으면 나중에 어긋납니다.

사용
    .venv/bin/python doc/tools/build_pptx.py \
        --source doc/reports/presentation.html \
        --out artifacts/exports/presentation.pptx
"""
from __future__ import annotations

import argparse
import html
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
LINE = RGBColor(0xD9, 0xDE, 0xE5)
FONT = "Apple SD Gothic Neo"


class SlideParser(HTMLParser):
    """발표용 HTML에서 슬라이드별 (kicker, title, lead, bullets, table)를 뽑는다."""

    def __init__(self) -> None:
        super().__init__()
        self.slides: list[dict] = []
        self._current: dict | None = None
        self._stack: list[str] = []
        self._buffer: list[str] = []
        self._in_table = False
        self._table_rows: list[list[str]] = []
        self._row: list[str] = []

    # --- 헬퍼
    def _text(self) -> str:
        return html.unescape(re.sub(r"\s+", " ", "".join(self._buffer)).strip())

    def _flush(self) -> None:
        if self._current is not None and self._buffer:
            self._current.setdefault("lead", "")
            self._current["lead"] = (self._current["lead"] + " " + self._text()).strip()
        self._buffer = []

    # --- 파싱
    def handle_starttag(self, tag: str, attrs: list) -> None:
        self._stack.append(tag)
        classes = dict(attrs).get("class", "")
        if tag == "br" and self._current is not None:
            self._buffer.append(" · ")   # 줄바꿈을 구분자로 보존
        if tag == "img" and self._current is not None:
            src = dict(attrs).get("src")
            if src:
                self._current.setdefault("images", []).append(src)
        if tag == "section" and "slide" in classes:
            self._current = {"kicker": "", "title": "", "lead": "", "bullets": [], "table": []}
            self.slides.append(self._current)
        elif tag in {"h1", "h2"} and self._current is not None:
            self._buffer = []
        elif tag == "p" and self._current is not None:
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
        if tag == "strong" and self._current is not None:
            self._buffer.append(" ")
        elif tag in {"h1", "h2"} and self._current is not None:
            self._current["title"] = self._text()
            self._buffer = []
        elif tag == "p" and self._current is not None:
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
        elif tag == "div" and self._current is not None:
            self._flush()

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


def _add_text(slide, text: str, size: int, color=INK, bold: bool = False,
              space_after: int = 6, mono: bool = False, x: int = 800000, y: int = 0,
              width: int = 10600000):
    box = slide.shapes.add_textbox(Emu(x), Emu(y), Emu(width), Emu(500000))
    frame = box.text_frame
    frame.word_wrap = True
    paragraph = frame.paragraphs[0]
    run = paragraph.add_run()
    run.text = text
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.color.rgb = color
    run.font.name = "JetBrains Mono" if mono else FONT
    paragraph.space_after = Pt(space_after)
    box.height = Emu(int(size * 12700 * 2))
    return box


def build(source: Path, out: Path) -> int:
    parser = SlideParser()
    parser.feed(source.read_text(encoding="utf-8"))
    slides = parser.slides
    if not slides:
        raise SystemExit("슬라이드를 찾지 못했습니다")

    presentation = Presentation()
    presentation.slide_width = Emu(12192000)     # 13.333in (16:9)
    presentation.slide_height = Emu(6858000)     # 7.5in
    blank = presentation.slide_layouts[6]

    for index, data in enumerate(slides):
        slide = presentation.slides.add_slide(blank)
        title = _strip_markup(data["title"]) or _strip_markup(data.get("lead", ""))
        bullets = [_strip_markup(item) for item in data["bullets"]]

        if index == 0:  # 표지
            y = 1800000
            _add_text(slide, title, 40, INK, True, 16, y=y)
            y += 1400000
            for bullet in bullets:
                _add_text(slide, bullet, 16, MUTED, False, 4, y=y)
                y += 400000
            continue

        rows = data.get("table") or []
        title_text = title
        y = Emu(420000)
        title_box = slide.shapes.add_textbox(Emu(600000), y, Emu(11000000), Emu(900000))
        frame = title_box.text_frame
        frame.word_wrap = True
        paragraph = frame.paragraphs[0]
        run = paragraph.add_run()
        run.text = title_text
        run.font.size = Pt(30)
        run.font.bold = True
        run.font.color.rgb = INK
        run.font.name = FONT

        y = Emu(1350000)
        if rows:
            table_shape = slide.shapes.add_table(
                len(rows), len(rows[0]), Emu(600000), y, Emu(11000000),
                Emu(420000 * len(rows)))
            table = table_shape.table
            for row_index, row in enumerate(rows):
                for col_index, value in enumerate(row):
                    table_cell = table.cell(row_index, col_index)
                    table_cell.text = _strip_markup(value)
                    paragraph = table_cell.text_frame.paragraphs[0]
                    paragraph.font.size = Pt(14 if row_index else 12)
                    paragraph.font.bold = row_index == 0
                    paragraph.font.color.rgb = MUTED if row_index == 0 else INK
                    paragraph.font.name = FONT
                    if col_index and row_index:
                        paragraph.alignment = PP_ALIGN.RIGHT
            y = Emu(1350000 + 420000 * len(rows) + 120000)
        else:
            for bullet in bullets:
                box = slide.shapes.add_textbox(Emu(700000), y, Emu(10500000), Emu(500000))
                frame = box.text_frame
                frame.word_wrap = True
                paragraph = frame.paragraphs[0]
                run = paragraph.add_run()
                run.text = "• " + bullet
                run.font.size = Pt(16)
                run.font.color.rgb = INK
                run.font.name = FONT
                paragraph.space_after = Pt(10)
                y = Emu(y + 520000)

        # 화면 캡처(과제 요구: 캡처 필수) — 이미지가 있으면 아래에 배치한다.
        for src in data.get("images", []):
            image_path = (source.parent / src).resolve()
            if not image_path.is_file():
                print(f"  ! 이미지 없음: {src}")
                continue
            from PIL import Image  # Pillow가 없으면 건너뛴다
            with Image.open(image_path) as probe:
                width, height = probe.size
            max_w, max_h = 11_000_000, 4_400_000
            scale = min(max_w / width, max_h / height)
            pic = slide.shapes.add_picture(str(image_path), Emu(600000), y,
                                          Emu(int(width * scale)), Emu(int(height * scale)))
            y = Emu(y + int(height * scale) + 100000)

    out.parent.mkdir(parents=True, exist_ok=True)
    presentation.save(out)
    print(f"saved: {out} ({len(slides)} slides)")
    return len(slides)


def main() -> int:
    parser = argparse.ArgumentParser(description="발표 HTML → PPTX")
    parser.add_argument("--source", default="doc/reports/presentation.html")
    parser.add_argument("--out", default="artifacts/exports/presentation.pptx")
    args = parser.parse_args()
    build(Path(args.source), Path(args.out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
