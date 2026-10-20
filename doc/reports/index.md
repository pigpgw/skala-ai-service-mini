# 제출 산출물 색인 — 무슨 파일이 어디 있는지

마지막 갱신: 2026-10-20 · 광주 3반 79번 박건우 · Git `main` = `origin/main`

이 문서는 "제출 전 마지막으로 확인할 파일" 한 장이다. 다른 문서를 읽기 전에 여기서
어디가 무엇인지부터 보면 빠뜨리지 않는다.

## 1. 제출(스프레드시트·발표) 산출물

| 파일 | 용도 | 상태 |
|---|---|---|
| `result_report.md` | 최종 결과 보고서 원문 | 완료 |
| `result_report.pdf` | 위 보고서의 PDF (916KB) | 완료 |
| `presentation.html` | 발표 슬라이드 10장(16:9) 원본 | 완료 |
| `presentation.pdf` | 슬라이드 PDF (780KB) — **발표 기준본** | 완료 |
| `presentation.pptx` | 슬라이드 PPTX (40KB) — 편집용 | 완료 |
| `presentation_outline.md` | 슬라이드 구성안 + 10분 시간 배분 + 예상 질문 + 리허설 체크리스트 | 완료 |
| `spreadsheet_input.md` | Google Spread 붙여넣기용 본문 | 완료 (붙여넣기는 사용자 몫) |
| `rehearsal_log.md` | 리허설 기록(수치 검사 13/13, 시연 4단계 실측) | 완료 |
| `architecture.html` | 개선 시스템 아키텍처 다이어그램 (archify) | 완료 |
| `images/01~03_chat_*.png` | 보고서에 실린 시연 캡처 3장 | 완료 |
| `evidence/index.md` | 주장 ↔ 증거 ↔ 재현 명령 대조표 | 완료 |
| `evidence/before_after.md` | Before/After 비교표 (원본에서 자동 생성) | 완료 |
| `evidence/metrics/*.json` | 인용한 6개 실행의 요약 수치 | 완료 |

같은 파일은 `skala-tasks/w14-ai-agent/`에 동일 내용으로 사본이 있다(9개 파일 + images/ 3장, 해시 동일 확인).
이 색인 자체도 `AI서비스_Mini_산출물_색인.md`로 사본이 있다.

## 2. 코드·측정

| 파일 | 역할 |
|---|---|
| `agent/rag/{embedder,index,classifier}.py` | E1 RunBook 선택 (임베더·인덱스 캐시·5분기 판정) |
| `agent/graph.py::_select_incident_type()` | RAG 우선 판정 연결 지점 |
| `agent/data_profile.py` | `DATA_PROFILE=base\|extended` 단일 결정 지점 |
| `agent/session_store.py` | 세션 저장소 (`var/session.db`) |
| `eval/run_eval.py` | 통합 하네스 — 실행 1회 = `artifacts/runs/<run_id>/` |
| `eval/metrics.py` | accuracy·macro-F1·혼동행렬·지연 percentile |
| `eval/check_reported_numbers.py` | **문서에 적힌 수치 ↔ 측정 원본** 일치 검사 |
| `eval/make_before_after.py` | Before/After 표·요약 JSON 자동 생성 |
| `tests/` | unit 5종 + integration 2종 (50개) |
| `doc/tools/{md2html,build_pptx,capture_ui}` | 보고서 PDF·PPTX·브라우저 캡처 도구 |

## 3. 재현 명령 (같은 수치가 나오는지 확인)

```bash
# 1) 테스트
.venv/bin/python -m pytest                                   # 50개

# 2) 분류 측정 (같은 조건 2회 → 재현성)
.venv/bin/python eval/run_eval.py --variant before-rag --profile extended
.venv/bin/python eval/run_eval.py --variant after-rag  --profile extended --repeat 2

# 3) E2E (서버를 먼저 띄우고)
LANGCHAIN_TRACING_V2=false LLM_BACKEND=fake DATA_PROFILE=extended \
  .venv/bin/python server.py &
.venv/bin/python eval/run_e2e_probe.py --tag final --out eval/e2e_probe_final.json

# 4) 문서 수치 ↔ 원본 일치 검사
.venv/bin/python eval/check_reported_numbers.py               # 13/13 PASS

# 5) 비교표 재생성
.venv/bin/python eval/make_before_after.py \
  --pair artifacts/runs/<before> artifacts/runs/<after>
```

## 4. 커밋되지 않는 것(재생성 가능)

| 경로 | 내용 | 복구 방법 |
|---|---|---|
| `artifacts/runs/<run_id>/` | 측정 원본 16개 실행 | `eval/run_eval.py`로 재생성 |
| `artifacts/design/` | archify 검증 영수증 | archify 재실행 |
| `var/session.db`, `var/logs/` | 런타임 상태·로그 | 서버 실행 시 자동 생성 |
| `data/runbook_index.json` | 임베딩 인덱스 캐시 | 서버 기동 시 자동 생성 |
| `.archify/`, `__pycache__/`, `.pytest_cache/` | 도구 작업물·캐시 | 자동 생성 |

## 5. 남아 있는 사람 몫 (2가지)

1. **S6** — `spreadsheet_input.md`를 Google Spread에 붙여넣고 보고서 주소(링크) 등록
2. **S7** — 말하기 리허설 1회 (절차: `presentation_outline.md` 마지막 절)

구글 시트에는 이 프로젝트에서 접근하지 않았다. Composio 계정에 Google Sheets 연결이
하나 남아 있으면(설치 시 실수로 생김) `composio connections remove googlesheets`로 해제한다.
