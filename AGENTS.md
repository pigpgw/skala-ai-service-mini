# AGENTS.md — 프로젝트 공통 계약

SKALA AI 서비스 Mini-project, **과제 1번(Base AI Agent 기능 개선/추가)** 개인 과제 저장소다.
대상 코드는 `all_total_vue_student` — FastAPI + LangGraph v2 + MCP 2서버 인시던트 대응 에이전트다.

## 규칙 우선순위

1. `/Users/baggeon-u/Desktop/skala/AGENTS.md` (SKALA 학습 운영 지침)
2. `/Users/baggeon-u/Desktop/skala/skala-tasks/AGENTS.md` (과제·보고서 작성 지침)
3. 이 문서 — 프로젝트 공통
4. 하위 폴더 `AGENTS.md` — 그 폴더에서만 다른 규칙. **깊은 쪽이 우선한다.**

현재 하위 문서: `agent/AGENTS.md`, `sh/AGENTS.md`, `doc/AGENTS.md`, `data/AGENTS.md`, `tests/AGENTS.md`

## 루트 진입점 (이동·이름 변경 금지)

| 경로 | 역할 |
|---|---|
| `server.py` | FastAPI 백엔드 (:8100) |
| `mcp_server.py` | MCP `ops` 서버 (Tool·Resource·Prompt 실사용) |
| `mcp_server_docs.py` | MCP `docs` 서버 (decoy — agent가 쓰지 않음) |
| `web_demo_server.py` | 정적 페이지 + `/chat` 프록시 (:8600) |
| `web_chat.html` | Vue 3 채팅 화면 (CDN, 빌드 없음) |
| `sh/*.sh` | 실행 스크립트 |

과제 매뉴얼(`doc/README.md`)과 배포 zip이 위 경로를 그대로 참조한다. `server.py`·`agent/`를 `src/`로 옮기지 않는다.

## 폴더 구조 (2026-10-20 기준)

`doc/artifact_management_design.md` 9장 P0·P3을 실행한 상태다. P1(이미지 이동)·P2(`session.db` → `var/`)는 **미실행**이다.

| 경로 | 역할 | 커밋 |
|---|---|---|
| `agent/`, `eval/`, `tests/` | 실행 코드·평가 코드·테스트 | O |
| `data/` | 측정 입력(기준선 포함) | O |
| `doc/` | 사람이 읽는 문서 | O |
| `doc/reports/` | 제출·발표 산출물(보고서·증거 대조표) | O |
| `artifacts/` | 측정 원본 — 실행 1회 = `artifacts/runs/<run_id>/` | X (README만 O) |
| `var/` | 런타임 상태·로그 (`var/logs/`) | X |
| `session.db` | 아직 루트에 있다 (P2 미실행) | X |

## 명령

| 순서 | 명령 | 비용 | 용도 |
|---|---|---|---|
| 1 | `bash sh/setup_venv.sh` | 없음 | `.venv` 생성 + `requirements.txt` 설치 (최초 1회) |
| 1' | `.venv/bin/pip install -r requirements-dev.txt` | 없음 | 테스트 도구(`pytest`) — 측정 환경과 분리 |
| 2 | `bash sh/setup_ollama.sh` | 없음 | 로컬 모델 준비 (`OLLAMA_FORCE_REFRESH=1`이면 재구성) |
| 3 | `bash sh/run_agent_ollma.sh` | 없음 | 백엔드만 기동, curl·웹으로 직접 테스트 |
| 3' | `bash sh/run_agent_openai.sh` | **과금** | 실제 OpenAI API 사용 (y/N 확인) |
| 4 | `bash sh/run_frontend.sh` | 백엔드 따름 | `http://localhost:8600` 채팅 화면 |

확인 명령: `curl -s localhost:8100/health`, `curl -s localhost:8100/version`, `curl -N localhost:8100/chat/stream`

평가 명령 (실행 1회 = `artifacts/runs/<run_id>/`):

| 명령 | 용도 |
|---|---|
| `.venv/bin/python -m pytest` | 테스트 50개 (unit·integration) |
| `.venv/bin/python eval/run_eval.py --variant before-rag --profile extended` | 개선 전 기준선 측정 → `artifacts/runs/` |
| `.venv/bin/python eval/run_eval.py --variant after-rag --profile extended --repeat 2` | 개선 후 측정·재현성 확인 |
| `.venv/bin/python eval/run_eval.py --variant after-rag --mode e2e` | 기동 중인 서버(:8100) 대상 지연·비용 측정 |
| `.venv/bin/python eval/make_before_after.py --pair <before> <after>` | Before/After 표 생성 → `doc/reports/evidence/` |

환경변수로 런타임이 바뀐다 — 측정 조건에 반드시 적는다.

| 변수 | 값 | 의미 |
|---|---|---|
| `LLM_BACKEND` | `fake`(기본) / `ollama` / `openai` | LLM 백엔드 |
| `SUPERVISOR_VERSION` | `v2`(기본) / `v1` | LangGraph 파이프라인 / legacy 선형 |
| `DATA_PROFILE` | `extended`(기본) / `base` | 모니터링 데이터 12시스템 / 6시스템 (`agent/data_profile.py`) |
| `RAG_ENABLED` | `true`(기본) / `false` | RAG RunBook 선택 on/off — 같은 코드에서 A/B |
| `RAG_MIN_SCORE`, `RAG_MIN_MARGIN` | `0.50`, `0.03` | RAG 판정 하한·1·2위 격차 하한 (미달 시 keyword 폴백) |
| `RAG_EMBEDDER`, `RAG_EMBED_MODEL` | `auto` / `qwen3-embedding:0.6b` | 임베더 선택·모델 (실제 사용값은 `/health.rag`) |
| `LANGCHAIN_TRACING_V2`, `LANGCHAIN_PROJECT` | `.env` | LangSmith 기록 |

## 근거 규칙 (평가 대응)

평가표: 기능 구현 30 · Before/After 실측 10(보너스) · 기술 요소 30 · 한계·트레이드오프 20 · 발표 20.
진행 추적은 `doc/evaluation-checklist.md` 하나로 한다. 폴더·산출물 설계는 `doc/artifact_management_design.md`.

- **수치는 측정 원본에서 인용한다.** 보고서에 손으로 옮겨 적은 숫자를 쓰지 않는다.
- **측정하지 않은 수치를 쓰지 않는다.** 실행하지 않은 테스트의 통과를 주장하지 않는다.
- Before/After는 **같은 입력·같은 백엔드·같은 조건**에서 2회 실행한다. 입력은 `doc/regression_test_queries.md`의 고정 질의 세트를 쓴다.
- 개선 지점마다 **코드 위치(파일·함수)를 말할 수 있어야 한다.** 과제 조건이다.
- 개선이 만든 약점은 `doc/evaluation-checklist.md` 6장에 수치와 함께 남긴다.

## 금지

- 루트 진입점 이동·이름 변경, `agent/` 재배치
- `.env`, API 키, 토큰을 커밋·로그·응답·에러 메시지에 노출
- `artifacts/`, `var/`, `.archify/`, `.venv/`, `session.db`, `__pycache__/` 커밋 (`.gitignore` 처리됨)
- 실행 안 한 명령의 결과를 캡처·로그처럼 기록
- 상위 과제 지침(`skala-tasks/AGENTS.md`)의 보고서 형식 위반

## 작업 후 확인

1. `git status --short` — 의도한 파일만 변경됐는가
2. `curl -s localhost:8100/health` — 서버가 살아 있는가
3. 회귀 질의 세트 중 변경과 관련된 항목 재실행 — 기존 동작이 깨지지 않았는가
4. `doc/evaluation-checklist.md` 상태 갱신 — 증거 경로를 함께 적었는가

## 이 문서를 갱신할 시점

`doc/artifact_management_design.md` 9장의 P0·P3을 실행해 `artifacts/`, `var/`, `tests/`, `doc/reports/`가 생겼다(2026-10-20). 경로는 위 "폴더 구조" 표를 기준으로 한다.
아직 **미실행**인 것은 P1(`doc/image_usecase*` → `doc/assets/` 이동)과 P2(`session.db` → `var/session.db`)다.
P1·P2를 실행하면 이 문서와 `agent/AGENTS.md`·`doc/AGENTS.md`·`sh/AGENTS.md`의 경로를 **같은 작업에서** 고친다.
