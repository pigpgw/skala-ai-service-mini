"""Markdown → HTML 변환기 (의존성 없이, 제출 문서용 최소 구현).

왜 직접 만들었나
    제출 보고서(.md)를 PDF로 넘기는데 pandoc·wkhtmltopdf가 이 머신에 없다.
    Chrome 헤드리스로 PDF를 뽑으려면 HTML이 필요한데, 보고서에 쓰는 문법은
    제목·문단·표·목록·코드블록·이미지·인라인 강조 뿐이다. 그 정도만 지원하면
    충분해서 외부 도구 없이 만들었다.

지원하는 문법
    # ~ ###### 제목, 빈 줄로 구분된 문단, - / * 목록, 1. 목록,
    | a | b | 표(GFM), ``` 코드블록, > 인용, --- 구분선,
    **굵게**, `코드`, [링크](url), ![이미지](경로)

사용
    .venv/bin/python doc/tools/md2html.py doc/reports/result_report.md \
        --out doc/reports/result_report.html --title "AI 서비스 Mini-project 과제 보고서"
"""
from __future__ import annotations

import argparse
import html
import re
from pathlib import Path

CSS = """
:root { --ink:#1a1d21; --muted:#5b6470; --line:#d9dee5; --accent:#2f5fd0; --code:#f5f7fa; }
* { box-sizing: border-box; }
body {
  margin: 0 auto; padding: 44px 52px; max-width: 900px;
  font-family: "Pretendard", "Apple SD Gothic Neo", "Noto Sans KR", -apple-system, sans-serif;
  color: var(--ink); line-height: 1.75; font-size: 15px; word-break: keep-all;
}
h1 { font-size: 26px; margin: 0 0 6px; letter-spacing: -0.02em; }
h2 { font-size: 19px; margin: 38px 0 12px; padding-bottom: 7px; border-bottom: 2px solid var(--line); }
h3 { font-size: 16px; margin: 26px 0 8px; }
h4 { font-size: 15px; margin: 20px 0 6px; color: var(--muted); }
p { margin: 11px 0; line-height: 1.95; }
ul, ol { margin: 10px 0; padding-left: 24px; }
li { margin: 4px 0; }
code { background: var(--code); padding: 0 4px; border-radius: 4px; font-size: 12.5px; line-height: 1.45;
       font-family: "JetBrains Mono", ui-monospace, Menlo, monospace; }
pre { background: var(--code); border: 1px solid var(--line); border-radius: 8px;
      padding: 14px 16px; overflow-x: auto; }
pre code { background: none; padding: 0; font-size: 12.5px; line-height: 1.6; }
table { border-collapse: collapse; width: 100%; margin: 16px 0; font-size: 13.5px; }
th, td { border: 1px solid var(--line); padding: 7px 10px; text-align: left; vertical-align: top; }
th { background: #f7f9fc; font-weight: 600; }
tr:nth-child(even) td { background: #fbfcfe; }
blockquote { margin: 14px 0; padding: 8px 16px; border-left: 3px solid var(--accent);
             background: #f7f9fd; color: var(--muted); }
img { display: block; max-width: 100%; border: 1px solid var(--line); border-radius: 8px; margin: 12px 0 6px; }
hr { border: none; border-top: 1px solid var(--line); margin: 30px 0; }
a { color: var(--accent); }
table, pre, img, h2, h3 { page-break-inside: avoid; }
@page { size: A4; margin: 18mm 16mm; }
@media print {
  body { padding: 0; max-width: none; font-size: 11pt; }
  h2 { margin-top: 26px; }
}
"""

INLINE_CODE = re.compile(r"`([^`]+)`")
BOLD = re.compile(r"\*\*([^*]+)\*\*")
IMAGE = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")
LINK = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")


def _inline(text: str) -> str:
    placeholders: list[str] = []

    def keep(value: str) -> str:
        placeholders.append(value)
        return f"\x00{len(placeholders) - 1}\x00"

    def code_sub(match: re.Match) -> str:
        return keep(f"<code>{html.escape(match.group(1))}</code>")

    def image_sub(match: re.Match) -> str:
        alt, src = match.group(1), match.group(2)
        return keep(f'<img src="{html.escape(src)}" alt="{html.escape(alt)}">')

    def link_sub(match: re.Match) -> str:
        label, href = match.group(1), match.group(2)
        return keep(f'<a href="{html.escape(href)}">{html.escape(label)}</a>')

    def bold_sub(match: re.Match) -> str:
        return keep(f"<strong>{match.group(1)}</strong>")

    text = INLINE_CODE.sub(code_sub, text)
    text = IMAGE.sub(image_sub, text)
    text = LINK.sub(link_sub, text)
    text = BOLD.sub(bold_sub, text)
    text = html.escape(text)
    for index, value in enumerate(placeholders):
        text = text.replace(f"\x00{index}\x00", value)
    return text


def _table_row(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def convert(markdown: str) -> str:
    lines = markdown.splitlines()
    out: list[str] = []
    index = 0

    while index < len(lines):
        line = lines[index]
        stripped = line.strip()

        if not stripped:
            index += 1
            continue

        # 코드 블록
        if stripped.startswith("```"):
            index += 1
            block: list[str] = []
            while index < len(lines) and not lines[index].strip().startswith("```"):
                block.append(lines[index])
                index += 1
            index += 1
            out.append("<pre><code>" + html.escape("\n".join(block)) + "</code></pre>")
            continue

        # 표
        if stripped.startswith("|") and index + 1 < len(lines) and \
                set(lines[index + 1].strip().replace("|", "").replace(" ", "")) <= set("-:"):
            headers = _table_row(lines[index])
            index += 2
            rows: list[list[str]] = []
            while index < len(lines) and lines[index].strip().startswith("|"):
                rows.append(_table_row(lines[index]))
                index += 1
            parts = ["<table><thead><tr>"]
            parts += [f"<th>{_inline(cell)}</th>" for cell in headers]
            parts.append("</tr></thead><tbody>")
            for row in rows:
                parts.append("<tr>" + "".join(f"<td>{_inline(cell)}</td>" for cell in row) + "</tr>")
            parts.append("</tbody></table>")
            out.append("".join(parts))
            continue

        # 제목
        heading = re.match(r"^(#{1,6})\s+(.*)$", stripped)
        if heading:
            level = len(heading.group(1))
            out.append(f"<h{level}>{_inline(heading.group(2))}</h{level}>")
            index += 1
            continue

        # 구분선
        if re.match(r"^(-{3,}|\*{3,})$", stripped):
            out.append("<hr>")
            index += 1
            continue

        # 인용
        if stripped.startswith(">"):
            quote: list[str] = []
            while index < len(lines) and lines[index].strip().startswith(">"):
                quote.append(lines[index].strip().lstrip(">").strip())
                index += 1
            out.append(f"<blockquote>{_inline(' '.join(quote))}</blockquote>")
            continue

        # 목록
        bullet = re.match(r"^(\s*)([-*]|\d+\.)\s+(.*)$", line)
        if bullet:
            ordered = bool(re.match(r"\d+\.", bullet.group(2)))
            items: list[str] = []
            while index < len(lines):
                item = re.match(r"^(\s*)([-*]|\d+\.)\s+(.*)$", lines[index])
                if not item or bool(re.match(r"\d+\.", item.group(2))) != ordered:
                    break
                items.append(item.group(3))
                index += 1
            # 들여쓴 이어쓰기 줄은 마지막 항목의 continuation이다.
            while index < len(lines) and lines[index].strip() and \
                    lines[index].startswith((" ", "\t")) and \
                    not re.match(r"^\s*([-*]\s|\d+\.\s)", lines[index]):
                if items:
                    items[-1] = f"{items[-1]} {lines[index].strip()}"
                index += 1
            tag = "ol" if ordered else "ul"
            body = "".join(f"<li>{_inline(item)}</li>" for item in items)
            out.append(f"<{tag}>{body}</{tag}>")
            continue

        # 문단
        paragraph: list[str] = []
        while index < len(lines) and lines[index].strip() and \
                not re.match(r"^\s*([-*]\s|\d+\.\s|#{1,6}\s|>|\||```)", lines[index]):
            paragraph.append(lines[index].strip())
            index += 1
        if paragraph:
            out.append(f"<p>{_inline(' '.join(paragraph))}</p>")
        else:
            index += 1

    return "\n".join(out)


def main() -> int:
    parser = argparse.ArgumentParser(description="Markdown → HTML")
    parser.add_argument("source")
    parser.add_argument("--out", required=True)
    parser.add_argument("--title", default="")
    args = parser.parse_args()

    source = Path(args.source)
    body = convert(source.read_text(encoding="utf-8"))
    title = args.title or source.stem
    document = (
        "<!doctype html>\n<html lang=\"ko\">\n<head>\n<meta charset=\"utf-8\">\n"
        f"<title>{html.escape(title)}</title>\n<style>{CSS}</style>\n</head>\n"
        f"<body>\n{body}\n</body>\n</html>\n"
    )
    Path(args.out).write_text(document, encoding="utf-8")
    print(f"saved: {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
