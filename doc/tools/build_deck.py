"""발표 덱 → HTML(브라우저·PDF용). 슬라이드 정의는 deck_content.py를 공유한다.

왜 정의를 나눠 두는가
    HTML 덱과 PPTX의 내용이 어긋나면 둘 중 하나가 틀린 말이 된다.
    그래서 **내용은 deck_content.py 한 벌**이고, 렌더러만 둘이다.
      - 이 파일(HTML) : doc/tools/build_deck.py
      - PPTX          : doc/tools/build_pptx_native.py

사용
    .venv/bin/python doc/tools/build_deck.py            # HTML 덱 + PDF
    .venv/bin/python doc/tools/build_deck.py --only html
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))

from deck_content import AUTHOR, DECK_TITLE, SLIDES   # noqa: E402

REPORTS = REPO_ROOT / "doc" / "reports"
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

CSS = """
*{box-sizing:border-box;margin:0;padding:0}
:root{
  --ink:#12151A; --muted:#5A6472; --faint:#8A93A0; --line:#E4E8EE; --bg:#FFFFFF;
  --accent:#2B5FD9; --accent-soft:#EEF3FF; --accent-line:#D3E0FB;
  --good:#17784A; --good-soft:#E9F6EE; --good-line:#C9E7D6;
  --warn:#8A5300; --warn-soft:#FBF3E2; --warn-line:#EDDDBB; --bar:#C4CEDF;
  --sans:"Pretendard","Apple SD Gothic Neo","Malgun Gothic",sans-serif;
  --mono:"Menlo","Consolas",monospace;
}
body{background:#E9EDF3;color:var(--ink);font-family:var(--sans);-webkit-font-smoothing:antialiased}
.slide{width:1280px;height:720px;background:var(--bg);position:relative;overflow:hidden;
       padding:48px 66px 58px;display:flex;flex-direction:column}
.kicker{font-size:14px;font-weight:700;letter-spacing:.06em;color:var(--accent);
        display:flex;align-items:center;gap:14px;margin-bottom:12px}
.kicker .rule{flex:1;height:1px;background:var(--line)}
h1{font-size:48px;line-height:1.18;letter-spacing:-.025em}
h2{font-size:33px;line-height:1.24;letter-spacing:-.022em;margin-bottom:8px}
.sub{font-size:19px;color:var(--muted);line-height:1.5}
.lead{font-size:15.5px;color:var(--muted);line-height:1.5;margin-bottom:22px}
.body{flex:1;display:flex;flex-direction:column;gap:16px}
.row{display:flex;gap:20px}
.col{display:flex;flex-direction:column;gap:16px}
.grow{flex:1}
.card{border:1px solid var(--line);border-radius:13px;padding:17px 20px;background:#fff}
.card.accent{background:var(--accent-soft);border-color:var(--accent-line)}
.card.good{background:var(--good-soft);border-color:var(--good-line)}
.card.warn{background:var(--warn-soft);border-color:var(--warn-line)}
.card h3{font-size:15.5px;font-weight:700;margin-bottom:7px}
.card p{font-size:13.5px;line-height:1.5;color:var(--muted)}
.card p strong{color:var(--ink)}
.stat{display:flex;flex-direction:column;gap:3px}
.stat .v{font-size:30px;font-weight:800;letter-spacing:-.03em;color:var(--accent);line-height:1.1}
.stat .v.good{color:var(--good)} .stat .v.warn{color:var(--warn)}
.stat .l{font-size:12.5px;color:var(--muted)}
ul{list-style:none;display:flex;flex-direction:column;gap:8px}
li{font-size:14px;line-height:1.45;padding-left:17px;position:relative}
li::before{content:"";position:absolute;left:2px;top:8px;width:6px;height:6px;border-radius:2px;background:var(--accent)}
li .where{display:block;font-size:11.5px;color:var(--faint);font-family:var(--mono);margin-top:2px}
code{font-family:var(--mono);font-size:.9em;background:#F4F6FA;border:1px solid var(--line);
     border-radius:5px;padding:1px 5px}
pre{background:#11151B;color:#E7ECF3;border-radius:11px;padding:16px 18px;
    font-family:var(--mono);font-size:13px;line-height:1.68;overflow:hidden;white-space:pre}
pre .k{color:#8FB6FF} pre .c{color:#79839A} pre .s{color:#8FD9A6}
table{width:100%;border-collapse:collapse;font-size:14px}
th{font-size:12px;font-weight:700;color:var(--muted);text-align:left;
   padding:0 10px 7px 0;border-bottom:2px solid #D5DBE5}
td{padding:8px 10px 8px 0;border-bottom:1px solid var(--line);vertical-align:top}
td.n,th.n{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}
td.up{color:var(--good);font-weight:700}
.shot{border:1px solid var(--line);border-radius:11px;overflow:hidden;background:#fff}
.shot img{display:block;width:100%}
.shot .cap{font-size:12px;color:var(--muted);padding:7px 11px;background:#FAFBFD;border-top:1px solid var(--line)}
.foot{position:absolute;left:66px;right:66px;bottom:20px;display:flex;justify-content:space-between;
      align-items:center;font-size:12px;color:var(--faint);border-top:1px solid var(--line);padding-top:9px}
.cover{justify-content:center;padding:48px 90px}
.cover .meta{font-size:15px;color:var(--muted);line-height:1.85}
.cover .meta b{color:var(--ink)}
.plan{display:grid;grid-template-columns:1fr 1fr;gap:16px;max-width:820px;margin-top:30px}
.plan .p{border:1px solid var(--line);border-radius:13px;padding:16px 18px;background:#fff}
.plan .p.a{background:var(--accent-soft);border-color:var(--accent-line)}
.plan .p b{display:block;font-size:17px;margin-bottom:4px}
.plan .p span{font-size:13.5px;color:var(--muted)}
.bar{display:flex;align-items:center;gap:14px;margin-bottom:14px}
.bar .lab{width:178px;font-size:14px;color:var(--ink);text-align:right;line-height:1.3}
.bar .tracks{flex:1;display:flex;flex-direction:column;gap:4px}
.bar .track{height:12px;background:#F1F4F9;border-radius:4px;position:relative;overflow:hidden}
.bar .fill{position:absolute;left:0;top:0;bottom:0;border-radius:4px}
.bar .fill.before{background:var(--bar)} .bar .fill.after{background:var(--accent)}
.bar .val{width:158px;font-size:14px;font-weight:700;font-variant-numeric:tabular-nums;color:var(--muted)}
.bar .val b{color:var(--accent)}
.bar .arrow{color:var(--faint);font-weight:400;padding:0 4px}
.legend{display:flex;gap:16px;font-size:12px;color:var(--muted);margin:9px 0 13px}
.legend i{display:inline-block;width:11px;height:11px;border-radius:3px;margin-right:5px;vertical-align:-1px}
@media print{
  body{background:#fff}
  .slide{box-shadow:none;margin:0;page-break-after:always;break-after:page}
  @page{size:1280px 720px;margin:0}
}
"""

TONE_CLASS = {"plain": "", "accent": "accent", "good": "good", "warn": "warn"}


def _code(lines) -> str:
    out = []
    for tone, text in lines:
        cls = {"k": "k", "c": "c", "s": "s"}.get(tone, "")
        out.append(f'<span class="{cls}">{text}</span>' if cls else text)
    return "\n".join(out)


def _bullets(items) -> str:
    out = []
    for text, where in items:
        out.append(f"<li>{text}" + (f'<span class="where">{where}</span>' if where else "") + "</li>")
    return "<ul>" + "".join(out) + "</ul>"


def _bars(items, legend) -> str:
    out = ['<div class="legend">']
    for tone, label in legend:
        color = "var(--bar)" if tone == "before" else "var(--accent)"
        out.append(f'<span><i style="background:{color}"></i>{label}</span>')
    out.append("</div>")
    for item in items:
        out.append(
            '<div class="bar"><div class="lab">' + item["label"] + "</div>"
            '<div class="tracks">'
            f'<div class="track"><div class="fill before" style="width:{max(3, item["b"] * 100)}%"></div></div>'
            f'<div class="track"><div class="fill after" style="width:{max(3, item["a"] * 100)}%"></div></div>'
            '</div><div class="val">' + item["before"]
            + '<span class="arrow">→</span><b>' + item["after"] + "</b></div></div>")
    return "".join(out)


def _table(block) -> str:
    head = "".join(f"<th{' class=n' if i else ''}>{h}</th>" for i, h in enumerate(block["head"]))
    rows = []
    for row in block["rows"]:
        cells = []
        for i, cell in enumerate(row):
            cls = ' class="n up"' if (i and cell.startswith("−")) else (' class="n"' if i else "")
            cells.append(f"<td{cls}>{cell}</td>")
        rows.append("<tr>" + "".join(cells) + "</tr>")
    return (f'<h3>{block["title"]}</h3><table><thead><tr>{head}</tr></thead>'
            f'<tbody>{"".join(rows)}</tbody></table>')


def _render_block(block, img_prefix="") -> str:
    kind = block["type"]
    if kind == "stats":
        items = "".join(
            f'<div class="card grow stat"><span class="v {TONE_CLASS.get(i.get("tone","accent"),"accent")}">'
            f'{i["value"]}</span><span class="l">{i["label"]}</span></div>' for i in block["items"])
        return f'<div class="row">{items}</div>'
    if kind == "cards2x2":
        cells = []
        for item in block["items"]:
            body = (f'<p>{item["body"]}</p>' if item.get("body")
                    else _bullets(item.get("bullets", [])))
            cells.append(f'<div class="card grow"><h3>{item["title"]}</h3>{body}'
                         f'<span class="where">{item["where"]}</span></div>')
        return '<div class="row">' + "".join(cells[:2]) + '</div><div class="row">' + "".join(cells[2:]) + "</div>"
    if kind == "cards2":
        cells = []
        for item in block["items"]:
            body = (f'<p>{item["body"]}</p>' if item.get("body")
                    else _bullets(item.get("bullets", [])))
            cells.append(f'<div class="card grow"><h3>{item["title"]}</h3>{body}</div>')
        return '<div class="row">' + "".join(cells) + "</div>"
    if kind == "note":
        where = (f'<span class="where">{block["where"]}</span>' if block.get("where") else "")
        return (f'<div class="card {TONE_CLASS.get(block.get("tone","plain"),"")}">'
                f'<h3>{block["title"]}</h3><p>{block["body"]}</p>{where}</div>')
    if kind == "bullets":
        return _bullets(block["items"])
    if kind == "table":
        return f'<div class="card">{_table(block)}</div>'
    if kind == "code":
        caption = (f'<div class="cap">{block["caption"]}</div>' if block.get("caption") else "")
        return f'<pre>{_code(block["lines"])}</pre>{caption}'
    if kind == "bars":
        return f'<div class="card grow">{_bars(block["items"], block["legend"])}</div>'
    if kind == "image":
        return (f'<div class="shot"><img src="{img_prefix}{block["src"]}" alt="">'
                f'<div class="cap">{block["caption"]}</div></div>')
    if kind == "card":
        tone = TONE_CLASS.get(block.get("tone", "plain"), "")
        bullets = _bullets(block["bullets"]) if block.get("bullets") else ""
        body = f'<p>{block["body"]}</p>' if block.get("body") else bullets
        where = (f'<span class="where">{block["where"]}</span>' if block.get("where") else "")
        return f'<div class="card {tone} grow"><h3>{block["title"]}</h3>{body}{where}</div>'
    if kind == "split":
        left = block["left"] if isinstance(block["left"], list) else [block["left"]]
        right = block["right"] if isinstance(block["right"], list) else [block["right"]]
        lh = "".join(_render_block(b, img_prefix) for b in left)
        rh = "".join(_render_block(b, img_prefix) for b in right)
        return f'<div class="row grow"><div class="col grow" style="flex:0 0 56%">{lh}</div>' \
               f'<div class="col grow">{rh}</div></div>'
    raise ValueError(f"알 수 없는 블록: {kind}")


def render_slide(spec, index, img_prefix="") -> str:
    if spec.get("kind") == "cover":
        plan = "".join(
            f'<div class="p{" a" if i == 0 else ""}"><b>{head}</b><span>{body}</span></div>'
            for i, (head, body) in enumerate(spec["plan"]))
        return f"""
<section class="slide cover">
  <div class="kicker">{spec['kicker']}</div>
  <h1>{'<br>'.join(spec['title'])}</h1>
  <div class="sub" style="margin-top:14px">{spec['sub']}</div>
  <div class="plan">{plan}</div>
  <div class="meta" style="margin-top:28px">{'<br>'.join(spec['meta'])}</div>
  <div class="foot"><span>{AUTHOR}</span><span>{index}</span></div>
</section>
"""
    lead = (f'<div class="lead">{spec["lead"].replace(chr(10), "<br>")}</div>'
            if spec.get("lead") else "")
    body = "".join(_render_block(b, img_prefix) for b in spec["blocks"])
    title = spec["title"]
    title_html = "<br>".join(title) if isinstance(title, list) else title
    return f"""
<section class="slide">
  <div class="kicker">{spec['kicker']}<span class="rule"></span></div>
  <h2>{title_html}</h2>
  {lead}
  <div class="body">{body}</div>
  <div class="foot"><span>{spec.get('foot', '')}</span><span>{index}</span></div>
</section>
"""


def build_html() -> Path:
    body = "\n".join(render_slide(spec, i) for i, spec in enumerate(SLIDES, 1))
    out = REPORTS / "presentation.html"
    out.write_text(
        "<!doctype html>\n<html lang='ko'>\n<head>\n<meta charset='utf-8'>\n"
        f"<title>{DECK_TITLE} — 발표자료</title>\n<style>{CSS}</style>\n</head>\n<body>\n{body}\n</body>\n</html>\n",
        encoding="utf-8")
    return out


def build_pdf(html_path: Path) -> Path | None:
    if not Path(CHROME).exists():
        return None
    out = REPORTS / "presentation.pdf"
    subprocess.run([
        CHROME, "--headless=new", "--disable-gpu", "--no-first-run",
        "--user-data-dir=/tmp/archify-pdf-profile",
        f"--print-to-pdf={out}", "--no-pdf-header-footer",
        f"file://{html_path}",
    ], check=False, capture_output=True)
    return out if out.exists() else None


def main() -> int:
    parser = argparse.ArgumentParser(description="발표 덱 → HTML · PDF")
    parser.add_argument("--only", default="all", choices=["all", "html", "pdf"])
    args = parser.parse_args()

    html_path = build_html()
    print(f"saved: {html_path.relative_to(REPO_ROOT)}")
    if args.only == "html":
        return 0
    pdf = build_pdf(html_path)
    if pdf:
        print(f"saved: {pdf.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
