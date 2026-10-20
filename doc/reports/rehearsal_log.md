# 발표 리허설 기록 (2026-10-20)

발표 전까지 **기계가 대신 확인 가능한 것**을 전부 확인해 둔 기록이다.
사람이 해야 하는 마지막 두 가지는 맨 아래에 적었다.

## 1. 수치 일치 검사 — 통과 13/13

`eval/check_reported_numbers.py` — 문서(슬라이드·보고서·스프레드시트 본문·README·체크리스트)에
적힌 숫자가 측정 원본(`doc/reports/evidence/metrics/`)과 같은지 대조한다.

| 주장 | 원본 값 | 상태 |
|---|---|---|
| 40문항 정확도 Before / After | 0.3250 / 0.8500 | PASS |
| macro-F1 Before / After | 0.2836 / 0.8521 | PASS |
| E2E 정확도 Before / After | 0.2000 / 1.0000 | PASS |
| 분류 지연 p50 (After) | 32.43ms | PASS |
| E2E 요청 p50 Before / After | 750.76ms / 819.73ms | PASS |
| 조사 커버리지 unknown (base / extended) | 18.75% / 0.00% | PASS |
| RAG 폴백률 | 15.00% | PASS |
| 재현성 | identical | PASS |

검사 중 **실제 오류 1건**이 잡혀 고쳤다. coverage(extended) 수치를 base 실행 폴더에서
읽는 **원본 매핑 오류**였다(값은 맞았고 표기만 틀릴 뻔했다).
고친 뒤 슬라이드 8과 체크리스트 지표표에 폴백률(15.00%) 행을 추가했다.

## 2. 회귀 질의 10개 — 10/10 통과

`eval/run_regression_queries.py` — PDF 9쪽 예시 질의를 실제 서버에 던지고(10번은 서버를
실제로 재시작), 기대 결과(라우팅·판정 유형·조회 대상·unknown·기억)를 확인한다.

| 조건 | 통과 | 근거 |
|---|---|---|
| 라우팅 수정 전 | 3/10 | `eval/regression_queries_before.json` |
| 라우팅 수정 후 (RAG on) | **10/10** | `eval/regression_queries.json` |
| 라우팅 수정 후 (RAG off = keyword) | 9/10 | `eval/regression_queries_rag_off.json` |

keyword 경로가 남기는 1건(#4 타임아웃 → cpu-spike)은 규칙 순서 결함이고,
RAG를 켜면 network-timeout으로 고쳐진다. 이건 개선된 지점이다.

## 3. 시연 순서 실측 — 총 3초

`fake` 백엔드, `DATA_PROFILE=extended`, RAG on, 프론트엔드 프록시(:8600) 경유.

| 순서 | 명령 | 소요 | 결과 |
|---|---|---|---|
| 1 | `curl -s localhost:8100/health` | 0.03s | `rag.enabled=true`, `embedder=ollama:qwen3-embedding:0.6b`, `docs=10`, `profile=extended(12시스템)` |
| 2 | 채팅 "auth-service 로그인 응답이 p95 2.4초로 느려졌어요, 원인 진단해주세요" | 1.29s | `high-latency` · rag · score 0.6108 |
| 3 | 채팅 "search-service 인덱싱 큐가 1만 2천 건 밀렸어요, 원인 진단해주세요" | 0.81s | `queue-backlog` · rag · score 0.6452 |
| 4 | 채팅 "billing-service 장애 긴급합니다, 원인 진단해주세요" | 0.80s | `db-down` · **keyword 폴백** · score 0.3709 · `systems_unknown=['billing-service']` |

- 4번(미지 시스템)이 "폴백한다"는 것을 화면으로 보여줄 수 있다. RAG가 확신하지 못해
  keyword로 내려가는 순간을 그대로 보여주는 게 이 시연의 목적이다.
- 채팅 라우트(잡담)는 `chat`으로 분기하는 것도 함께 확인했다(시연 0).
- 요청 자체는 3초다. 시연 전체 3분은 **입력 타이핑·대기 포함** 예산이라 여유가 충분하다.

## 4. 발표물 파일 점검

| 파일 | 상태 |
|---|---|
| `doc/reports/presentation.pdf` | 10장(16:9) 생성 확인 |
| `doc/reports/presentation.pptx` | 10장 생성 확인 (PPT는 편집용, PDF가 기준) |
| `doc/reports/result_report.pdf` | 생성 확인 (916KB) |
| `doc/design/architecture.html` | archify 게이트 4종 통과, 브라우저 렌더 확인 |
| `doc/reports/spreadsheet_input.md` | 붙여넣기용 본문 준비 |

## 5. 남은 사람 몫 (2가지)

1. **스프레드시트 등록(S6)** — `doc/reports/spreadsheet_input.md` 내용을 붙여넣고 보고서 주소(Google Drive 링크)를 등록.
   (구글 시트에는 접근하지 않았다. 필요하면 붙여넣을 수 있는 형태로만 prepared 되어 있다.)
2. **실제 말하기 리허설(S7)** — 위 시연 순서와 슬라이드 7·8의 수치를 소리 내어 한 번.
   슬라이드 8에서는 **"데이터 확장은 정확도를 올리지 못했다"**를 먼저 말한다.

## 6. 되돌릴 수 있는 것

- 이 문서와 `eval/check_reported_numbers.py`, `eval/reported_numbers_check.json`은 커밋 대상이다.
- 서버·프론트엔드는 리허설 측정 뒤 종료했다(포트 8100·8600 정리 완료).
