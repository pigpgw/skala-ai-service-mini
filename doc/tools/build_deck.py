"""발표 덱 빌더 — 한 벌의 슬라이드 정의에서 (HTML 덱 · 슬라이드별 HTML · PDF · PPTX)을 만든다.

왜 한 곳에 정의하나
    HTML 덱(브라우저·PDF용)과 슬라이드별 HTML(PPTX 변환용)이 따로 있으면
    내용·수치가 어긋난다. 슬라이드 정의를 한 곳에 두고 생성만 나눈다.

디자인 원칙 (5분 발표)
    - 한 장에 메시지 하나. 표는 최대 5행.
    - 숫자가 주인공: 큰 수치 → 설명, 근거는 화면 캡처.
    - 그리드: 좌우 여백 76px, 본문 폭 1128px, 세로 리듬 24px.
    - 색 4개만: 잉크 · 보조회색 · 강조(파랑) · 긍정(초록) + 경고(앰버).

사용
    .venv/bin/python doc/tools/build_deck.py            # HTML 덱 + 슬라이드별 HTML + PDF + PPTX
    .venv/bin/python doc/tools/build_deck.py --only html
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
REPORTS = REPO_ROOT / "doc" / "reports"
SLIDES_DIR = REPORTS / "slides"

CSS = """
*{box-sizing:border-box;margin:0;padding:0}
:root{
  --ink:#12151A; --muted:#5A6472; --faint:#8A93A0; --line:#E4E8EE; --bg:#FFFFFF;
  --accent:#2B5FD9; --accent-soft:#EEF3FF; --good:#17784A; --good-soft:#E9F6EE;
  --warn:#8A5300; --warn-soft:#FBF3E2;
  --sans:"Pretendard","Apple SD Gothic Neo","Malgun Gothic",sans-serif;
  --mono:"Menlo","Consolas",monospace;
}
body{background:#E9EDF3;color:var(--ink);font-family:var(--sans);-webkit-font-smoothing:antialiased}
.slide{width:1280px;height:720px;background:var(--bg);position:relative;overflow:hidden;
       padding:56px 76px 64px;display:flex;flex-direction:column}
.kicker{font-size:15px;font-weight:700;letter-spacing:.06em;color:var(--accent);
        display:flex;align-items:center;gap:10px;margin-bottom:14px}
.kicker .tag{background:var(--accent-soft);border:1px solid #D3E0FB;border-radius:6px;
             padding:3px 9px;font-size:13.5px}
.kicker .rule{flex:1;height:1px;background:var(--line)}
h1{font-size:52px;line-height:1.16;letter-spacing:-.025em}
h2{font-size:37px;line-height:1.22;letter-spacing:-.022em;margin-bottom:10px}
.sub{font-size:22px;color:var(--muted);line-height:1.5}
.lead{font-size:19px;color:var(--muted);line-height:1.55;margin-bottom:26px;max-width:1000px}
.body{flex:1;display:flex;flex-direction:column;justify-content:flex-start;gap:20px}
.row{display:flex;gap:20px}
.col{display:flex;flex-direction:column;gap:20px}
.grow{flex:1}
.card{border:1px solid var(--line);border-radius:14px;padding:20px 22px;background:#fff}
.card.soft{background:var(--accent-soft);border-color:#D3E0FB}
.card.good{background:var(--good-soft);border-color:#C9E7D6}
.card.warn{background:var(--warn-soft);border-color:#EDDDBB}
.card h3{font-size:17px;font-weight:700;margin-bottom:8px;letter-spacing:-.01em}
.card p{font-size:16px;line-height:1.55;color:var(--muted)}
.card p strong{color:var(--ink)}
.stat{display:flex;flex-direction:column;gap:2px}
.stat .v{font-size:40px;font-weight:800;letter-spacing:-.03em;color:var(--accent);line-height:1.1}
.stat .v.good{color:var(--good)} .stat .v.warn{color:var(--warn)}
.stat .l{font-size:14.5px;color:var(--muted)}
ul{list-style:none;display:flex;flex-direction:column;gap:11px}
li{font-size:17px;line-height:1.5;padding-left:20px;position:relative}
li::before{content:"";position:absolute;left:2px;top:10px;width:7px;height:7px;border-radius:2px;background:var(--accent)}
li strong{font-weight:700}
li .where{display:block;font-size:14px;color:var(--faint);font-family:var(--mono);margin-top:2px}
code{font-family:var(--mono);font-size:.9em;background:#F4F6FA;border:1px solid var(--line);
     border-radius:5px;padding:1px 5px}
pre{background:#11151B;color:#E7ECF3;border-radius:12px;padding:18px 20px;
    font-family:var(--mono);font-size:14.5px;line-height:1.72;overflow:hidden}
pre .k{color:#8FB6FF} pre .c{color:#79839A} pre .s{color:#8FD9A6}
table{width:100%;border-collapse:collapse;font-size:16px}
th{font-size:13px;font-weight:700;color:var(--muted);text-align:left;
   padding:0 12px 8px 0;border-bottom:2px solid #D5DBE5}
td{padding:9px 12px 9px 0;border-bottom:1px solid var(--line);vertical-align:top}
td.n,th.n{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}
td.up{color:var(--good);font-weight:700}
.shot{border:1px solid var(--line);border-radius:12px;overflow:hidden;background:#fff}
.shot img{display:block;width:100%;max-height:420px;object-fit:contain}
.shot .cap{font-size:13px;color:var(--muted);padding:8px 12px;background:#FAFBFD;border-top:1px solid var(--line)}
.foot{position:absolute;left:76px;right:76px;bottom:22px;display:flex;justify-content:space-between;
      align-items:center;font-size:13px;color:var(--faint);border-top:1px solid var(--line);padding-top:10px}
.foot .who{font-weight:600;color:var(--muted)}
.cover{justify-content:center;padding:56px 96px}
.cover .meta{font-size:17px;color:var(--muted);line-height:1.9}
.cover .meta b{color:var(--ink)}
.plan{display:grid;grid-template-columns:1fr 1fr;gap:18px;max-width:880px;margin-top:34px}
.plan .p{border:1px solid var(--line);border-radius:14px;padding:18px 20px;background:#fff}
.plan .p.a{background:var(--accent-soft);border-color:#D3E0FB}
.plan .p b{display:block;font-size:19px;margin-bottom:4px}
.plan .p span{font-size:15px;color:var(--muted)}
.bar{display:flex;align-items:center;gap:16px;margin-bottom:16px}
.bar .lab{width:190px;font-size:16px;color:var(--ink);text-align:right;line-height:1.3}
.bar .tracks{flex:1;display:flex;flex-direction:column;gap:4px}
.bar .track{height:13px;background:#F1F4F9;border-radius:4px;position:relative;overflow:hidden}
.bar .fill{position:absolute;left:0;top:0;bottom:0;border-radius:4px}
.bar .fill.before{background:#C4CEDF}
.bar .fill.after{background:var(--accent)}
.bar .val{width:172px;font-size:16px;font-weight:700;font-variant-numeric:tabular-nums;color:var(--muted)}
.bar .val b{color:var(--accent)}
.bar .arrow{color:var(--faint);font-weight:400;padding:0 4px}
.legend{display:flex;gap:18px;font-size:13.5px;color:var(--muted);margin:10px 0 16px}
.legend i{display:inline-block;width:12px;height:12px;border-radius:3px;margin-right:6px;vertical-align:-1px}
@media print{
  body{background:#fff}
  .slide{box-shadow:none;margin:0;page-break-after:always;break-after:page}
  @page{size:1280px 720px;margin:0}
}
"""


def bar(lab: str, before: str, after: str, before_ratio: float, after_ratio: float) -> str:
    """한 지표를 한 줄로: 라벨 | Before 막대 + After 막대 | Before → After 값."""
    before_w = max(3, min(100, before_ratio * 100))
    after_w = max(3, min(100, after_ratio * 100))
    return (
        f'<div class="bar"><div class="lab">{lab}</div>'
        f'<div class="tracks">'
        f'<div class="track"><div class="fill before" style="width:{before_w}%"></div></div>'
        f'<div class="track"><div class="fill after" style="width:{after_w}%"></div></div>'
        f'</div>'
        f'<div class="val">{before}<span class="arrow">→</span><b>{after}</b></div></div>'
    )


def slide_cover() -> str:
    return """
<section class="slide cover">
  <div class="kicker"><span class="tag">과제 1번</span> SKALA AI 서비스 MINI-PROJECT</div>
  <h1>Base AI Agent의<br>RunBook 선택 개선</h1>
  <div class="sub" style="margin-top:16px">RAG 기반 RunBook 선택 · 라우팅 기준 확대 · 데이터 확장 · 평가 하네스</div>
  <div class="plan">
    <div class="p a"><b>2분 — 기능과 결과</b><span>무엇을 고쳤나 · Before/After 수치</span></div>
    <div class="p"><b>3분 — 코드 설명</b><span>Agent Graph 구성 · MCP · RAG</span></div>
  </div>
  <div class="meta" style="margin-top:30px">
    <b>79번 박건우</b> (G079 · 광주 3반) · 2026-10-21<br>
    github.com/pigpgw/skala-ai-service-mini
  </div>
  <div class="foot"><span class="who">79번 박건우 · 광주 3반</span><span>1</span></div>
</section>
"""


def slide_problem() -> str:
    return """
<section class="slide">
  <div class="kicker"><span class="tag">2분</span>문제<span class="rule"></span></div>
  <h2>장애 유형 판정이 "키워드 첫 매칭"이었다</h2>
  <div class="lead">규칙 순서가 증상 우선순위와 무관했고, 질의문은 아예 보지 않았다.
    고치기 전에 기준선부터 재니 12문항 중 4개가 어긋났다.</div>
  <div class="body">
    <div class="row">
      <div class="card grow stat"><span class="v warn">8/12</span>
        <span class="l">keyword 기준선 정확도 = 0.6667</span></div>
      <div class="card grow stat"><span class="v">4개</span>
        <span class="l">오분류 — 모두 코드 위치로 추적</span></div>
      <div class="card grow stat"><span class="v">0</span>
        <span class="l">질의문을 읽는 코드 (0줄)</span></div>
    </div>
    <div class="row grow">
      <div class="card grow">
        <h3>무엇이 틀렸나</h3>
        <ul>
          <li><strong>B07</strong> gateway(타임아웃) + payments(CPU)를 함께 보면 알림이 한 덩어리라
            <code>cpu</code>가 먼저 잡힘
            <span class="where">agent/graph.py:195-216</span></li>
          <li><strong>B09</strong> <code>memory</code>가 <code>disk</code>보다 앞에 있어 디스크 문제를
            메모리 절차로 답함</li>
          <li><strong>B10·B11</strong> 판정 함수가 질의문을 읽지 않음 → "디스크 부족"이
            지연으로 분류됨</li>
          <li><strong>매칭 실패</strong> → 무조건 <code>db-down</code> ("아무 장애나 db-down 대응")</li>
        </ul>
      </div>
      <div class="card soft" style="flex:0 0 420px">
        <h3>판정 로직 (개선 전)</h3>
        <pre><span class="c"># agent/graph.py</span>
<span class="k">for</span> keyword, incident_type <span class="k">in</span> _RULES:
    <span class="k">if</span> keyword <span class="k">in</span> text:
        <span class="k">return</span> incident_type   <span class="c"># 첫 매칭</span>
<span class="k">return</span> <span class="s">"db-down"</span>            <span class="c"># 기본값</span></pre>
      </div>
    </div>
  </div>
  <div class="foot"><span class="who">문제 — agent/graph.py::_classify_incident_type</span><span>2</span></div>
</section>
"""


def slide_changes() -> str:
    return """
<section class="slide">
  <div class="kicker"><span class="tag">2분</span>개선한 기능<span class="rule"></span></div>
  <h2>네 축을 손봤다 — 판정 하나를 바꾸고, 측정할 수 있게 만들었다</h2>
  <div class="body">
    <div class="row">
      <div class="card grow">
        <h3>1. RAG 기반 RunBook 선택</h3>
        <p>키워드 첫 매칭 → 런북 10종 임베딩 의미 검색. <strong>확신이 없으면
          keyword로 폴백</strong>해 기존 동작이 깨지지 않게 했다.</p>
        <span class="where">agent/rag/{embedder,index,classifier}.py</span>
      </div>
      <div class="card grow">
        <h3>2. 라우팅 기준 확대</h3>
        <p>결정론 백엔드의 정규식이 키워드 7개뿐이라 <strong>매뉴얼 예시 질의 7개가
          chat으로</strong> 떨어졌다. 운영 어휘로 넓혔다.</p>
        <span class="where">agent/fake_llm.py::route</span>
      </div>
    </div>
    <div class="row">
      <div class="card grow">
        <h3>3. 데이터 확장</h3>
        <p>모니터링 <strong>6 → 12시스템</strong>, 런북 <strong>6 → 10종</strong>
          (신규 유형 4종). 파일 선택은 한 곳에서만.</p>
        <span class="where">agent/data_profile.py · data/monitoring_extended.json</span>
      </div>
      <div class="card grow">
        <h3>4. 평가 하네스</h3>
        <p>실행 1회 = 폴더 1개(<strong>조건·지표·입출력</strong>), 40문항 라벨 동결,
          회귀 10문항 실행기, <strong>문서 숫자 ↔ 원본 자동 대조</strong>.</p>
        <span class="where">eval/run_eval.py · tests/ (65개)</span>
      </div>
    </div>
    <div class="card good" style="padding:16px 22px">
      <p><strong>개선 후 회귀 질의 10개: 3/10 → 10/10</strong> — 매뉴얼 9쪽이 알려준
        테스트 질의로 자기 자신을 테스트할 수 없던 상태였다.</p>
    </div>
  </div>
  <div class="foot"><span class="who">개선 — agent/rag/* · agent/fake_llm.py · agent/data_profile.py · eval/</span><span>3</span></div>
</section>
"""


def slide_results() -> str:
    return """
<section class="slide">
  <div class="kicker"><span class="tag">2분</span>결과<span class="rule"></span></div>
  <h2>같은 입력, 같은 조건 — 2회 실행한 결과</h2>
  <div class="body">
    <div class="row grow">
      <div class="col grow" style="flex:0 0 520px">
        <div class="card grow" style="justify-content:center">
          <h3>검색 정확도</h3>
          <div class="legend"><span><i style="background:#C4CEDF"></i>Before (keyword)</span>
            <span><i style="background:var(--accent)"></i>After (RAG)</span></div>
          """ + bar("40문항 분류 정확도", "0.3250", "0.8500", 0.3250, 0.8500) + """
          """ + bar("macro-F1", "0.2836", "0.8521", 0.2836, 0.8521) + """
          """ + bar("E2E 5문항 (실서버)", "0.2000", "1.0000", 0.2000, 1.0) + """
          """ + bar("회귀 10문항", "3/10", "10/10", 0.30, 1.0) + """
        </div>
      </div>
      <div class="col grow">
        <div class="card">
          <h3>비용과 부작용</h3>
          <table>
            <thead><tr><th>지표</th><th class="n">Before</th><th class="n">After</th><th class="n">차이</th></tr></thead>
            <tbody>
              <tr><td>분류 지연 p50</td><td class="n">0.0ms</td><td class="n">32.43ms</td><td class="n">+32.43ms</td></tr>
              <tr><td>비용 (USD)</td><td class="n">0.000000</td><td class="n">0.000000</td><td class="n">0</td></tr>
              <tr><td>retry 횟수</td><td class="n">1</td><td class="n">1</td><td class="n">0</td></tr>
              <tr><td>keyword 폴백률</td><td class="n">100.00%</td><td class="n">15.00%</td><td class="n up">−85.00%p</td></tr>
            </tbody>
          </table>
        </div>
        <div class="card warn grow" style="padding:16px 20px">
          <p><strong>한계도 그대로:</strong> 데이터 확장(6→12)은 분류 정확도를 0 올렸다
            (base 34/40 ≡ extended 34/40). 바뀐 건 조사 커버리지(unknown 18.75% → 0%).
            margin 게이트는 2문항을 아꼈다.</p>
          <p style="font-size:14px;color:var(--faint);margin-top:6px">
            근거 화면·원본: doc/reports/evidence/before_after.md</p>
        </div>
      </div>
    </div>
  </div>
  <div class="foot"><span class="who">결과 — artifacts/runs/ · doc/reports/evidence/before_after.md</span><span>4</span></div>
</section>
"""


def slide_graph() -> str:
    return """
<section class="slide">
  <div class="kicker"><span class="tag">3분</span>Agent Graph 구성<span class="rule"></span></div>
  <h2>그래프는 그대로 — 판정 한 줄만 갈아끼웠다</h2>
  <div class="lead">route → plan → gate → research → <strong>replan_check</strong> → analysis → write → validate → finalize.
    <strong>replan_check</strong>가 런북을 추가로 조회하는 지점이고, 그 판단을 RAG로 바꿨다.</div>
  <div class="body">
    <div class="shot" style="max-height:276px">
      <img src="{{IMG}}/05_architecture_graph.jpg" alt="Agent Graph와 MCP·RAG 구성">
      <div class="cap">FastAPI 프로세스(:8100) 안의 그래프 · MCP ops 서버(stdio) · RAG 인덱스와 임베더 · 평가 하네스</div>
    </div>
    <div class="row">
      <div class="card grow"><h3>왜 그 지점인가</h3>
        <p>판정을 바꾸면 <strong>런북 조회</strong>와 <strong>답변 작성</strong>이 같이 바뀐다.
          근거를 남기지 않으면 이유를 설명할 수 없다.</p></div>
      <div class="card grow"><h3>근거를 남긴 곳</h3>
        <p><code>/health.rag</code> · <code>/chat</code> metadata ·
          SSE <code>ReplanCheck</code> — 어떤 런북을 골랐는지, 점수와 1·2위 격차가 그대로 보인다.</p></div>
    </div>
  </div>
  <div class="foot"><span class="who">그래프 — agent/graph.py::_select_incident_type() · replan_check_node</span><span>5</span></div>
</section>
"""


def slide_rag() -> str:
    return """
<section class="slide">
  <div class="kicker"><span class="tag">3분</span>RAG 코드<span class="rule"></span></div>
  <h2>임베딩 검색 + 확신 없으면 기존 경로로</h2>
  <div class="body">
    <div class="row grow">
      <div class="col grow" style="flex:0 0 560px">
        <pre><span class="c"># agent/rag/classifier.py — 판정 5분기</span>
<span class="k">if</span> not enabled:            → <span class="s">keyword</span>
<span class="k">if</span> index is None:            → <span class="s">keyword</span>
vector = embedder.embed([text])[0]
top1, top2 = index.search(vector)
<span class="k">if</span> top1 &lt; min_score:      → <span class="s">keyword</span>  <span class="c">(0.50)</span>
<span class="k">if</span> top1-top2 &lt; min_margin: → <span class="s">keyword</span>  <span class="c">(0.03)</span>
<span class="k">return</span> top1                    <span class="s"># rag</span></pre>
        <div class="card soft" style="padding:14px 18px">
          <p><strong>입력 4블록</strong> — [사용자 질문][시스템][상태][알림].
            질의문을 넣는 이유는 기존 오분류 2개가 "질의를 안 본 것"이었기 때문.</p>
        </div>
      </div>
      <div class="col grow">
        <div class="shot">
          <img src="{{IMG}}/03_screen_rag_evidence.jpg" alt="RAG 판정 근거 SSE 출력">
          <div class="cap">실제 SSE 출력 — classifier_source=rag · rag_score=0.6452 · rag_margin=0.2177</div>
        </div>
        <div class="card good" style="padding:14px 18px">
          <p><strong>게이트가 안전장치다.</strong> RAG가 확신하지 못하면 예전 경로로 내려간다.
            그래서 기존 동작이 깨지지 않는다는 걸 숫자로 확인할 수 있었다.</p>
        </div>
      </div>
    </div>
  </div>
  <div class="foot"><span class="who">RAG — agent/rag/{embedder,index,classifier}.py</span><span>6</span></div>
</section>
"""


def slide_mcp() -> str:
    return """
<section class="slide">
  <div class="kicker"><span class="tag">3분</span>MCP 코드<span class="rule"></span></div>
  <h2>조회는 MCP로, 데이터 선택은 한 곳에서</h2>
  <div class="body">
    <div class="row grow">
      <div class="col grow" style="flex:0 0 560px">
        <pre><span class="c"># mcp_server.py — ops 서버</span>
<span class="k">@mcp.tool</span>     get_monitoring_status(system_name)
<span class="k">@mcp.resource</span> get_incident_runbook(incident_type)
<span class="k">@mcp.prompt</span>   incident_analysis_prompt(system, symptom)

<span class="c"># agent/data_profile.py — 파일 선택의 단일 지점</span>
DATA_PROFILE = base | extended   <span class="c"># 6시스템 | 12시스템</span></pre>
        <div class="card warn" style="padding:14px 18px">
          <p><strong>경로가 다섯 곳에 흩어져 있으면</strong> 시스템만 늘고 실제로 조사하는 대상은
            여섯 개로 잘린다 — 이름만 늘고 조사는 그대로인 "가짜 확장"이 된다.</p>
        </div>
      </div>
      <div class="col grow">
        <ul>
          <li><strong>Tool / Resource / Prompt</strong> 를 구분해 쓴다
            <span class="where">모니터링 조회 · 런북 본문 · 분석 절차</span></li>
          <li><strong>stdio subprocess</strong> 로 붙는다
            <span class="where">agent/mcp_client.py — list → find → read 순서로 탐색</span></li>
          <li><strong>decoy 서버는 쓰지 않는다</strong>
            <span class="where">mcp_server_docs.py — 쓰지 않음이 설계 의도</span></li>
          <li><strong>RAG는 의존성 주입</strong>
            <span class="where">SupervisorDeps.rag — 노드가 환경변수를 직접 읽지 않는다</span></li>
          <li><strong>LangSmith</strong> 트레이싱 경로 확보
            <span class="where">노드에 @traceable — 실 API 키 없는 환경이라 캡처는 못 했다</span></li>
        </ul>
      </div>
    </div>
  </div>
  <div class="foot"><span class="who">MCP — mcp_server.py · agent/mcp_client.py · agent/data_profile.py · agent/deps.py</span><span>7</span></div>
</section>
"""


def slide_end() -> str:
    return """
<section class="slide">
  <div class="kicker">마무리<span class="rule"></span></div>
  <h2>판정을 바꾼 게 아니라,<br>판단의 근거를 남기고 측정할 수 있게 바꾼 것</h2>
  <div class="body">
    <div class="row">
      <div class="card grow stat"><span class="v">0.3250 → 0.8500</span>
        <span class="l">40문항 분류 정확도</span></div>
      <div class="card grow stat"><span class="v good">0.2836 → 0.8521</span>
        <span class="l">macro-F1</span></div>
      <div class="card grow stat"><span class="v">3/10 → 10/10</span>
        <span class="l">회귀 질의 (매뉴얼 9쪽)</span></div>
    </div>
    <div class="row grow">
      <div class="card grow">
        <h3>배운 점</h3>
        <ul>
          <li>RAG의 핵심은 임베딩보다 <strong>입력 정의와 게이트</strong>였다</li>
          <li>"개선"이라고 말하려면 <strong>기준선을 먼저</strong> 재야 한다</li>
          <li>근거를 화면에 남기면 <strong>설명하지 않아도 확인</strong>된다</li>
        </ul>
      </div>
      <div class="card grow">
        <h3>다음에 하고 싶은 것</h3>
        <ul>
          <li>실제 장애 티켓으로 라벨 세트 재구축 (지금은 자기 평가)</li>
          <li>LLM-as-judge 평가 추가 · Research 서브그래프 분리</li>
          <li>실 OpenAI 백엔드로 비용·지연 재측정</li>
        </ul>
      </div>
    </div>
  </div>
  <div class="foot"><span class="who">github.com/pigpgw/skala-ai-service-mini · 근거 doc/reports/evidence/index.md</span><span>8</span></div>
</section>
"""


SLIDES = [slide_cover, slide_problem, slide_changes, slide_results,
          slide_graph, slide_rag, slide_mcp, slide_end]

DOC_TEMPLATE = """<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<title>{title}</title>
<style>{css}</style>
</head>
<body>
{body}
</body>
</html>
"""

SLIDE_TEMPLATE = """<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<title>{title}</title>
<style>{css}</style>
</head>
<body style="background:#fff">
{slide}
</body>
</html>
"""


def build_html() -> Path:
    body = "\n".join(fn().replace("{{IMG}}", "images") for fn in SLIDES)
    out = REPORTS / "presentation.html"
    out.write_text(DOC_TEMPLATE.format(
        title="Base AI Agent의 RunBook 선택 개선 — 발표자료",
        css=CSS, body=body), encoding="utf-8")
    return out


def build_slide_files() -> list[Path]:
    SLIDES_DIR.mkdir(parents=True, exist_ok=True)
    for old in SLIDES_DIR.glob("slide-*.html"):
        old.unlink()
    files = []
    for index, fn in enumerate(SLIDES, 1):
        path = SLIDES_DIR / f"slide-{index:02d}.html"
        path.write_text(SLIDE_TEMPLATE.format(
            title=f"slide {index}", css=CSS,
            slide=fn().replace("{{IMG}}", "../images")), encoding="utf-8")
        files.append(path)
    return files


def build_pdf(html_path: Path) -> Path | None:
    chrome = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
    if not Path(chrome).exists():
        return None
    out = REPORTS / "presentation.pdf"
    subprocess.run([
        chrome, "--headless=new", "--disable-gpu", "--no-first-run",
        "--user-data-dir=/tmp/archify-pdf-profile",
        f"--print-to-pdf={out}", "--no-pdf-header-footer",
        f"file://{html_path}",
    ], check=False, capture_output=True)
    return out if out.exists() else None


def main() -> int:
    parser = argparse.ArgumentParser(description="발표 덱 빌더")
    parser.add_argument("--only", default="all",
                        choices=["all", "html", "pptx", "pdf"])
    args = parser.parse_args()

    html_path = build_html()
    print(f"saved: {html_path.relative_to(REPO_ROOT)}")

    slide_files = build_slide_files()
    print(f"saved: {len(slide_files)}개 슬라이드 HTML → {SLIDES_DIR.relative_to(REPO_ROOT)}")
    if args.only == "html":
        return 0

    if args.only in {"all", "pdf"}:
        pdf = build_pdf(html_path)
        if pdf:
            print(f"saved: {pdf.relative_to(REPO_ROOT)}")

    if args.only in {"all", "pptx"}:
        cmd = [sys.executable, str(REPO_ROOT / "doc" / "tools" / "html2pptx_deck.py"),
               "--slides-dir", str(SLIDES_DIR),
               "--out", str(REPORTS / "presentation.pptx")]
        result = subprocess.run(cmd, cwd=REPO_ROOT)
        return result.returncode
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
