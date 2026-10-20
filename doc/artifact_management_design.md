# 산출물 관리 및 폴더 구조 설계 (v0.3)

- 대상: `skala-references/w15-ai-service-mini/all_total_vue_student`
- 상태: **P0~P3 실행 완료 (2026-10-20)**.
- 실행 결과: `artifacts/`·`var/`·`tests/`·`doc/reports/` 생성, `eval/run_eval.py`·`eval/metrics.py`·`eval/make_before_after.py` 추가,
  테스트 50개(`tests/`), 근거 대조표(`doc/reports/evidence/`), 제출 산출물(보고서·발표자료·아키텍처).
  현재 경로는 루트 `AGENTS.md` "폴더 구조" 표 기준.
- **P1 실행 방식**: `doc/image_usecase*`를 `doc/assets/`로 **이동하지 않고** 같은 경로에서 PNG→JPEG로 압축했다
  (5.2MB → 1.6MB). 이유: `doc/README.md`가 강사 제공 매뉴얼이라 그 안의 디렉터리 트리를 건드리지 않기 위해서다.
  매뉴얼 2개가 참조하는 이미지 링크 12곳만 `.png` → `.jpg`로 바꿨다.
- **P2 실행 방식**: `agent/session_store.py`의 `DB_PATH` → `var/session.db`(디렉터리는 자동 생성),
  `sh/run_agent_*.sh`의 `rm -f session.db` → `rm -f var/session.db`,
  `sh/make_student_zip.sh`에 `artifacts`·`var`·`.archify`·`.pytest_cache`·`.git` 제외 규칙 추가.
- **정리(2026-10-20)**: `.archify/`(3.0M)·`__pycache__`·`.pytest_cache`·`artifacts/captures/`(원본 캡처는
  `doc/reports/images/`에 압축본 커밋)·`artifacts/exports/`의 중복 PDF·`data/runbook_index.json`(캐시) 삭제.
  `/tmp`의 Chrome 프로필 잔여물도 정리했다.
- 근거
  - `../AI 서비스 Mini-Project.pdf`: Git 주소 등록, 결과 보고서(Google Spread), 개인별 발표
  - 같은 PDF 평가표: 기능 구현 30 · Before/After 실측 10(보너스) · 기술 요소 30 · 한계/트레이드오프 20 · 발표 20
  - 기준선 크기(`doc` 8.3M, `.archify` 3.0M, `session.db` 128K) → 정리 후 `doc` 4.7M

---

## 1. 현재 상태 진단

| # | 문제 | 근거 |
|---|---|---|
| 1 | 코드·입력 데이터·문서·생성물·런타임 상태가 루트와 `doc/`에 혼재 | 루트에 `server.py`, `session.db`, `web_chat.html`이 같은 층 |
| 2 | 생성물과 원본의 구분 규칙이 없음 | `.archify/`(2.9MB 작업물)가 `.gitignore`에 없고, `eval/baseline_keyword.json`(생성물)은 커밋 대상 |
| 3 | Before/After 비교의 "실행 1회" 단위가 없음 | `eval/`에 결과 파일이 고정 이름 1개뿐 → 개선 전/후를 나란히 보관 불가 |
| 4 | 캡처·평가 결과의 최종본/중간본 구분이 없음 | `doc/image_usecase*` 5.2MB, `eval/*.json` |
| 5 | Git 이력이 없음 | 저장소 루트가 `/Users/baggeon-u/Desktop`, 커밋 0건 → "Git 주소 등록" 요건 미충족 위험 |

핵심 원칙: **"다시 만들 수 있는가?"** 로 위치를 정한다.
다시 만들 수 있으면 `artifacts/`(커밋 안 함), 다시 만들 수 없거나 증거로 제출해야 하면 `doc/`(커밋)에 둔다.

---

## 2. 설계 원칙

1. **4계층 분리** — 입력 / 코드 / 생성물 / 공개 증거를 섞지 않는다.
   - 입력: `data/`, `eval/*_labels.json`
   - 코드: `agent/`, `eval/*.py`, `server.py`, `tests/`
   - 생성물: `artifacts/`, `var/`, `.archify/` (전부 gitignore)
   - 공개 증거: `doc/reports/`, `doc/design/`, `doc/assets/` (선별·압축·커밋)
2. **실행 1회 = 폴더 1개** — 모든 측정은 `artifacts/runs/<run_id>/`에 자기완결적으로 남긴다. 같은 폴더를 덮어쓰지 않는다.
3. **이름만 보고 정렬·식별** — `run_id`는 `YYYYMMDD-HHMMSS_<backend>_<variant>` (예: `20261020-153012_openai_before-rag`).
4. **문서는 증거를 링크하고, 수치는 원본에서 인용** — 보고서에 손으로 옮겨 적은 숫자 대신 `metrics.json` 경로를 병기한다.
5. **루트 진입점은 유지** — `server.py`, `mcp_server.py`, `sh/*.sh` 경로는 과제 매뉴얼과 학생 배포 zip이 참조하므로 이동하지 않는다.

---

## 3. 목표 폴더 구조

표기: `[유지]` 현행 유지 · `[신규]` 추가 · `[이동]` 위치 변경 · `[수정]` 내용 변경

```text
all_total_vue_student/
├── server.py                       [유지] FastAPI 진입점
├── mcp_server.py                   [유지] MCP ops 서버
├── mcp_server_docs.py              [유지] MCP docs 서버(decoy)
├── web_demo_server.py              [유지] 정적 페이지 + 프록시(:8600)
├── web_chat.html                   [유지] Vue 채팅 화면
├── requirements.txt                [유지]
├── requirements-dev.txt            [신규] pytest 등 개발 의존성 (테스트 단계에서)
├── .env.example                    [유지] 키 이름만
├── .env                            [유지] 비밀, 커밋 금지
├── .gitignore                      [수정] 생성물·런타임·도구 디렉토리 추가
├── README.md                       [신규] 3줄 안내 + doc/README.md 링크 (루트 진입점)
│
├── agent/                          [유지] 런타임 코드
│   ├── deps.py  graph.py  supervisor_v1.py
│   ├── fake_llm.py  ollama_llm.py  openai_llm.py
│   ├── mcp_client.py  retry.py
│   ├── session_store.py            [수정 예정] DB 경로 → var/session.db
│   └── rag/                        [유지]
│
├── data/                           [유지] 사실 입력(원본)
│   ├── monitoring.json
│   ├── runbooks/*.md               (6종)
│   └── runbook_index.json          [유지] 임베딩 캐시 = 생성물, gitignore 유지
│
├── eval/                           [유지] 평가 코드 + 고정 기준선
│   ├── common.py  run_baseline.py
│   ├── baseline_labels.json        [유지] 평가셋(입력)
│   └── baseline_keyword.json       [유지] 개선 전 기준선 스냅샷(커밋)
│
├── tests/                          [신규] 단위·통합 테스트
│   ├── unit/                       (분류기, gate, retry, RAG 매핑)
│   └── integration/                (FastAPI TestClient, MCP stdio, 세션 재시작)
│
├── sh/                             [유지] 실행 스크립트 (경로 변경 금지)
│   ├── setup_venv.sh  setup_ollama.sh
│   ├── run_agent_ollma.sh  run_agent_openai.sh  run_frontend.sh
│   └── make_student_zip.sh         [수정 예정] artifacts/·var/ 제외 추가
│
├── doc/                            [유지] 사람이 읽는 문서 (커밋)
│   ├── README.md                   [수정] 구조도·실행법 (본 설계 반영)
│   ├── manual_ollma.md             [수정 예정] 이미지 경로
│   ├── manual_openai.md            [수정 예정] 이미지 경로
│   ├── regression_test_queries.md
│   ├── artifact_management_design.md   ← 이 문서
│   │
│   ├── design/                     [신규] 설계 산출물
│   │   └── architecture.html       [이동] .archify 최종본만 복사
│   │
│   ├── reports/                    [신규] 제출·발표 산출물
│   │   ├── result_report.md        결과 보고서 원문(Google Spread 입력용)
│   │   ├── presentation_outline.md 문제 → 개선 → Before/After 수치 → 한계
│   │   └── evidence/
│   │       ├── index.md            주장 ↔ 증거 파일 ↔ 재현 명령 대응표
│   │       ├── before_after.md     비교표 + 해석
│   │       └── metrics/*.json      선별 복사한 작은 수치 파일
│   │
│   └── assets/                     [신규] 문서용 이미지 (커밋)
│       ├── manual-ollama/          [이동] doc/image_usecase/
│       └── manual-openai/          [이동] doc/image_usecase_openai/
│
├── artifacts/                      [신규] 원본 생성물 (커밋 안 함)
│   ├── README.md                   [신규·커밋] 보관 규칙과 삭제 기준
│   ├── runs/<run_id>/              실행 1회 = 1폴더 (5장 참조)
│   ├── eval/                       eval 스크립트가 남기는 원본 결과
│   ├── captures/<run_id>/          시연·발표용 원본 스크린샷
│   ├── traces/                     LangSmith 내보내기·trace ID 목록
│   ├── exports/                    PPT/PDF/zip 등 바이너리
│   └── tmp/                        7일 뒤 삭제해도 되는 중간물
│
├── var/                            [신규] 런타임 상태 (커밋 안 함)
│   ├── session.db                  [이동 예정] SQLite 대화 이력
│   └── logs/                       서버 로그
│
├── .archify/                       [유지] 도구 작업 디렉토리 (커밋 안 함)
└── .venv/                          [유지] (커밋 안 함)
```

코드 디렉토리(`agent/` → `src/agent/`) 재배치는 **하지 않는다.** 과제 매뉴얼·배포 zip·import 경로가 모두 현재 구조를 전제로 하고, 재배치 이득보다 검증 비용이 크다.

---

## 4. 디렉토리 책임과 보관 정책

| 경로 | 책임 | 커밋 | 정리 기준 |
|---|---|---|---|
| `data/` | 모니터링·런북 사실 데이터 | O | 원본이므로 삭제 금지 |
| `eval/baseline_*.json` | 개선 전 기준선 | O | 재생성은 가능하지만 비교 기준이므로 고정 |
| `agent/`, `eval/*.py`, `tests/` | 실행 코드·테스트 | O | 삭제 대신 대체 후 이력으로 남김 |
| `doc/design/`, `doc/reports/` | 제출·발표 산출물 | O | 최종본만. 초안은 `artifacts/tmp/` |
| `doc/assets/` | 문서에 실제로 쓰는 이미지 | O | 300KB 이하로 압축, 미사용 이미지 제거 |
| `artifacts/runs/` | 측정 원본 | X | 최종 비교 run은 채점 후까지 보존, 나머지는 30일 |
| `artifacts/tmp/`, `var/logs/` | 중간물·로그 | X | 7일 |
| `.archify/` | 도구 내부 상태 | X | 최종 HTML만 `doc/design/`에 복사 후 정리 가능 |

용량 규칙: 커밋 파일 1개 1MB 이하, 총 저장소 20MB 이하 목표. 초과분은 `artifacts/exports/`에 두고 보고서에서 경로만 안내한다. Git LFS는 쓰지 않는다.

---

## 5. 실행 산출물 표준 (`artifacts/runs/<run_id>/`)

```text
20261020-153012_openai_before-rag/
├── manifest.json      실행 조건·버전·명령 (비밀값 제외)
├── requests.jsonl     입력 1건 = 1줄 (id, query, session_id)
├── responses.jsonl    출력 1건 = 1줄 (id, reply, latency_ms, tokens, cost_usd, error)
├── metrics.json       집계 (정확도, p50/p95 지연, retry, 비용)
├── notes.md           사람이 쓴 관찰·해석
├── logs/server.log    해당 실행 구간 로그
├── traces/            LangSmith trace ID·내보내기
└── captures/          해당 실행의 스크린샷
```

`manifest.json` 최소 스키마:

```json
{
  "run_id": "20261020-153012_openai_before-rag",
  "started_at": "2026-10-20T15:30:12+09:00",
  "ended_at": "2026-10-20T15:33:40+09:00",
  "variant": "before-rag",
  "git_commit": "abc1234",
  "git_dirty": false,
  "backend": "openai",
  "model": "gpt-4.1-mini",
  "supervisor_version": "v2",
  "dataset": "eval/baseline_labels.json",
  "command": ".venv/bin/python eval/run_eval.py --variant before-rag",
  "env": { "LLM_BACKEND": "openai", "SUPERVISOR_VERSION": "v2" },
  "metrics": { "accuracy": 0.75, "p50_latency_ms": 1200, "retry_count": 2 },
  "notes": "RAG 도입 전 기준선"
}
```

규칙:
- `env`는 **허용 목록 방식**으로 기록한다. API 키·토큰·`.env` 전체 덤프 금지.
- 같은 `run_id` 폴더는 덮어쓰지 않는다. 재실행은 새 타임스탬프.
- `variant` 값은 `before-*` / `after-*` 접두어로 고정해 비교 대상을 이름으로 찾게 한다.

---

## 6. 평가 항목 ↔ 산출물 대응 (증거 매트릭스)

| 평가 항목 | 배점 | 필요한 증거 | 위치 | 확인 방법 |
|---|---|---|---|---|
| 기능 구현 완성도 | 30 | 실행되는 코드, 시연 캡처·로그, 테스트 | `server.py`, `agent/`, `tests/`, `artifacts/captures/` | `pytest -q`, `curl :8100/version`, `:8600` 화면 |
| Before/After 실측 | 10 | 동일 입력 2회 실행 + 수치 비교 | `artifacts/runs/*before*`, `*after*`, `doc/reports/evidence/before_after.md` | eval 재실행, `metrics.json` 대조 |
| 기술 요소 반영 | 30 | Multi-Agent·MCP·RAG·DI·LangSmith·모듈화·테스트의 코드 위치 | `doc/design/architecture.html`, `agent/`, `tests/` | trace 링크, 노드 목록 |
| 한계·트레이드오프 | 20 | 개선이 만든 부작용과 수치 | `doc/reports/result_report.md` §한계 | 인용 수치가 `metrics.json`과 일치 |
| 발표 | 20 | 문제→개선→수치→한계 순서 자료 | `doc/reports/presentation_outline.md`, `artifacts/exports/` | 리허설, PDF 백업 |

`doc/reports/evidence/index.md` 형식(1줄 1주장):

| 주장 | 증거 파일 | 재현 명령 | 작성일 |
|---|---|---|---|
| RAG 매핑으로 분류 정확도 62%→81% | `metrics/after-rag.json` | `eval/run_eval.py --variant after-rag` | 2026-10-20 |

---

## 7. 명명 규칙

| 대상 | 규칙 | 예 |
|---|---|---|
| 실행 폴더 | `YYYYMMDD-HHMMSS_<backend>_<variant>` | `20261020-153012_ollama_after-rag` |
| 평가 결과 | `<dataset>__<run_id>.json` | `baseline_labels__20261020-153012_ollama_after-rag.json` |
| 캡처 | `NN_<장면>.png` (발표 순서) | `01_chat_greeting.png` |
| 보고서 초안 | `draft_<주제>_<날짜>.md` → `artifacts/tmp/` | `draft_limits_20261020.md` |
| 최종 문서 | `<목적>.md` 고정 이름 | `result_report.md` |

시각은 로컬(KST) 기준, `manifest.json`에는 오프셋 포함 ISO 8601로 기록한다.

---

## 8. `.gitignore` 추가안

```gitignore
# 생성 산출물
/artifacts/*
!/artifacts/README.md
/var/
.archify/

# 기존 유지
.env
.venv/
session.db
__pycache__/
*.log
data/runbook_index.json
.pytest_cache/
```

`artifacts/README.md`만 예외로 커밋해 "이 폴더는 비어 있는 것이 정상"임을 남긴다.

---

## 9. 이행 단계 (각 단계는 검증 후 다음으로)

### P0 — 구조만 추가 (코드 변경 0)  ← 실행 완료(2026-10-20)
1. `artifacts/{runs,eval,captures,traces,exports,tmp}`, `var/logs`, `doc/{design,reports/evidence/assets}`, `tests/{unit,integration}` 생성
2. `artifacts/README.md`, `doc/reports/evidence/index.md` 골격 작성
3. `.gitignore`에 8장 추가
- 검증: `bash sh/run_agent_ollma.sh` 기동, `:8100/version` 응답, `git status`에 `artifacts/`·`var/` 미표시

### P1 — 문서·이미지 정리 (참조 수정 필요)  ← 실행 완료(압축 방식, 2026-10-20)
1. `doc/image_usecase*` → `doc/assets/manual-*` 이동
2. `manual_ollma.md`·`manual_openai.md` 이미지 경로 수정
3. `.archify/.../all-total-architecture.html` → `doc/design/architecture.html`
- 검증: `grep -rn "image_usecase" doc/` 결과 0건, 두 매뉴얼 미리보기에서 이미지 표시

### P2 — 런타임 상태 분리  ← 실행 완료(2026-10-20)
1. `agent/session_store.py`의 `DB_PATH` → `var/session.db`
2. `sh/run_agent_*.sh`의 `rm -f session.db` → `rm -f var/session.db`
3. `sh/make_student_zip.sh` 제외 목록에 `artifacts`, `var`, `.archify` 추가
- 검증: 서버 재시작 후 이름 기억 시나리오 통과, `session.db`가 루트에 생기지 않음

### P3 — 평가·테스트 표준화  ← 실행 완료(2026-10-20)
1. `eval/` 결과 출력을 `artifacts/eval/`로 변경(기준선 파일은 유지)
2. `tests/` 작성, `requirements-dev.txt` 추가
3. Before/After 2회 실행 → `doc/reports/evidence/before_after.md`
- 검증: `pytest -q` 통과, 두 run의 `manifest.json`·`metrics.json` 존재

### P4 — 제출물
1. `result_report.md` → Google Spread 입력
2. `presentation_outline.md` → PPT/PDF (`artifacts/exports/`)
- 검증: 보고서 수치가 `evidence/index.md` 경유로 `metrics.json`과 일치

---

## 10. 결정이 필요한 항목

| ID | 질문 | 권고 |
|---|---|---|
| D1 | Git 저장소를 어디에 만들까? (현재 상위 Desktop이 커밋 0건인 repo) | 이 프로젝트 폴더를 독립 repo로 `git init` 후 P0 이전에 첫 커밋. 과제의 "Git 주소" 요건 충족 |
| D2 | PPT 바이너리를 커밋할까? | 원본은 `presentation_outline.md`, 바이너리는 `artifacts/exports/`에만 두고 링크 |
| D3 | `.archify/`를 삭제할까? | 최종 HTML 복사 후에도 당장은 보존, 채점 종료 후 정리 |
| D4 | eval 원본 JSON을 커밋할까? | 원본은 `artifacts/`, 선별 요약만 `doc/reports/evidence/metrics/` |
| D5 | `var/` 대신 `artifacts/runtime/`을 쓸까? | 상태(DB)와 산출물(측정)은 성격이 달라 `var/` 분리 권고 |

---

## 11. 이 설계에서 하지 않는 것

- `server.py`·`agent/`를 `src/`로 재배치 (매뉴얼·zip·import 경로 파손)
- 모노레포화, Docker화 (별도 단계)
- Git LFS, 대용량 trace 커밋
- `doc/` 안에 측정 원본 저장 (문서와 생성물 혼합)
- 초안·중간 산출물의 커밋 (최종본만 커밋)

---

## 12. 다음 한 단계

D1(저장소 위치) 확정 → **P0 구조 생성**만 실행하고, `sh/run_agent_ollma.sh` 기동과 `git status`로 검증한다.
