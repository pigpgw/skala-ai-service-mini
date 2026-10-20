# 평가 항목 체크리스트 (AI 서비스 Mini-Project)

- 근거: `../AI 서비스 Mini-Project.pdf` (14쪽), `../스크린샷 2026-10-20 오전 11.15.14.png`
- 대상: `all_total_vue_student` (FastAPI + LangGraph + MCP 인시던트 대응 에이전트)
- 배점: 100점 + 보너스 10점
- 갱신 규칙: 상태는 **증거를 확인한 뒤에만** 바꾼다. 측정하지 않은 수치는 쓰지 않는다.

## 상태 표기

- `[ ]` 미착수 · `[~]` 진행중 · `[x]` 검증 완료(증거 경로 있음) · `[!]` 막힘(원인 기록)

---

## 0. 최종 상태 요약 (2026-10-20)

| 항목 | 상태 |
|---|---|
| 구현 | 0~4단계 완료 — RAG RunBook 선택 · 데이터 확장(12시스템/10런북) · 평가 하네스 |
| 코드 | `main` = `origin/main`, 작업 트리 clean, 커밋 파일 141개 / 5.5MB |
| 측정 | 40문항 0.3250 → 0.8500, macro-F1 0.2836 → 0.8521, E2E 1/5 → 5/5, 재현성 identical |
| 검증 | 테스트 50개 통과 · 수치 일치 검사 13/13 · E2E 5건 PASS · 프로파일 3건 PASS |
| 산출물 | 보고서(MD·PDF) · 발표자료(HTML·PDF·PPTX·구성안) · 스프레드시트 본문 · 아키텍처 · 리허설 기록 (색인: `doc/reports/index.md`) |
| 남은 일 (사용자 몫) | ① 스프레드시트 붙여넣기 + 보고서 주소 등록 ② 말하기 리허설 1회 |

---

## 1. 일정과 제출 (PDF 3쪽)

Day1 = 2026-10-20, Day3 = 2026-10-22. 등록처는 Google Spread `https://shorturl.at/UfFvw` (소속반 UID·성함 먼저 작성).

| # | 기한 | 할 일 | 등록/제출처 | 상태 |
|---|---|---|---|---|
| S1 | Day1 10/20 09–10시 | Base AI Agent 프로그램·과제 설명 | – | [x] 참석 |
| S2 | Day1 10/20 ~17:00 | 과제 선택(1번/2번 중 택1) 등록 | Google Spread | [x] 2026-10-20 등록 |
| S3 | Day1 10/20 ~17:00 | 진행 계획(초안) 등록 — 진행 중 수정 가능 | Google Spread | [x] 2026-10-20 등록 |
| S4 | Day3 10/22 ~14:00 | 계획을 반영한 구현 | – | [x] 0~4단계 구현 완료 |
| S5 | Day3 10/22 ~14:00 | Git 주소 등록 | Google Spread | [x] `https://github.com/pigpgw/skala-ai-service-mini` |
| S6 | Day3 10/22 ~14:00 | 결과 보고서 작성 + 보고서 주소 등록 | Google Spread | [~] 초안 완료(Google Spread 등록·주소 입력 필요) |
| S7 | Day3 10/22 17:30 | 개인별 결과 보고서 발표 (Zoom, 반별 자율 진행) | Zoom | [ ] |

- **S2·S3 등록 완료 (2026-10-20, 사용자 보고)**: 소원 `G079 박건우`, 과제 `1`,
  등록 문구 "RAG 기반 RunBook 선택 · 데이터 확장 · 평가 하네스 구축".
  3절의 진행 계획 초안이 이 문구에 대응한다. (등록 캡처 이미지는 미첨부 — 스프레드시트 확인 필요)
- **S5 Git 주소**: `https://github.com/pigpgw/skala-ai-service-mini`.
  2026-10-20 확인 — `origin`이 이 주소로 설정돼 있고 `main`이 `origin/main`과 동일한 커밋에 있다.
  0~4단계 변경은 아직 커밋 전이다(§8 참고).
- S3은 진행 중 수정이 가능하다(PDF 3쪽). 4단계까지 구현했으므로 3절 표를 실제 수치로 갱신해 재등록하면 된다.

---

## 2. 선택한 과제

| 항목 | 내용 |
|---|---|
| 선택 | **1번 — Base AI Agent 기능 개선/추가** |
| 대상 | `all_total_vue_student` 기존 코드 (FastAPI + LangGraph v2 + MCP 2서버) |
| 제약 | 기능 개선·추가에 제약 없음. AI 도구 사용 제약 없음 |
| 필수 조건 | **작성한 코드와 내용을 설명할 수 있어야 함** → 발표에서 개선 지점마다 코드 위치를 말할 수 있어야 한다 |

---

## 3. 진행 계획 초안 (Google Spread 등록용 형식)

PDF 11–12쪽 양식: `순번 | 영역 | 무엇을 바꾸나 | 추가설명`

| 순번 | 영역 | 무엇을 바꾸나 | 추가설명 | 측정 지표 | 상태 |
|---|---|---|---|---|---|
| 1 | RAG | RunBook 선택을 키워드 첫 매칭 → runbook 임베딩 의미 검색으로 교체 | 입력 = 질문+시스템+상태+알림. top1 score·margin 미달 시 기존 keyword로 폴백. `RAG_ENABLED`로 같은 코드에서 A/B. **1·2단계 완료** — `agent/rag/` + `deps.rag` + `/health`·metadata·SSE 노출 | Top-1 정확도, macro-F1, fallback rate, 분류 p50/p95 | [x] |
| 2 | 데이터 보강 | 시스템 6→12, runbook 6→10, 신규 incident_type 4종 | 신규 타입: `connection-pool`, `cert-expiry`, `replication-lag`, `queue-backlog`. `data/monitoring.json` 보존 + `monitoring_extended.json` 신규, `DATA_PROFILE=base|extended` | 12시스템 조회 성공, 신규 4타입 top-1 선택 | [x] |
| 3 | 평가 | 평가 하네스 + 단위·통합 테스트 | `eval/run_eval.py` 통합(실행 1회 = `artifacts/runs/<run_id>/`, manifest·metrics·jsonl), `eval/metrics.py`(macro-F1·혼동행렬), `tests/` 50개(unit·integration), `doc/reports/evidence/` 대조표 | accuracy, macro-F1, 지연 p50/p95, retry, cost_usd | [x] |

확정된 설계 값:

| # | 정할 것 | 내용 |
|---|---|---|
| P1 | 현재 병목(코드 근거) | `agent/graph.py:192-202` 키워드 **첫 매칭** — 규칙 순서(latency→pool→cpu→memory→timeout→network→disk)가 증상 우선순위와 무관. `graph.py:206-209`는 질의문을 보지 않고 collected만 읽음. `graph.py:213` 매칭 실패 시 무조건 `db-down`. → 기준선 12문항 **8/12 = 0.6667**, 오분류 `B07·B09·B10·B11` (`eval/baseline_keyword.json`) |
| P2 | 개선안 한 문장 | `replan_check_node`의 runbook 선택을 runbook 임베딩 의미 검색으로 교체하고, score/margin 미달 시 기존 keyword로 폴백 |
| P3 | 비교 지표와 측정 방법 | Top-1 정확도·macro-F1(40문항), fallback rate, 분류 p50/p95, E2E 지연·retry·cost_usd. Before/After는 `RAG_ENABLED`만 다르게 2회 |
| P4 | 동일 입력 데이터셋 | `doc/regression_test_queries.md` 10개(E2E) + `eval/baseline_labels.json` 12문항(분류, 동결) + 확장 40문항 |
| P5 | 성공 판정 기준(수치) | 12문항 정확도 0.6667 초과, 40문항에서 keyword 대비 accuracy·macro-F1 모두 개선, 폴백률·지연은 원본 기록 |

PDF 11–12쪽에 제시된 개선 예시(채택 여부 미정, 후보 풀):

| # | 영역 | 예시 |
|---|---|---|
| E1 | RAG | 키워드 기반 incident_type 매핑 → runbook 사전 임베딩 + 의미 기반 검색 |
| E2 | 모듈화 | 단일 파일 graph 노드를 별도 모듈로 분리 |
| E3 | 그래프 개선 | research 노드를 로그/메트릭/런북 3개 서브에이전트로 분리(멀티 에이전트) |
| E4 | 그래프 개선 | 위험 조치 응답 전 `interrupt()` 승인 노드(HITL) 삽입 |
| E5 | 메모리 | 10턴 이상 대화 요약 압축 → 토큰·컨텍스트 비용 실측 비교 |
| E6 | 평가 | 키워드 매칭 평가에 LLM-as-judge(수치 인용 정확성) 추가 |
| E7 | 하드코딩 | Prompt 조회·Target System 디폴트 하드코딩 개선 |
| E8 | 데이터 보강 | incident_type 등 샘플 데이터 확장 |

- E7의 "시스템명 하드코딩"은 이미 일부 수정된 흔적이 있다(`doc/regression_test_queries.md`가 그 검증 목록). 착수 전 현재 코드 기준으로 남은 하드코딩을 다시 확인해야 한다.

---

## 4. 평가표 대응 (PDF 13쪽)

| 평가 항목 | 배점 | 평가 기준 | 완료 판정(증거) | 검증 명령 | 상태 |
|---|---|---|---|---|---|
| 기능 구현 완성도 | 30 | 선택한 개선안이 실제로 동작하는가 | 개선 후 실제 요청·응답 기록 1건 이상 | `curl :8100/health`, `curl :8100/version`, `:8600` 채팅 1회 | [x] `eval/e2e_probe_final.json` 5개 체크 PASS, 시연 캡처 3장 |
| Before/After 실측 비교 | 10 (보너스) | 같은 입력으로 개선 전/후를 돌려 수치로 차이 제시 | before/after 결과 2개 + 비교표 | 두 실행의 결과 파일 대조 | [x] `artifacts/runs/` 4개(분류 2 + E2E 2), `doc/reports/evidence/before_after.md` |
| 기술 요소 반영 | 30 | Multi-Agent, MCP, RAG, 의존성 주입, LangSmith, 모듈화, 단위 테스트 | 항목별 코드 위치 1줄 + 테스트 실행 결과 | `pytest -q` | [x] `agent/rag/`, `agent/deps.py`, `agent/graph.py`, `tests/` 50개 통과 |
| 한계·트레이드오프 설명 | 20 | 개선이 새로 만든 약점을 스스로 짚었는가 | 부작용 + 그 부작용의 수치 | 보고서 수치 = 측정 원본 | [x] 6장 4행(커버리지 비용·margin 2문항·자기평가 라벨 등) |
| 발표 PPT 작성·발표 | 20 | 문제 → 개선 포인트 → Before/After 수치 → 한계·추가 개선 순서 | PPT/PDF 백업 + 리허설 1회 | 파일 열어 순서 확인 | [~] PPT·PDF·구성안 완성, 리허설만 남음 |

### 기술 요소 현재 상태 (코드 확인 기준)

| 기술 요소 | 현재 확인된 사실 | 상태 |
|---|---|---|
| Multi-Agent / LangGraph | `agent/graph.py` StateGraph, `agent/supervisor_v1.py` | [x] 코드 있음 |
| MCP | `mcp_server.py`(ops), `mcp_server_docs.py`(decoy), `agent/mcp_client.py` | [x] 코드 있음 |
| 의존성 주입 | `agent/deps.py`, `server.py:63` lifespan에서 번들 1회 생성 | [x] 코드 있음 |
| 모듈화 | `agent/` 하위 llm·graph·mcp·retry 분리 | [x] 코드 있음 |
| LangSmith | `.env.example`의 `LANGCHAIN_TRACING_V2`·`LANGCHAIN_PROJECT`, `agent/graph.py` 노드에 `@traceable` | [~] 실 API 키 없는 환경이라 trace 캡처는 미수행(연결만 확인) |
| RAG | `agent/rag/` — `embedder.py`(Ollama/Hashing), `index.py`(JSON 캐시·무효화), `classifier.py`(5분기+폴백). `deps.rag`로 주입, `graph.py::_select_incident_type`에서 호출 | [x] 2단계 E2E 검증 (`eval/e2e_probe.json`) |
| 단위 테스트 | `tests/unit/` 5종 + `tests/integration/` 2종, `pytest.ini`, `requirements-dev.txt` | [x] 50개 통과 |

---

## 5. Before / After 실행 기록

동일 입력 = `doc/regression_test_queries.md`의 고정 질의 세트(PDF 9쪽: `regression_test_queries.md` 참조). before/after 모두 같은 세트, 같은 백엔드(`fake`/`ollama`/`openai`), 같은 조건에서 실행한다.

| 구분 | 실행 일시 | 백엔드 | 입력 | 결과 경로 | 지표 요약 |
|---|---|---|---|---|---|
| before | 2026-10-20 | `fake` | 분류 12문항 (`eval/baseline_labels.json`) | `eval/baseline_keyword.json` | 8/12 = 0.6667 |
| after | 2026-10-20 | `fake` + `ollama:qwen3-embedding:0.6b` | 분류 12문항 (동일) | `eval/rag_probe.json` | 12/12 = 1.0000 (RAG 10, 폴백 2) |
| E2E before | 2026-10-20 | `fake`, `RAG_ENABLED=false` | E2E 3문항 (`eval/run_e2e_probe.py`) | `eval/e2e_probe_rag_off.json` | 1/3 (E01·E02 오분류) |
| E2E after | 2026-10-20 | `fake`, `RAG_ENABLED=true` | E2E 3문항 (동일) | `eval/e2e_probe.json` | 3/3, SSE ReplanCheck에 근거 노출 |
| 40문항 before | 2026-10-20 | `fake`, `DATA_PROFILE=extended` | 분류 40문항 (`eval/labels_extended.json`) | `eval/baseline_extended_keyword.json` | 13/40 = 0.3250 |
| 40문항 after | 2026-10-20 | `fake` + qwen3-embedding, `DATA_PROFILE=extended` | 분류 40문항 (동일) | `eval/rag_probe_extended.json` | 34/40 = 0.8500 |
| ablation | 2026-10-20 | 위 3군 + base | 40문항 (동일) | `eval/ablation.json` | RAG +0.5250, 데이터 확장 정확도 0 / coverage 18.75%→0% |
| E2E 확장 | 2026-10-20 | `fake`, `DATA_PROFILE=extended` | E2E 4문항 (신규 시스템 포함) | `eval/e2e_probe_extended.json` | 4/4, `search-service` unknown 0 |
| 하네스 before | 2026-10-20 15:28 | `fake`, `DATA_PROFILE=extended` | 분류 40문항 (`eval/run_eval.py --variant before-rag`) | `artifacts/runs/20261020-152756_fake_before-rag/` | 13/40 = 0.3250, macro-F1 0.2836 |
| 하네스 after | 2026-10-20 15:28 | `fake` + qwen3-embedding, `DATA_PROFILE=extended` | 분류 40문항 (동일, `--repeat 2`) | `artifacts/runs/20261020-152756_fake_after-rag/` | 34/40 = 0.8500, macro-F1 0.8521, 재현성 identical |
| 하네스 E2E before | 2026-10-20 15:32 | `fake`, `RAG_ENABLED=false` | E2E 5문항 (`--mode e2e`) | `artifacts/runs/20261020-153204_fake_before-rag/` | 1/5 = 0.2000, p50 750.76ms |
| 하네스 E2E after | 2026-10-20 15:32 | `fake`, `RAG_ENABLED=true` | E2E 5문항 (동일) | `artifacts/runs/20261020-153211_fake_after-rag/` | 5/5 = 1.0000, p50 819.73ms |

| 지표 | before | after | 차이 | 측정 조건 |
|---|---|---|---|---|
| 정확도 | 8/12 = 0.6667 | 12/12 = 1.0000 (RAG 10/12, 폴백 2/12) | +0.3333 | 12문항 동결, `RAG_MIN_SCORE=0.50`, `RAG_MIN_MARGIN=0.03`, `ollama:qwen3-embedding:0.6b` (`eval/rag_probe.json`) |
| 정확도(확장) | 13/40 = 0.3250 | 34/40 = 0.8500 | +0.5250 | 40문항 동결, `DATA_PROFILE=extended`, 10문서 인덱스 `bfdc27ec…` (`eval/ablation.json`) |
| macro-F1(40문항) | 0.2836 | 0.8521 | +0.5685 | 하네스 4단계, `artifacts/runs/20261020-152756_fake_{before,after}-rag/metrics.json` |
| 조사 커버리지 | unknown 18.75% (base 6) | unknown 0% (extended 12) | −18.75%p | 같은 40문항이 조회한 80회 기준 (`eval/ablation.json` coverage) |
| 폴백률(keyword로 내려간 비율) | 100.00% | 15.00% | −85.00%p | 하네스 4단계, 동일 40문항 (`metrics.json`의 `fallback`) |
| 분류 지연 p50 | 0.0ms (keyword — 0.01ms 미만이라 반올림 0) | 32.43ms (RAG 임베딩 1회) | +32.43ms | 하네스 4단계, 동일 40문항 (`metrics.json`의 `latency`) |
| E2E 요청 지연 p50 | 750.76ms | 819.73ms | +68.97ms | 실서버 :8100, `fake`, E2E 5문항 (`metrics.json`의 `latency`) |
| 비용(호출·토큰) | $0.000000 (로컬 fake·ollama) | $0.000000 (로컬 fake·ollama) | 0 | E2E 응답의 `cost_usd` 합계. 실 API 비용은 `LLM_BACKEND=openai` 실행 때만 발생 |
| retry 횟수 | 1 (MCP 최초 호출 지연 시뮬레이션) | 1 (동일) | 0 | `agent/mcp_client.py`의 Wave 9 첫 호출 실패 → 재시도 1회 |
| 재현성 | — | 동일 조건 2회 반복 결과 동일 (`identical=true`) | — | `--repeat 2`, `metrics.json`의 `reproducibility` |
| 자동 테스트 | — | 50개 통과 (unit·integration) | — | `.venv/bin/python -m pytest` (2026-10-20) |

- 실행 순서(PDF 5쪽): `bash sh/setup_venv.sh` → `bash sh/setup_ollama.sh` → `bash sh/run_agent_ollma.sh` → `bash sh/run_frontend.sh`. 개발 정리 후 `run_agent_openai.sh`(과금)로 실제 API 테스트.
- 세션 기억 질의(#10)는 서버 재시작 여부까지 조건에 적는다.

---

## 6. 한계·트레이드오프

개선이 새로 만든 약점만 적는다. 개선 전부터 있던 문제는 여기 쓰지 않는다.

| 개선 | 새로 생긴 약점 | 근거(수치·코드) | 완화책 |
|---|---|---|---|
| RAG 분류 도입 | 질의 1회 임베딩이 분류 단계에 추가된다 | `eval/rag_probe.json` items `elapsed_ms` (B01 616ms 최초 호출, 이후 32~55ms) | 인덱스는 기동 시 1회, 질의 임베딩만 요청당 1회. p50/p95는 4단계에서 정식 측정 |
| RAG 분류 도입 | 작은 코퍼스(6~10종)라 top1·top2 차이가 좁아 margin 판정이 흔들린다 | `eval/rag_threshold_sweep.json` — margin 0.01~0.03 구간에서 RAG 판정 11→10건으로 바뀜 | margin 미달 시 keyword 폴백, 폴백률을 지표로 감시 |
| RAG 분류 도입 | 임베딩 모델이 없으면 `HashingEmbedder`로 떨어져 품질이 급락한다 | `agent/rag/embedder.py::build_embedder` — auto 모드에서 조용히 대체 | `/health.rag.embedder`·인덱스 `embedder.name`에 실제 사용값 기록, 폴백 시 `offline` 표시 |
| RAG 분류 도입 | 12문항 100%는 개발셋 수치다 | `eval/rag_probe.json` — 라벨을 먼저 동결한 뒤 meta를 작성했지만 표본이 작다 | 확장 40문항(3단계)으로 재측정, 일반화 주장 금지 |
| 데이터 확장 | 확장이 **분류 정확도는 올리지 못했다** | `eval/ablation.json` B=C=34/40 (문항 단위 동일). RAG가 질의 텍스트로 증상을 읽기 때문에 시스템 알림이 중복 신호였다 | 효과를 coverage(unknown 18.75%→0%)와 신규 4유형 지원으로 서술. "확장으로 정확도 상승"이라고 쓰지 않는다 |
| margin 게이트 | 보수적 폴백 비용 2문항 (40문항 기준 34 vs 36) | `eval/rag_threshold_sweep_extended.json` — margin 0.00에서 X24·X32가 RAG로 넘어가 정답. 두 문항 차이는 0.0155·0.0000 | 게이트를 없애면 1단계 B01형 오답이 재발. 0.03 유지하고 비용을 기록 |
| 40문항 라벨 | 20/40이 ambiguous·no_system = 질의 텍스트 의존 | `eval/labels_extended.json` design_notes — 두 카테고리의 정답은 "사용자 신고 증상" 기준 | 카테고리별 정확도를 따로 보고, 전체 수치로 일반화하지 않는다 |

---

## 7. 발표 (PDF 3쪽, 13쪽)

- [x] 문제 정의 (개선 전 무엇이 틀렸는가) — 슬라이드 2·3, 근거 `eval/baseline_keyword.json` (8/12)
- [x] 개선/추가 포인트 (무엇을 어떻게 바꿨는가) — 슬라이드 4·5·6, 코드 위치 표는 보고서 2절
- [x] Before/After 수치 (표 그대로) — 슬라이드 7, 원본 `doc/reports/evidence/before_after.md`
- [x] 한계와 추가 개선 사항 — 슬라이드 8·9, 보고서 5절
- [x] 코드 설명 준비 — 슬라이드 4·5·6에 파일·함수 위치 표시 (`agent/rag/*`, `agent/graph.py::_select_incident_type`, `agent/data_profile.py`, `eval/run_eval.py`)
- [x] PPT/PDF 백업 — `doc/reports/presentation.pptx`·`.pdf`, `skala-tasks/w14-ai-agent/`에 사본
- [~] Zoom 발표 리허설 — **기계가 확인 가능한 부분 완료**: 수치 일치 검사 13/13(`eval/check_reported_numbers.py`),
  시연 4단계 실측(총 3초·결과 확인), 발표물 파일 점검. 기록은 `doc/reports/rehearsal_log.md`.
  남은 건 **말하기 리허설 1회**(사람) — 절차는 `doc/reports/presentation_outline.md` '리허설 체크리스트'

---

## 8. Git·제출물

| # | 요건 | 현재 상태 | 상태 |
|---|---|---|---|
| G1 | Git 주소 등록(S5) | `https://github.com/pigpgw/skala-ai-service-mini` — `origin` 설정, `main` = `origin/main` (2026-10-20 확인) | [x] |
| G2 | 제출 코드가 현재 작업 트리와 일치 | 2026-10-20 커밋·푸시 완료(0~4단계 + 산출물 + 정리), `main` = `origin/main`, 작업 트리 clean | [x] |
| G3 | 결과 보고서(Google Spread) | 보고서 `doc/reports/result_report.md`(+PDF), **스프레드시트 입력용 본문 `doc/reports/spreadsheet_input.md`**, 발표자료 PDF·PPTX·구성안, 아키텍처 `doc/design/architecture.html`, 시연 캡처 3장, 리허설 기록 `doc/reports/rehearsal_log.md`. 제출 폴더 `skala-tasks/w14-ai-agent/`에 사본. **스프레드시트 붙여넣기·주소 등록은 사용자 몫(구글 시트에는 접근하지 않음)** | [~] |
| G4 | `.env`·`.venv`·`session.db` 미커밋 | `.gitignore`에 포함됨 | [x] |
| G5 | 생성물(원본 측정·런타임 상태) 미커밋 | `artifacts/`·`var/` 제외됨, `artifacts/README.md`만 예외 커밋 | [x] |

---

## 9. 진척 기록

| 날짜 | 한 일 | 확인한 증거 | 다음 한 단계 |
|---|---|---|---|
| 2026-10-20 | PDF 14쪽 재확인, 평가표·일정·제출 요건을 체크리스트로 통합 | PDF 3쪽 일정, 11–12쪽 계획 양식, `tests/`·`eval/`·`artifacts/` 없음, 원격 없음 | P1 병목 확정 → S2·S3 등록(17:00) |
| 2026-10-20 | 계층별 작업 규칙·문서 세팅 (루트 + `agent`·`sh`·`doc`·`data`) | `AGENTS.md` 5개, `README.md` 5개(루트·agent·sh·data 신규, `doc/README.md`는 기존 매뉴얼 유지) | 저장소 푸시 후 P1 병목 확정 |
| 2026-10-20 | **0단계 완료** — 과제 범위 확정(RAG + 데이터 보강 + 평가 하네스), 12문항 라벨 동결, keyword 기준선 측정 | `eval/common.py`, `eval/baseline_labels.json`, `eval/run_baseline.py`, `eval/baseline_keyword.json`(8/12), `eval/baseline_keyword.run2.json`(2회 실행 동일) | 1단계 RAG 부품(`agent/rag/embedder.py`→`index.py`→`classifier.py`) |
| 2026-10-20 | **1단계 완료** — RAG 부품 3종 + `meta.json` 6종. 12문항 8/12 → **12/12**(RAG 10, 폴백 2). 임계값 확정 0.50/0.03 | `agent/rag/{embedder,index,classifier}.py`, `data/runbooks/meta.json`(신규, 기존 파일 무변경), `eval/run_rag_probe.py`, `eval/rag_probe.json`, `eval/rag_probe.run2.json`, `eval/rag_threshold_sweep.json`, `doc/rag_design.md` §6.1·§9.1 | 2단계 `agent/graph.py`·`server.py` 연결 |
| 2026-10-20 | **2단계 완료** — `deps.rag` 주입, `_select_incident_type` 연결, `/health.rag`·`/chat` metadata·SSE `ReplanCheck`에 근거 노출. E2E 3/3, RAG off 시 1/3로 기준선 재현 | `agent/deps.py`, `agent/graph.py`, `server.py`, `eval/run_e2e_probe.py`, `eval/e2e_probe.json`, `eval/e2e_probe_rag_off.json`, `doc/rag_design.md` §9.2 | 3단계 데이터 확장(12시스템·10런북·신규 4타입) |
| 2026-10-20 | **3단계 완료** — 시스템 6→12, 런북 6→10, `DATA_PROFILE` 일원화(5곳 하드코딩 제거), 40문항 동결·측정. keyword 13/40 → RAG 34/40. 데이터 확장은 정확도 0·coverage 18.75%→0% | `agent/data_profile.py`, `data/monitoring_extended.json`, `data/runbooks/{connection-pool,cert-expiry,replication-lag,queue-backlog}.md`, `eval/labels_extended.json`, `eval/{baseline_extended_keyword,rag_probe_extended,rag_probe_extended_on_base,ablation,profile_probe}.json`, `doc/rag_design.md` §9.3 | 4단계 평가 하네스 정식화(`eval/run_eval.py`, macro-F1, 지연 p50/p95, 재현성) |
| 2026-10-20 | **4단계 완료** — 통합 하네스(`eval/run_eval.py`: manifest·metrics·requests/responses jsonl, 실행 1회=`artifacts/runs/<run_id>/`), 지표 모듈(`eval/metrics.py`), 테스트 50개(`tests/`), Before/After 표 자동 생성(`eval/make_before_after.py`) → `doc/reports/evidence/`. 40문항 0.3250→0.8500, macro-F1 0.2836→0.8521, E2E 1/5→5/5, 재현성 identical, 분류 지연 +32.43ms | `eval/run_eval.py`, `eval/metrics.py`, `eval/make_before_after.py`, `eval/e2e_cases.json`, `tests/{unit,integration}/`, `pytest.ini`, `requirements-dev.txt`, `artifacts/runs/20261020-1527*`, `artifacts/runs/20261020-1532*`, `doc/reports/evidence/{index.md,before_after.md,metrics/}`, `doc/rag_design.md` §9.4 | 0~4단계 변경 커밋·푸시 → S6 보고서 작성 |
| 2026-10-20 | **S2·S3·S5 확인** — 소원 G079 박건우, 과제 1번, 등록 문구 "RAG 기반 RunBook 선택 · 데이터 확장 · 평가 하네스 구축", Git 주소 `https://github.com/pigpgw/skala-ai-service-mini` | 사용자 등록 보고, `git remote -v`·`git ls-remote` 확인(origin = 해당 주소, `main` = `origin/main`) | 0~4단계 변경 커밋·푸시 → S6 보고서 |
| 2026-10-20 | **커밋·푸시 완료** — 0~4단계 6커밋(`923514e..4e7d752`), `main` = `origin/main`, 작업 트리 clean. 비밀·상태 파일 미포함 확인(`.env`·`session.db`·`.venv`·`artifacts/`·`var/` 전부 제외, `.env.example`만 존재) | `git push origin main` → `923514e..4e7d752 main -> main`, `git ls-remote origin` = `4e7d752` | S6 결과 보고서 작성(증거 대조표 `doc/reports/evidence/index.md` 인용) |
| 2026-10-20 | **제출 산출물 작성** — 결과 보고서(MD+PDF), 발표자료(슬라이드 10장 HTML·PDF·PPTX + 구성안), 아키텍처 다이어그램, 시연 캡처 3장. 스프레드시트 입력용으로 `skala-tasks/w14-ai-agent/`에 복사 | `doc/reports/{result_report.md,result_report.pdf,presentation*,images/}`, `doc/design/architecture.html`, `doc/tools/{md2html.py,build_pptx.py,capture_ui.mjs}`, `skala-tasks/w14-ai-agent/` | 스프레드시트에 보고서 본문·주소 입력 → 발표 리허설 |
| 2026-10-20 | **산출물·디렉토리 정리** — 조사 후 일괄 정리: 생성물 삭제(`.archify` 3.0M·`__pycache__`·`.pytest_cache`·`artifacts/captures`·중복 PDF·인덱스 캐시), 매뉴얼 이미지 PNG→JPEG 압축(5.2MB→1.6MB), 세션 DB를 `var/session.db`로 이동(P2), 배포 zip 제외 규칙 보강·재생성(5.2MB→1.9MB), 아키텍처 영수증 `artifacts/design/` 분리 | `doc/artifact_management_design.md` v0.3, `git status`, `unzip -l all_total_vue_student.zip`, 세션 저장소 재오픈 이력 확인, pytest 50개 통과 | 스프레드시트에 보고서 본문·주소 입력 → 발표 리허설 |
| 2026-10-20 | **최종 보완·마무리** — 루트 README를 개선 내용 기준으로 전면 개편, `sh/AGENTS.md`에 세션 DB 경로·zip 제외 규칙 기록, 스프레드시트 입력용 본문(`doc/reports/spreadsheet_input.md`)과 발표 리허설 체크리스트 추가, 제출 폴더 7개 파일 동기화. 정리 후 전 기능 재검증: 테스트 50개 통과·프로파일 검증 3건 PASS·E2E 5개 체크 PASS·분류 측정 동일 수치 재현(0.3250→0.8500, 재현성 identical) | `README.md`, `sh/AGENTS.md`, `doc/reports/spreadsheet_input.md`, `doc/reports/presentation_outline.md`, `eval/e2e_probe_final.json` | 스프레드시트 붙여넣기·주소 등록 → 발표 리허설 |
| 2026-10-20 | **발표 리허설 검증(기계 가능 범위)** — `eval/check_reported_numbers.py`로 슬라이드·보고서·README·체크리스트에 적힌 수치 13개가 측정 원본과 일치하는지 대조(13/13 PASS). 검사 중 **원본 매핑 오류 1건**(extended coverage를 base 실행에서 읽음) 발견·수정, 폴백률 15.00% 표기 추가. 시연 4단계 실측(총 3초: high-latency·queue-backlog·billing-service 폴백) | `eval/check_reported_numbers.py`, `eval/reported_numbers_check.json`, `doc/reports/rehearsal_log.md`, `doc/reports/presentation.html`(슬라이드 8 수정) | 스프레드시트 붙여넣기·주소 등록 → 말하기 리허설 1회 |
