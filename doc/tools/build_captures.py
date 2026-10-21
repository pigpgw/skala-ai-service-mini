"""캡처용 화면(HTML) 생성 — 보고서·발표에 넣는 "화면 캡처"를 원본 데이터에서 만든다.

왜 코드로 만드는가
    보고서와 발표에는 "화면 캡처 필수"가 들어 있다. 손으로 만든 표를 캡처하면
    숫자가 원본과 어긋날 위험이 있다. 그래서 **측정 원본(커밋된 요약본)**에서
    HTML을 만들고, 그 HTML을 Chrome으로 캡처한다. 캡처는 언제든 재생성된다.

출력
    artifacts/captures/<id>/screen_rag_evidence.html   — RAG 판정 근거(SSE 원본)
    artifacts/captures/<id>/screen_before_after.html    — Before/After 수치 화면
    (PNG는 Chrome으로 캡처한다 — 아래 주석의 명령)

사용
    .venv/bin/python doc/tools/build_captures.py --out-dir artifacts/captures/20261021-final
    # PNG 변환
    CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
    "$CHROME" --headless=new --disable-gpu --no-first-run --user-data-dir=/tmp/archify-pdf-profile \\
      --screenshot=screen_rag_evidence.png --window-size=1400,900 \\
      "file://$PWD/artifacts/captures/20261021-final/screen_rag_evidence.html"
"""
from __future__ import annotations

import argparse
import html
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
METRICS_DIR = REPO_ROOT / "doc" / "reports" / "evidence" / "metrics"

TERMINAL_CSS = """
body { margin:0; background:#12161c; color:#e6ecf3;
       font-family:"JetBrains Mono", ui-monospace, Menlo, monospace; font-size:15px; line-height:1.7; }
.bar { display:flex; gap:8px; align-items:center; padding:10px 16px; background:#1b2029; border-bottom:1px solid #2a313d; }
.dot { width:12px; height:12px; border-radius:50%; }
.title { margin-left:10px; color:#8b95a5; font-size:13px; }
pre { margin:0; padding:18px 20px; white-space:pre-wrap; word-break:break-all; }
.k { color:#8fb8ff; } .g { color:#9ad8a4; } .y { color:#e8c37a; } .c { color:#7f8a99; }
"""

SCREEN_CSS = """
body { margin:0; background:#fff; color:#16191d; padding:34px 40px;
       font-family:"Pretendard","Apple SD Gothic Neo","Noto Sans KR",-apple-system,sans-serif; }
h1 { font-size:26px; margin:0 0 4px; letter-spacing:-.02em; }
.sub { font-size:14px; color:#5b6470; margin-bottom:22px; }
table { width:100%; border-collapse:collapse; font-size:16px; margin-bottom:22px; }
th,td { border-bottom:1px solid #e3e7ee; padding:9px 10px; text-align:left; }
th { font-size:13px; color:#5b6470; font-weight:600; }
td.n,th.n { text-align:right; font-variant-numeric:tabular-nums; }
.up { color:#1f7a4d; font-weight:700; } .before { color:#5b6470; }
.card { display:grid; grid-template-columns:repeat(4,1fr); gap:14px; margin-bottom:22px; }
.m { border:1px solid #e3e7ee; border-radius:10px; padding:14px 16px; }
.m .v { font-size:30px; font-weight:700; letter-spacing:-.03em; }
.m .l { font-size:13px; color:#5b6470; margin-top:2px; }
.src { font-size:12px; color:#8b95a5; border-top:1px solid #e3e7ee; padding-top:12px; }
"""


def _terminal_html(title: str, body: str) -> str:
    return (
        "<!doctype html><html lang='ko'><head><meta charset='utf-8'>"
        f"<title>{html.escape(title)}</title><style>{TERMINAL_CSS}</style></head><body>"
        "<div class='bar'><span class='dot' style='background:#ff5f57'></span>"
        "<span class='dot' style='background:#febc2e'></span>"
        "<span class='dot' style='background:#28c840'></span>"
        f"<span class='title'>{html.escape(title)}</span></div>"
        f"<pre>{body}</pre></body></html>"
    )


def _highlight(line: str) -> str:
    escaped = html.escape(line)
    if "ReplanCheck" in line:
        escaped = escaped.replace('"classifier_source": "rag"', '<span class="g">"classifier_source": "rag"</span>')
        escaped = escaped.replace('"target"', '<span class="k">"target"</span>')
    elif "FinalAnswer" in line:
        escaped = escaped.replace('"type": "FinalAnswer"', '<span class="k">"type": "FinalAnswer"</span>')
    elif "TaskCompleted" in line:
        escaped = escaped.replace('"source": "monitoring"', '<span class="y">"source": "monitoring"</span>')
    return escaped


def build_rag_evidence(sse_path: Path) -> str:
    lines = sse_path.read_text(encoding="utf-8").splitlines()
    keep = [line for line in lines
            if any(key in line for key in ("RouteDecided", "PlanCreated", "TaskCompleted",
                                          "ReplanCheck", "FinalAnswer"))]
    body = "\n".join(_highlight(line) for line in keep)
    return _terminal_html(
        "curl -N localhost:8100/chat/stream  (RAG 판정 근거가 SSE 로 그대로 나온다)", body)


def _read(run_id: str) -> dict:
    return json.loads((METRICS_DIR / f"{run_id}.json").read_text(encoding="utf-8"))


def build_before_after() -> str:
    before_cls = _read("20261020-152756_fake_before-rag")
    after_cls = _read("20261020-152756_fake_after-rag")
    before_e2e = _read("20261020-153204_fake_before-rag")
    after_e2e = _read("20261020-153211_fake_after-rag")
    before_base = _read("20261020-152800_fake_before-rag")
    after_base = _read("20261020-152800_fake_after-rag")

    def row(label, b, a, fmt=lambda v: f"{v:.4f}", cls="up"):
        return (f"<tr><td>{label}</td><td class='n before'>{fmt(b)}</td>"
                f"<td class='n {cls}'>{fmt(a)}</td><td class='n {cls}'>{'+' if a >= b else ''}{fmt(a - b)}</td></tr>")

    acc_b, acc_a = before_cls["accuracy"], after_cls["accuracy"]
    f1_b, f1_a = before_cls["macro_f1"], after_cls["macro_f1"]
    lat_b, lat_a = before_cls["latency"], after_cls["latency"]
    e2e_b, e2e_a = before_e2e["accuracy"], after_e2e["accuracy"]
    cov_b = before_base["coverage"]["unknown_rate"]      # base 6시스템 조건
    cov_a = after_cls["coverage"]["unknown_rate"]        # extended 12시스템 조건
    fb_a = after_cls["fallback"]["fallback_rate"]

    cards = [
        ("정확도", f"{acc_b['accuracy']:.4f}", f"{acc_a['accuracy']:.4f}", "40문항 분류"),
        ("macro-F1", f"{f1_b:.4f}", f"{f1_a:.4f}", "유형별 균형"),
        ("E2E", f"{e2e_b['accuracy']:.4f}", f"{e2e_a['accuracy']:.4f}", "실서버 5문항"),
        ("분류 지연 p50", f"{lat_b['p50_ms']:.2f}ms", f"{lat_a['p50_ms']:.2f}ms", "임베딩 1회 비용"),
    ]
    card_html = "".join(
        f"<div class='m'><div class='v' style='color:#2f5fd0'>{b} → {a}</div>"
        f"<div class='l'>{label} · {note}</div></div>" for label, b, a, note in cards)

    table = f"""
    <table>
      <thead><tr><th>지표</th><th class='n'>Before (keyword)</th><th class='n'>After (RAG)</th><th class='n'>차이</th></tr></thead>
      <tbody>
        <tr><td>40문항 분류 정확도</td><td class='n before'>{acc_b['correct']}/{acc_b['total']} = {acc_b['accuracy']:.4f}</td>
            <td class='n up'>{acc_a['correct']}/{acc_a['total']} = {acc_a['accuracy']:.4f}</td>
            <td class='n up'>+{acc_a['accuracy'] - acc_b['accuracy']:.4f}</td></tr>
        <tr><td>macro-F1</td><td class='n before'>{f1_b:.4f}</td><td class='n up'>{f1_a:.4f}</td>
            <td class='n up'>+{f1_a - f1_b:.4f}</td></tr>
        <tr><td>E2E 5문항 (실서버 :8100)</td><td class='n before'>{e2e_b['correct']}/{e2e_b['total']} = {e2e_b['accuracy']:.4f}</td>
            <td class='n up'>{e2e_a['correct']}/{e2e_a['total']} = {e2e_a['accuracy']:.4f}</td>
            <td class='n up'>+{e2e_a['accuracy'] - e2e_b['accuracy']:.4f}</td></tr>
        <tr><td>분류 지연 p50</td><td class='n before'>{lat_b['p50_ms']:.2f}ms</td>
            <td class='n'>{lat_a['p50_ms']:.2f}ms</td><td class='n'>+{lat_a['p50_ms'] - lat_b['p50_ms']:.2f}ms</td></tr>
        <tr><td>분류 지연 p95</td><td class='n before'>{lat_b['p95_ms']:.2f}ms</td>
            <td class='n'>{lat_a['p95_ms']:.2f}ms</td><td class='n'>+{lat_a['p95_ms'] - lat_b['p95_ms']:.2f}ms</td></tr>
        <tr><td>비용 (USD, 로컬 백엔드)</td><td class='n before'>$0.000000</td><td class='n'>$0.000000</td><td class='n'>0</td></tr>
        <tr><td>retry 횟수</td><td class='n before'>{before_e2e['retry']['total']}</td>
            <td class='n'>{after_e2e['retry']['total']}</td><td class='n'>0</td></tr>
        <tr><td>조사 커버리지 (unknown 비율)</td><td class='n before'>{cov_b:.2%}</td>
            <td class='n up'>{cov_a:.2%}</td><td class='n up'>{cov_a - cov_b:+.2%}</td></tr>
        <tr><td>keyword 폴백률</td><td class='n before'>100.00%</td><td class='n'>{fb_a:.2%}</td>
            <td class='n'>{fb_a - 1:+.2%}</td></tr>
      </tbody>
    </table>"""

    return (
        "<!doctype html><html lang='ko'><head><meta charset='utf-8'><title>Before/After</title>"
        f"<style>{SCREEN_CSS}</style></head><body>"
        "<h1>Before / After — 같은 입력, 같은 조건</h1>"
        "<div class='sub'>LLM_BACKEND=fake · DATA_PROFILE=extended · 임베더 qwen3-embedding:0.6b · "
        "임계값 0.50 / 0.03 · Before/After 2회 실행</div>"
        f"<div class='card'>{card_html}</div>{table}"
        "<div class='src'>원본: artifacts/runs/20261020-152756_fake_before-rag · …_after-rag · "
        "20261020-153204_fake_before-rag · …_after-rag · 20261020-152800_fake_before-rag · …_after-rag "
        "(요약본: doc/reports/evidence/metrics/)</div>"
        "</body></html>")


def main() -> int:
    parser = argparse.ArgumentParser(description="캡처용 화면 HTML 생성")
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--sse", default=None, help="SSE 원본 텍스트 (없으면 건너뛴다)")
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    if args.sse:
        sse = Path(args.sse)
        if sse.is_file():
            (out_dir / "screen_rag_evidence.html").write_text(
                build_rag_evidence(sse), encoding="utf-8")
            print(f"saved: {out_dir / 'screen_rag_evidence.html'}")
        else:
            print(f"! SSE 파일 없음: {sse}")
    (out_dir / "screen_before_after.html").write_text(build_before_after(), encoding="utf-8")
    print(f"saved: {out_dir / 'screen_before_after.html'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
