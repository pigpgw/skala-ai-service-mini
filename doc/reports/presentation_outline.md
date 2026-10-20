# 발표 자료 구성안 — Base AI Agent의 RunBook 선택 개선

광주 3반 79번 박건우 · 2026-10-22 · 약 10분 + 시연 3분

사용 파일
- 슬라이드 본체: `doc/reports/presentation.html` (인쇄하면 16:9 PDF가 됨)
- 배포용 바이너리: `artifacts/exports/`
- 근거: `doc/reports/evidence/index.md`

**발표 원칙**: 수치는 화면에 있는 그대로 말한다. 근거 경로(원본 파일)를
한 번씩 말해 두면 질문이 왔을 때 바로 보여줄 수 있다.

---

## 슬라이드 구성

### 1. 표지
- 제목: Base AI Agent의 RunBook 선택 개선
- 부제: RAG 기반 RunBook 선택 · 데이터 확장 · 평가 하네스 구축
- 광주 3반 79번 박건우 / 2026-10-22 / Git 주소
- 말할 말: "기존 인시던트 대응 에이전트가 '어떤 대응 절차'를 고르는 부분에서
  잘못되는 경우가 있어서, 그 부분을 RAG로 바꾸고 측정할 수 있게 만들었습니다."

### 2. 문제 — 어디가 틀렸나
- 장애 유형 판정이 `agent/graph.py::_classify_incident_type()` 한 함수에 있음
- 키워드 규칙을 **순서대로** 보면서 **처음 맞는 것**을 선택
- 문제 3가지:
  1. 규칙 순서가 증상 우선순위와 무관 (CPU가 timeout보다 앞)
  2. 질의문을 아예 보지 않음
  3. 매칭 실패 시 무조건 `db-down`
- 화면: 코드 위치 표시

### 3. 근거 — 먼저 재기를 돌렸다
- 고정 질의 12개로 기준선 측정 → **8/12 = 0.6667**
- 오분류 4개: B07(규칙 순서), B09(memory가 disk보다 앞), B10·B11(질의문 미사용)
- 예시: "gateway-service → payments-service 타임아웃" → `cpu-spike`로 분류됨
- 판단: 규칙을 늘리는 건 유지보수 남는 숙제 → 의미 검색으로 교체
- 증거: `eval/baseline_keyword.json`

### 4. 개선 1 — RAG 기반 RunBook 선택
- `agent/rag/embedder.py` (Ollama qwen3-embedding:0.6b, 1024차원)
- `agent/rag/index.py` (10문서 인덱스 + JSON 캐시, `index_sha256` 기록)
- `agent/rag/classifier.py` (판정 5분기: disabled·index_unavailable·embed_failed·low_score·low_margin → keyword 폴백)
- 연결: `agent/graph.py::_select_incident_type()` → `replan_check_node`
- 근거 노출: `/health.rag`, `/chat` metadata, SSE `ReplanCheck`
- 말할 말: "RAG가 확신하지 못하면 예전 동작 그대로 돌아갑니다. 게이트를 둔 이유입니다."

### 5. 개선 2 — 데이터 확장
- 시스템 6 → 12 (`data/monitoring_extended.json`), 런북 6 → 10
- 신규 유형 4개: queue-backlog, cert-expiry, connection-pool, replication-lag
- `DATA_PROFILE=base|extended` — 파일 선택은 `agent/data_profile.py` 한 곳에서만
- 기존 `monitoring.json`은 기준선으로 보존(덮어쓰지 않음)
- `billing-service`는 일부러 제외 (미지 시스템 처리 회귀 검증용)

### 6. 개선 3 — 평가 하네스
- `eval/run_eval.py` — 실행 1회 = `artifacts/runs/<run_id>/` (manifest·metrics·jsonl)
- `eval/metrics.py` — accuracy·macro-F1·혼동행렬·지연 percentile
- `eval/labels_extended.json` — 40문항(10유형 × 4카테고리), 측정 전 동결
- `tests/` — unit 5종 + integration 2종 = 50개 통과
- 말할 말: "Before/After가 같은 조건인지 확인되려면 그 조건이 파일로 남아야 했습니다."

### 7. 결과 — Before / After
표(같은 조건: fake 백엔드, DATA_PROFILE=extended, qwen3-embedding:0.6b, 임계값 0.50/0.03)

| 지표 | Before | After | 차이 |
|---|---|---|---|
| 40문항 정확도 | 13/40 = 0.3250 | 34/40 = 0.8500 | +0.5250 |
| macro-F1 | 0.2836 | 0.8521 | +0.5685 |
| E2E 5문항(실서버) | 1/5 | 5/5 | +0.8000 |
| 분류 지연 p50 | 0.0ms | 32.43ms | +32.43ms |
| E2E 요청 p50 | 750.76ms | 819.73ms | +68.97ms |
| 비용 | $0 | $0 | 0 (로컬) |

- 신규 4유형 F1: queue-backlog 0.000→1.000, cert-expiry 0.000→1.000,
  connection-pool 0.000→1.000, replication-lag 0.000→0.857
- 증거: `artifacts/runs/20261020-152756_fake_*`, `doc/reports/evidence/before_after.md`

### 8. 해석 — 좋았던 것, 안 좋았던 것
- 데이터 확장은 **정확도를 올리지 못했다** (base 34/40 ≡ extended 34/40)
  - 대신 조사 커버리지(unknown 18.75% → 0%)가 개선
  - 이유: 라벨이 질의에 증상을 명시해 RAG가 질의만 읽어도 맞음 → 데이터는 보조 신호
- margin 게이트는 2문항을 아꼈습니다 (0.03 → 34/40, 0.00 → 36/40)
  - 동점(0.0155, 0.0000)에서 뒤집힌 사례가 있어 유지
- RAG 비용 = 임베딩 1회 호출 (+32.43ms, 요청의 약 9%)
- 말할 말: "데이터를 늘렸다고 정확도가 올랐다고는 쓰지 않았습니다. 측정이 그랬습니다."

### 9. 한계와 추가로 확인해 볼 것
- 40문항 라벨을 제가 만들었다 → 자기 평가. 카테고리별로 나눠 보고 전체 수치로 일반화하지 않음
- keyword 폴백 규칙은 그대로 → 신규 유형마다 갱신 필요
- 비용 0은 로컬 백엔드 때문 → 실 API 비용은 별도 측정 필요
- 지연은 단일 실행 기준 → 동시 요청 미측정
- 다음: 실제 장애 티켓으로 라벨 세트 재구축, 동시 부하 측정, 실 백엔드 비용 측정

### 10. 시연과 정리
- 라이브 데모 3분
  1. `curl -s localhost:8100/health` → rag 블록, data_profile 12시스템
  2. 채팅: "auth-service 응답이 p95 2.4초로 느려졌어요, 원인 진단해주세요" → high-latency
  3. 채팅: "search-service 인덱싱 큐가 1만 2천 건 밀렸어요" → queue-backlog (신규 유형)
  4. 채팅: "billing-service 장애" → unknown + keyword 폴백
- 정리: "판정을 바꾼 것이 아니라, 판단 근거를 남기고 측정할 수 있게 바꾼 것이 이번 과제입니다."
- Git: https://github.com/pigpgw/skala-ai-service-mini

---

## 시간 배분 (10분)

| 시간 | 슬라이드 |
|---|---|
| 0:00–1:00 | 1. 표지 |
| 1:00–2:30 | 2. 문제 |
| 2:30–3:30 | 3. 근거(기준선) |
| 3:30–5:00 | 4. 개선 1 (RAG) |
| 5:00–5:45 | 5. 개선 2 (데이터) |
| 5:45–6:30 | 6. 개선 3 (하네스) |
| 6:30–8:00 | 7. 결과 표 |
| 8:00–9:00 | 8. 해석 |
| 9:00–9:30 | 9. 한계 |
| 9:30–10:00 | 10. 정리 → 시연(3분) |

## 예상 질문과 답

**"라벨을 직접 만들었는데 정확도가 의미가 있나요?"**
라벨을 측정 전에 동결했고(동결 시각·해시 기록), 카테고리별로 나눠서
보고했습니다. 질의 의존도가 높은 20문항이 따로 있다는 점을 감안해서
전체 수치를 일반화 성능으로 쓰지 않았습니다. 실제 티켓 기반 라벨은 다음 단계로 남겼습니다.

**"RAG가 느려지는데 왜 도입했나요?**
분류 1건당 임베딩 1회 호출이니 +32ms이고, 실서버 요청 전체로는 +69ms
(요청 시간의 약 9%)입니다. 그 비용으로 오분류 27개(40문항 기준)가 줄었습니다.

**"데이터 확장이 효과가 있었나요?**
분류 정확도에는 없었습니다. 그건 그대로 기록했습니다. 대신 40문항이 조회한
모니터링 80회 중 데이터가 없어 못 본 15회가 0회가 됐습니다.

**"폴백이 많아져서 RAG가 안 쓰이는 건 아닌가요?**
40문항 중 6건(15%)만 keyword로 내려왔고, 나머지 34건은 RAG 판정을 따랐습니다.
내려간 6건은 1·2위 유사도 차이가 0.0155, 0.0000처럼 사실상 동점이었던 경우입니다.
