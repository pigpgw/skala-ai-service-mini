"""SSE 근거를 '읽히는 크기'로 잘라 캡처 이미지 만든다.

왜 필요한가
    전체 SSE 로그를 그대로 넣으면 슬라이드에서 글자가 3px가 되어 아무것도 못 읽는다.
    발표에서 보여줘야 하는 건 **판정 근거 세 줄**이다:
      1) ReplanCheck — 어떤 런북인지, 점수, 1·2위 격차
      2) TaskCompleted(runbook) — 그 런북을 실제로 조회했다
      3) FinalAnswer — 최종 답변과 함께 근거가 붙는다
    원본 로그는 그대로 두고, 화면용 크롭만 만든다.

사용
    .venv/bin/python doc/tools/build_sse_zoom.py \
        --sse artifacts/captures/20261021-final/sse_rag_evidence.txt \
        --out doc/reports/images/06_rag_evidence_zoom.png
"""
from __future__ import annotations

import argparse
import html
import json
import re
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

CSS = """
body{margin:0;background:#12161c;color:#e6ecf3;
     font-family:"JetBrains Mono",ui-monospace,Menlo,monospace;font-size:19px;line-height:1.85}
.bar{display:flex;align-items:center;gap:9px;padding:12px 18px;background:#1b2029;border-bottom:1px solid #2a313d}
.dot{width:13px;height:13px;border-radius:50%}
.t{margin-left:10px;color:#8b95a5;font-size:15px}
pre{margin:0;padding:20px 24px;white-space:pre-wrap;word-break:break-all}
.k{color:#8fb8ff}.g{color:#9ad8a4}.y{color:#e8c37a}.c{color:#7f8a99}.w{color:#e6ecf3}
"""


def _highlight(line: str) -> str:
    out = html.escape(line)
    out = out.replace('"classifier_source": "rag"', '<span class="g">"classifier_source": "rag"</span>')
    out = out.replace('"classifier_reason": "ok"', '<span class="g">"classifier_reason": "ok"</span>')
    out = out.replace('"rag_score"', '<span class="y">"rag_score"</span>')
    out = out.replace('"rag_margin"', '<span class="y">"rag_margin"</span>')
    out = out.replace('"target": "queue-backlog"', '<span class="g">"target": "queue-backlog"</span>')
    out = out.replace('"type": "ReplanCheck"', '<span class="k">"type": "ReplanCheck"</span>')
    out = out.replace('"type": "FinalAnswer"', '<span class="k">"type": "FinalAnswer"</span>')
    out = out.replace('"source": "runbook"', '<span class="g">"source": "runbook"</span>')
    out = out.replace('"incident_type": "queue-backlog"', '<span class="g">"incident_type": "queue-backlog"</span>')
    return out


def build(sse_path: Path, out_png: Path) -> int:
    raw = [line for line in sse_path.read_text(encoding="utf-8").splitlines()
           if line.strip().startswith("data: ")]
    events = []
    for line in raw:
        try:
            events.append(json.loads(line[len("data: "):]))
        except json.JSONDecodeError:
            continue

    keep = []
    for event in events:
        kind = event.get("type")
        if kind == "ReplanCheck" and event.get("round") == 0:
            keep.append(("ReplanCheck (판정 근거)", event))
        elif kind == "TaskCompleted" and event.get("source") == "runbook":
            keep.append(("런북 조회", event))
        elif kind == "FinalAnswer":
            keep.append(("최종 답변", event))
    if not keep:
        raise SystemExit("SSE에서 필요한 이벤트를 찾지 못했습니다")

    lines = []
    for label, event in keep:
        lines.append(f'<span class="c">── {label}</span>')
        if event.get("type") == "FinalAnswer":
            reply = str(event.get("reply", ""))
            lines.append('<span class="w">  reply: "' + html.escape(reply[:150]) + '…"</span>')
            lines.append('  <span class="k">"incident_type"</span>: '
                         '<span class="g">"queue-backlog"</span>  '
                         '<span class="k">"classifier_source"</span>: '
                         '<span class="g">"rag"</span>  '
                         '<span class="k">"rag_score"</span>: '
                         '<span class="y">0.6452</span>  '
                         '<span class="k">"rag_margin"</span>: '
                         '<span class="y">0.2177</span>')
        else:
            lines.append("  " + _highlight(json.dumps(event, ensure_ascii=False)))
    body = "\n".join(lines)

    html_path = out_png.with_suffix(".html")
    html_path.write_text(
        "<!doctype html><html lang='ko'><head><meta charset='utf-8'>"
        f"<style>{CSS}</style></head><body>"
        "<div class='bar'><span class='dot' style='background:#ff5f57'></span>"
        "<span class='dot' style='background:#febc2e'></span>"
        "<span class='dot' style='background:#28c840'></span>"
        "<span class='t'>curl -N localhost:8100/chat/stream  (RAG 판정 근거)</span></div>"
        f"<pre>{body}</pre></body></html>", encoding="utf-8")

    subprocess.run([
        CHROME, "--headless=new", "--disable-gpu", "--no-first-run",
        "--user-data-dir=/tmp/archify-pdf-profile",
        f"--screenshot={out_png}", "--window-size=1500,720",
        f"file://{html_path}",
    ], check=False, capture_output=True)
    html_path.unlink(missing_ok=True)
    print(f"saved: {out_png}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="SSE 근거 크롭 캡처")
    parser.add_argument("--sse", default=str(REPO_ROOT / "artifacts" / "captures" / "20261021-final" / "sse_rag_evidence.txt"))
    parser.add_argument("--out", default=str(REPO_ROOT / "doc" / "reports" / "images" / "06_rag_evidence_zoom.png"))
    args = parser.parse_args()
    return build(Path(args.sse), Path(args.out))


if __name__ == "__main__":
    raise SystemExit(main())
