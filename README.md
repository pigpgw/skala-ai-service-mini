# skala-ai-service-mini

SKALA AI 서비스 Mini-project 과제 1번 — 기존 Base AI Agent(인시던트 대응 에이전트)를 개선하는 개인 과제 저장소다.
FastAPI(:8100) + LangGraph v2 + MCP 2서버 구조이고, 브라우저 채팅 화면은 Vue 3(CDN)다.
에이전트는 요청 한 건을 route → plan → gate → research → replan_check → analysis → write → validate → finalize 순서로 처리한다.

## 무엇을 개선했나

장애 질의가 들어오면 에이전트가 MCP로 모니터링 데이터를 조회하고, 장애 유형을 정해 대응 런북을 골라
답변을 만든다. 이때 **장애 유형을 고르는 부분**을 중심으로 세 가지를 손봤다.

| # | 개선 | 내용 |
|---|---|---|
| 1 | **RAG 기반 RunBook 선택** | 키워드 첫 매칭(`agent/graph.py::_classify_incident_type`) → 런북 임베딩 의미 검색(`agent/rag/`). 확신이 없으면 기존 keyword 경로로 폴백 |
| 2 | **데이터 확장** | 모니터링 시스템 6→12, 런북 6→10(신규 유형 4종). 파일 선택은 `agent/data_profile.py` 한 곳에서만 |
| 3 | **평가 하네스** | 실행 1회 = `artifacts/runs/<run_id>/` 폴더 1개(`eval/run_eval.py`), 지표 모듈(`eval/metrics.py`), 테스트 50개(`tests/`) |

### 측정 결과 (같은 입력·같은 백엔드·같은 조건 2회 실행)

| 지표 | Before (keyword) | After (RAG) |
|---|---|---|
| 40문항 분류 정확도 | 13/40 = 0.3250 | **34/40 = 0.8500** |
| macro-F1 | 0.2836 | **0.8521** |
| E2E 5문항(실서버) | 1/5 = 0.2000 | **5/5 = 1.0000** |
| 분류 지연 p50 | 0.0ms | 32.43ms (임베딩 1회) |

원본은 `artifacts/runs/`, 주장↔증거 대조표는 `doc/reports/evidence/index.md`에 있다.
데이터 확장은 **분류 정확도를 올리지 못했다**(base 34/40 ≡ extended 34/40). 대신 조사 커버리지(unknown)가
18.75% → 0%로 줄었다. 이 한계도 수치 그대로 남겼다.

## 실행

```bash
bash sh/setup_venv.sh      # 최초 1회
bash sh/setup_ollama.sh    # 로컬 모델 준비
bash sh/run_agent_ollma.sh # 백엔드 기동 (:8100)
bash sh/run_frontend.sh    # 채팅 화면 (:8600)
```

자세한 사용법·캡처는 `doc/README.md`(메인 매뉴얼)와 `doc/manual_ollma.md`, `doc/manual_openai.md`를 본다.
실행 순서·비용·종료 방법은 `sh/README.md`에 정리돼 있다.

## 평가·검증

```bash
.venv/bin/python -m pytest                                   # 테스트 50개
.venv/bin/python eval/run_eval.py --variant before-rag --profile extended   # 기준선
.venv/bin/python eval/run_eval.py --variant after-rag  --profile extended --repeat 2
.venv/bin/python eval/make_before_after.py --pair <before> <after>          # 비교표 자동 생성
.venv/bin/python eval/check_reported_numbers.py                              # 문서 수치 ↔ 원본 일치 검사
```

측정 조건(백엔드·프로파일·임계값·데이터 해시·git 상태)은 실행마다 `artifacts/runs/<run_id>/manifest.json`에 남는다.

## 환경변수

| 변수 | 값 | 의미 |
|---|---|---|
| `LLM_BACKEND` | `fake`(기본) / `ollama` / `openai` | LLM 백엔드 |
| `SUPERVISOR_VERSION` | `v2`(기본) / `v1` | LangGraph v2 그래프 / legacy 선형 |
| `DATA_PROFILE` | `extended`(기본) / `base` | 모니터링 12시스템 / 6시스템 |
| `RAG_ENABLED` | `true`(기본) / `false` | RAG RunBook 선택 on/off (같은 코드에서 A/B) |
| `RAG_MIN_SCORE`, `RAG_MIN_MARGIN` | `0.50`, `0.03` | RAG 판정 하한·1·2위 격차 하한 (미달 시 keyword 폴백) |

## 폴더

| 폴더 | 내용 |
|---|---|
| `agent/` | LangGraph 그래프, LLM 백엔드 3종, MCP 클라이언트, 세션 저장소, `rag/`(E1) |
| `data/` | 입력 데이터 (`monitoring.json`, `monitoring_extended.json`, `runbooks/`) — 측정 기준선 |
| `eval/` | 평가 코드·동결 라벨·측정 원본 스냅샷 |
| `tests/` | unit 5종 + integration 2종 (50개) |
| `doc/` | 매뉴얼·설계·체크리스트·제출 산출물(`reports/`)·아키텍처(`design/`) |
| `sh/` | 실행 스크립트 |
| `artifacts/` | 측정 원본(커밋 안 함, 재생성 가능) |
| `var/` | 런타임 상태(세션 DB·로그) |

## 산출물

| 문서 | 내용 |
|---|---|
| `doc/reports/index.md` | 제출 산출물 색인 (무엇이 어디 있는지) |
| `doc/reports/result_report.md` (+PDF) | 최종 결과 보고서 |
| `doc/reports/presentation.html` (+PDF·PPTX) | 발표 슬라이드 10장, `presentation_outline.md`는 구성안·시간 배분·예상 질문·리허설 체크리스트 |
| `doc/reports/spreadsheet_input.md` | Google Spread 붙여넣기용 본문 |
| `doc/reports/rehearsal_log.md` | 리허설 기록 (수치 검사 13/13, 시연 실측) |
| `doc/design/architecture.html` | 개선 시스템 아키텍처 다이어그램 |
| `doc/reports/evidence/index.md` | 주장 ↔ 증거 ↔ 재현 명령 대조표 |
| `doc/rag_design.md` | RAG 설계·임계값 근거·측정 결과 |
| `doc/evaluation-checklist.md` | 평가 항목 진행 추적 (상태·증거 경로) |
| `doc/artifact_management_design.md` | 폴더·산출물 구조 설계와 실행 기록 |
| `doc/regression_test_queries.md` | Before/After 공통 입력 (고정 질의 세트) |
| `AGENTS.md` | 작업 규칙 (AI 에이전트·사람 공통 계약) |

Git: https://github.com/pigpgw/skala-ai-service-mini
