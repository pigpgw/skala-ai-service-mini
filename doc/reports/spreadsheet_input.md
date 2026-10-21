# Google Spread 입력용 — 결과 보고서 붙여넣기 본문

**79번 박건우** (G079 · 광주 3반) · 2026-10-21 · 과제 1번 — Base AI Agent 기능 개선/추가

아래 본문을 스프레드시트 셀에 그대로 붙여 넣는다. 긴 보고서는
`doc/reports/result_report.md`(PDF)를 링크로 함께 남긴다.

---

## 1. 진행 사항 소개

**선택 과제**: 1번 — Base AI Agent 기능 개선/추가
**대상 코드**: all_total_vue_student (FastAPI + LangGraph v2 + MCP 2서버 인시던트 대응 에이전트)
**Git 주소**: https://github.com/pigpgw/skala-ai-service-mini

### 추가·수정한 task 4개

1. RAG 기반 RunBook 선택 — 키워드 첫 매칭 → 런북 임베딩 의미 검색.
   확신이 없으면(min_score 0.50 / min_margin 0.03 미달) 기존 keyword 경로로 폴백.
   근거(유형·유사도·1·2위 격차)는 /health, /chat metadata, SSE ReplanCheck로 노출.
   코드: agent/rag/{embedder,index,classifier}.py, agent/graph.py::_select_incident_type()
2. 라우팅 기준 확대 — 결정론 백엔드의 라우팅 정규식이 키워드 7개뿐이라 PDF 9쪽 예시 질의 7개가
   chat으로 떨어져 장애 파이프라인이 돌지 않았다. 실제 LLM 백엔드와 같은 운영 어휘로 확대하고,
   시스템명이 언급되면 incident로 간다(목록에 없는 billing-service 포함).
   코드: agent/fake_llm.py::route
3. 데이터 확장 — 모니터링 6→12시스템, 런북 6→10종(신규 유형 queue-backlog·cert-expiry·
   connection-pool·replication-lag). 파일 선택은 agent/data_profile.py 한 곳에서만.
   기존 monitoring.json은 기준선으로 보존.
4. 평가 하네스 구축 — 실행 1회 = artifacts/runs/<run_id>/ 폴더 1개(manifest·metrics·jsonl),
   macro-F1·혼동행렬·지연 percentile 계산, 40문항 라벨 동결, 회귀 질의 10개 실행기,
   문서 수치 ↔ 원본 자동 대조(15/15), 테스트 65개.

### 개선 전에 무엇이 틀렸나

장애 유형 판정이 키워드 규칙을 순서대로 보다가 처음 맞는 것을 고르는 방식이었다.
규칙 순서가 증상 우선순위와 무관했고(CPU가 timeout보다 앞), 질의문을 보지 않았으며,
맞는 키워드가 없으면 무조건 db-down이었다. 기준선 측정 결과 12문항 중 4개 오분류(8/12 = 0.6667).

---

## 2. 사용한 기술 요소

| 기술 요소 | 구현 위치 | 상태 |
|---|---|---|
| Multi-Agent / LangGraph | agent/graph.py (StateGraph, 노드 10개), agent/supervisor_v1.py | 기존 활용 |
| MCP | mcp_server.py (Tool·Resource·Prompt), agent/mcp_client.py (stdio 클라이언트) | 기존 + 조회 경로 확장 |
| RAG | agent/rag/ — embedder·index·classifier, deps.rag 주입, graph.py::_select_incident_type() | 신규 |
| 의존성 주입 | agent/deps.py SupervisorDeps(rag 필드), server.py lifespan에서 1회 생성 | 확장 |
| LangSmith | graph.py 노드 @traceable, .env LANGCHAIN_TRACING_V2·LANGCHAIN_PROJECT | 연결·구성 완료 / 실 키 없는 환경이라 캡처 미수행 |
| 모듈화 | agent/ 하위 llm·graph·mcp·retry·rag·session_store, eval/, doc/tools/ | 확장 |
| 단위 테스트 | tests/unit 6종 + tests/integration 2종 | 신규 65개 |

### 화면 캡처 (첨부)

- 최종 실행 화면: doc/reports/images/01_chat_final_screen.jpg (조사 수집 → 장애유형 추가 조사 →
  대응 매뉴얼 조회 → 초안 → 검수 → 최종 답변)
- 기능 개선 화면: doc/reports/images/03_screen_rag_evidence.jpg (SSE로 나오는 RAG 판정 근거 —
  classifier_source=rag, rag_score=0.6452, rag_margin=0.2177)
- 신규 유형 화면: doc/reports/images/02_chat_new_incident_type.jpg (queue-backlog)
- Before/After 수치 화면: doc/reports/images/04_screen_before_after.jpg

---

## 3. 선택 사항 — Before / After 실측 비교

같은 입력, 같은 백엔드(fake), 같은 조건에서 2회 실행.
DATA_PROFILE=extended, 임베더 qwen3-embedding:0.6b, 임계값 0.50/0.03, 10문서 인덱스.

| 지표 | Before (keyword) | After (RAG) | 차이 |
|---|---|---|---|
| 40문항 분류 정확도 | 13/40 = 0.3250 | 34/40 = 0.8500 | +0.5250 |
| macro-F1 | 0.2836 | 0.8521 | +0.5685 |
| E2E 5문항 (실서버 :8100) | 1/5 = 0.2000 | 5/5 = 1.0000 | +0.8000 |
| 회귀 질의 10문항 (PDF 9쪽) | 3/10 | 10/10 | +0.7000 |
| 분류 지연 p50 | 0.0ms | 32.43ms | +32.43ms |
| E2E 요청 지연 p50 | 750.76ms | 819.73ms | +68.97ms |
| 비용 (USD, 로컬 백엔드) | $0.000000 | $0.000000 | 0 |
| retry 횟수 | 1 | 1 | 0 |
| 조사 커버리지 (unknown 비율) | 18.75% | 0.00% | −18.75%p |
| keyword 폴백률 | 100.00% | 15.00% | −85.00%p |

원본: artifacts/runs/ (20261020-152756_fake_before/after-rag, 153204/153211_fake_before/after-rag,
20261020-152800_fake_before/after-rag) · 요약본: doc/reports/evidence/metrics/ ·
대조표: doc/reports/evidence/index.md · 화면 캡처: doc/reports/images/04_screen_before_after.jpg

### 해석 (한계 포함)

- 데이터 확장(6→12시스템)은 분류 정확도를 올리지 못했다(base 34/40 ≡ extended 34/40).
  대신 40문항이 조회한 모니터링 80회 중 데이터가 없어 못 본 15회가 0회가 됐다(unknown 18.75% → 0%).
- margin 게이트는 2문항을 아꼈다(0으로 풀면 36/40). 그 2문항은 1·2위 유사도 차이가
  0.0155·0.0000인 동점이었고, 1단계에서 정답이 뒤집힌 사례도 이런 동점이었다.
- RAG의 비용은 임베딩 1회 호출이다(+32.43ms, 실서버 요청 시간의 약 9%).
- 40문항 라벨을 직접 만들어 자기 평가가 된다. 질의 의존도가 높은 20문항을 따로 두고
  카테고리별 정확자를 함께 냈다.
- keyword 경로에 남은 결함 1건: 회귀 #4(gateway 타임아웃 + payments CPU)는 규칙 순서로
  cpu-spike가 된다. RAG를 켜면 network-timeout으로 고쳐진다.

---

## 4. 느낀 점 / 이후에 반영하고 싶은 것

RAG는 임베딩보다 입력 정의(무엇을 넣을지)와 게이트(언제 믿고 언제 안 믿을지)와
근거 남기기(어떻게 보여줄지)가 핵심이었다. "확신하지 못하면 예전 경로로 내려간다"는
게이트 하나를 넣고 나서야 기존 동작이 깨지지 않는다는 걸 확신할 수 있었다.
개선을 말하려면 기준선을 먼저 재는 것도 마찬가지였다.

이후에 하고 싶은 것: ① 실제 장애 티켓·운영 로그로 라벨 세트 재구축 ② LLM-as-judge 평가 추가
③ Research 서브그래프 분리(멀티에이전트화) ④ Human-in-the-loop 승인 노드(LangGraph interrupt)
⑤ 메모리 Context 압축(10턴 이상 요약) ⑥ 실 OpenAI 백엔드로 비용·지연 재측정

---

## 5. 참고 링크

- Git: https://github.com/pigpgw/skala-ai-service-mini
- 근거 대조표(수치 ↔ 원본 파일 ↔ 재현 명령): doc/reports/evidence/index.md
- 산출물 색인: doc/reports/index.md
- 아키텍처 다이어그램: doc/design/architecture.html
- 발표자료: doc/reports/presentation.pdf (PPTX 동봉), 구성안 doc/reports/presentation_outline.md
- 제출 전 확인: 테스트 65개 통과 · 수치 일치 검사 15/15 · E2E 5건 PASS · 회귀 10/10 · 같은 조건 2회 실행 결과 동일
