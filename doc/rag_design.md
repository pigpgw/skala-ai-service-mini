# RAG 기반 RunBook 선택 — 설계 (v0.1)

- 대상: `all_total_vue_student` (FastAPI + LangGraph v2 + MCP)
- 상태: **설계안**. 승인 후 `agent/rag/` 코드 작성. 이 문서 단계에서는 코드를 만들지 않는다.
- 근거
  - 기준선 측정: `eval/baseline_keyword.json` (12문항 8/12 = 0.6667)
  - 병목 코드: `agent/graph.py:192-202`(규칙 순서), `graph.py:206-209`(질의 미사용), `graph.py:213`(db-down 폴백)
  - 데이터 동결 규칙: `data/AGENTS.md`
  - 평가 항목: `doc/evaluation-checklist.md` §3 P1~P5

---

## 1. 목표와 비목표

**목표**: `replan_check_node`가 고르는 runbook(=`incident_type`)을 **키워드 첫 매칭**에서 **runbook 임베딩 의미 검색**으로 바꾼다. 실패하면 기존 keyword로 폴백한다.

**비목표**
- 벡터 DB(Chroma/FAISS/pgvector) 도입 — runbook 10개 규모
- 리랭커(cross-encoder), LLM-as-judge
- 임베딩 모델 파인튜닝
- `plan_node`의 조사 대상(system) 선택 변경 — 이번 개선은 incident_type 판정만 다룬다

## 2. 교체점과 호출 계약

```text
graph.py replan_check_node
   AS-IS:  incident_type = _classify_incident_type(collected)
   TO-BE:  result = deps.rag.classify(query, collected)
           incident_type = result.incident_type
           (ReplanCheck 이벤트에 source·score·margin 기록)
```

- `_classify_incident_type()`은 **삭제하지 않는다.** RAG 비활성·저신뢰·임베딩 실패 시 폴백으로 계속 쓰인다.
- `deps.rag`는 `SupervisorDeps`에 추가하고 **`server.py` lifespan에서 1회 생성**한다(`agent/AGENTS.md` 규칙).

```python
# agent/rag/classifier.py — 시그니처만 (구현은 다음 단계)
class RagClassifier:
    def __init__(self, index, embedder, *, enabled: bool,
                 min_score: float, min_margin: float, keyword_fallback=None): ...
    def classify(self, query: str, collected: list[dict]) -> ClassifyResult: ...

@dataclass(frozen=True)
class ClassifyResult:
    incident_type: str          # 최종 선택
    source: str                 # "rag" | "keyword"
    reason: str                 # ok | disabled | index_unavailable | embed_failed | low_score | low_margin
    score: float | None         # top1 cosine
    margin: float | None        # top1 - top2
    doc_id: str | None
    candidates: list[tuple[str, float]]
    elapsed_ms: float
```

`keyword_fallback` 기본값은 지연 import로 `agent.graph._classify_incident_type`을 쓴다(순환 import 회피). 테스트에서는 가짜 함수를 주입한다.

## 3. 분류 입력 텍스트

`classifier`는 질의와 모니터링 결과를 **한 문자열**로 합쳐 임베딩한다. 포맷을 고정해야 Before/After 비교가 성립한다.

```text
[사용자 질문] gateway-service에서 payments-service로 가는 요청이 타임아웃 나요
[시스템] gateway-service, payments-service, web-01
[상태] gateway-service=degraded, payments-service=degraded, web-01=healthy
[알림] gateway-service: upstream timeout to payments-service (504), network packet loss 3%; payments-service: CPU 91% (threshold 80%), payments-service-3 instance responding slow
```

규칙
- `collected`에서 `source == "monitoring"`만 사용한다(runbook·analysis 제외).
- 시스템 순서는 `collected` 순서를 유지한다(정렬하지 않음 — 재현성).
- 알림이 없는 시스템은 `[알림]`에서 생략한다.
- 빈 항목은 `-`로 표기한다.
- 이 포맷 문자열은 `classify()` 안에서만 만들고, 별도 함수로 분리해 단위 테스트한다.

## 4. 임베딩

| 항목 | 결정 |
|---|---|
| 기본 모델 | `qwen3-embedding:0.6b` (Ollama) |
| 호출 | `POST {OLLAMA_URL}/api/embed` (`{"model","input"}`) → 실패 시 `/api/embeddings`(`{"model","prompt"}`) 폴백 |
| 정규화 | L2 정규화 후 저장 → cosine = 내적 |
| 타임아웃 | 연결 2s / 읽기 30s (인덱스 빌드 시 문서 수만큼 호출) |
| 폴백 | Ollama 불가 → `HashingEmbedder` (오프라인·결정론, 품질 낮음) |
| 선택 | `RAG_EMBEDDER=auto|ollama|hashing` (기본 `auto`: ollama 시도 후 실패 시 hashing) |

`HashingEmbedder`: 소문자화 → `[a-z0-9-]+` 토큰 + 한글 문자 bigram → blake2b 해시로 512차원 인덱스에 부호 있는 카운트 → L2 정규화. **네트워크·모델 없이 결정론을 보장하는 측정용 대체재**이며, 품질 비교의 주장에는 쓰지 않는다.

실제로 어떤 임베더가 쓰였는지는 `/health`와 `manifest.json`에 기록한다. 기록 없는 측정은 무효다.

## 5. 인덱스

`agent/rag/index.py`가 만들고 `data/runbook_index.json`에 캐시한다(생성물, `.gitignore` 대상).

```json
{
  "schema_version": 1,
  "embedder": {"name": "ollama:qwen3-embedding:0.6b", "dim": 1024, "normalized": true},
  "source": {"runbooks_dir": "data/runbooks", "meta": "data/runbooks/meta.json"},
  "fingerprint": {
    "meta": {"mtime": 1760000000.0, "size": 2140},
    "runbooks": {"high-latency.md": {"mtime": 1760000000.0, "size": 812}}
  },
  "docs": [
    {"id": "high-latency", "title": "응답 지연(High Latency) 대응 절차",
     "text": "...", "vector": [0.0123, "..."]}
  ],
  "built_at": "2026-10-20T15:00:00+09:00"
}
```

무효화 조건(하나라도 다르면 재생성)
1. `schema_version` 불일치
2. `embedder.name` 불일치 (모델 교체)
3. `meta.json`의 mtime·size 불일치
4. `runbooks/*.md`의 **파일 목록·mtime·size** 불일치 (내용 해시는 계산 비용 때문에 캐시 판정에 쓰지 않고, 재생성 후 `index_sha256`로 manifest에 기록)

빌드 시 문서 텍스트 = `title` + `symptoms` + `keywords` + runbook 본문. `meta.json`이 없거나 항목이 빠지면 파일명을 id로, 제목은 첫 `# ` 줄로 대체한다(3단계에서 meta를 10종으로 확장).

검색: 질의 벡터와 문서 벡터의 내적 → 상위 k=3. `k`는 관측용으로만 쓰고 판정은 top1·top2로 한다.

## 6. 판정 규칙

```text
if not enabled           → keyword (reason=disabled)
elif index is None       → keyword (reason=index_unavailable)
elif embed(query) 실패   → keyword (reason=embed_failed)
elif top1_score < MIN_SCORE → keyword (reason=low_score)
elif top1-top2 < MIN_MARGIN → keyword (reason=low_margin)
else                     → rag     (reason=ok)
```

### 6.1 확정값 (2026-10-20, 1단계 측정 후)

| 변수 | 확정값 | 선택 근거 |
|---|---|---|
| `RAG_MIN_SCORE` | `0.50` | 정확도가 0.40~0.55 구간에서 동일(12/12) → 구간 중앙값. 0.60에서 9/12로 떨어짐 |
| `RAG_MIN_MARGIN` | `0.03` | 0.01~0.03 구간 동일 정확도(12/12). 0.02는 관측 경계값 0.0200에 붙어 있어 재현 시 뒤집힘 위험 → 한 단계 위 채택 |

민감도(12문항 개발셋, `eval/rag_threshold_sweep.json`)

| `RAG_MIN_MARGIN` | 정확도 | RAG 판정 | 폴백 |
|---|---|---|---|
| 0.00 | 11/12 | 12 | 0 |
| 0.01 | 12/12 | 11 | 1 |
| 0.02 | 12/12 | 11 | 1 |
| **0.03** | **12/12** | **10** | **2** |
| 0.05 | 11/12 | 9 | 3 |
| 0.08 | 10/12 | 8 | 4 |

| `RAG_MIN_SCORE` | 정확도 | RAG 판정 | 폴백 |
|---|---|---|---|
| 0.40 | 12/12 | 10 | 2 |
| 0.45 | 12/12 | 10 | 2 |
| **0.50** | **12/12** | **10** | **2** |
| 0.55 | 12/12 | 10 | 2 |
| 0.60 | 9/12 | 5 | 7 |
| 0.65 | 8/12 | 1 | 11 |

**해석의 한계 (그대로 보고서에 쓴다)**

- 이 표는 **12문항 개발셋**이다. 임계값을 이 표에서 최댓값으로 고르면 과적합이다. 그래서 "정확도가 평탄한 구간의 중앙값"을 규칙으로 삼았다.
- `RAG_MIN_SCORE=0.50`은 이 12문항에서 **아무것도 걸러내지 못했다**(최저 top1 = 0.5533). 미지 입력의 하한 안전장치이며, 12문항으로 검증된 값이 아니다.
- `RAG_MIN_MARGIN`은 실제로 오분류 1건을 막았다 — B01의 top1은 `high-latency`(오답, 0.5834)였고 2위 `cpu-spike`와 차이가 0.0065였다. 폴백이 정답을 냈다.
- 정확도 12/12를 "일반화 성능"으로 쓰지 않는다. 확장 40문항(3단계) 결과가 본 측정이다.


## 7. 폴백과 관측

| 상황 | 동작 | 관측값 |
|---|---|---|
| `RAG_ENABLED=false` | keyword | `source=keyword, reason=disabled` |
| Ollama 없음 / 인덱스 없음 | keyword | `reason=index_unavailable` |
| 질의 임베딩 실패 | keyword | `reason=embed_failed` |
| 유사도 낮음 | keyword | `reason=low_score, score` |
| 1·2위 차이 작음 | keyword | `reason=low_margin, margin` |

노출 위치
- `ReplanCheck` 이벤트: `source`, `reason`, `score`, `margin`, `doc_id`
- `/chat` `metadata`: `incident_type`, `classifier_source`, `rag_score`, `rag_margin`
- `/health`: `rag.enabled`, `rag.embedder`, `rag.docs`, `rag.index_sha256`, `rag.min_score`, `rag.min_margin`

## 8. 데이터 프로파일 (E8과의 경계)

`data/AGENTS.md` 동결 규칙에 따라 **기존 파일을 덮어쓰지 않는다.**

| 파일 | 처리 |
|---|---|
| `data/monitoring.json` (6시스템) | **그대로 유지** — 기준선·ablation 입력 |
| `data/monitoring_extended.json` (12시스템) | 3단계에서 신규 |
| `data/runbooks/*.md` (6종) | 유지 |
| `data/runbooks/{connection-pool,cert-expiry,replication-lag,queue-backlog}.md` | 3단계에서 신규 |
| `data/runbooks/meta.json` | **1단계에서 6종으로 시작**, 3단계에서 10종 확장 |

`mcp_server.py`는 `DATA_PROFILE=base|extended`(기본 `extended`)로 `monitoring*.json`을 고른다. 인덱스는 runbook 디렉터리를 공유하므로 프로파일과 무관하다. **측정 조건에 `DATA_PROFILE`을 반드시 기록한다.**

`meta.json` 스키마

```json
{
  "schema_version": 1,
  "incident_types": {
    "high-latency": {
      "title": "응답 지연(High Latency) 대응 절차",
      "systems": ["auth-service", "payments-service"],
      "symptoms": ["p95 지연 증가", "커넥션 풀 고갈", "응답 지연"],
      "keywords": ["latency", "pool", "slow", "지연"]
    }
  }
}
```

## 9. 측정 계획 (1단계 완료 판정)

| # | 확인할 것 | 방법 | 판정 |
|---|---|---|---|
| 1 | 인덱스 생성·캐시 재사용 | 1회차 빌드 로그, 2회차 `cache_hit=true` | 두 번째 실행에서 재생성 0회 |
| 2 | 기준선 대비 정확도 | `eval/run_eval.py --variant after-rag` (4단계에서 정식화, 1단계는 임시 스크립트로 동일 측정) | 12문항 **0.6667 초과** |
| 3 | 폴백 동작 | `RAG_MIN_SCORE=0.99` 강제 실행 | keyword 결과와 동일, `reason=low_score` |
| 4 | 비활성 동작 | `RAG_ENABLED=false` | `eval/baseline_keyword.json`과 문항별 예측 동일 |

### 9.1 1단계 측정 결과 (2026-10-20)

측정 원본: `eval/rag_probe.json`, `eval/rag_probe.run2.json`, `eval/rag_threshold_sweep.json`

| 항목 | 값 |
|---|---|
| 임베더 | `ollama:qwen3-embedding:0.6b`, dim 1024 (오프라인 폴백 아님) |
| 인덱스 | runbook 6종, `index_sha256=3acb3580…`, `built_at` 고정 |
| 정확도 | **12/12 = 1.0000** (기준선 8/12 = 0.6667) |
| RAG 판정 / 폴백 | 10 / 2 (B01·B06 `low_margin`) |
| 폴백 2건의 결과 | 둘 다 keyword 정답 — 폴백이 정확도를 깎지 않았다 |
| 캐시 | 같은 프로세스 2회차 `cache_hit=True`, 다음 프로세스 첫 적재도 `cache_hit=True` |
| 결정론 | 2회 실행에서 `elapsed_ms`만 다름. items·accuracy·index_sha256 동일 |
| 4가지 확인 | 캐시 재사용·정확도·강제 저신뢰·비활성 **전부 PASS** |

**중요**: B01은 RAG 1위가 `high-latency`(오답)였고, margin 게이트가 keyword로 되돌려 정답을 냈다. 즉 12/12에는 RAG의 힘과 폴백의 힘이 섞여 있다. `classifier_source`를 빼고 "RAG 정확도"라고 쓰면 안 된다.

### 9.2 2단계 E2E 결과 (2026-10-20)

측정 원본: `eval/e2e_probe.json`(RAG on), `eval/e2e_probe_rag_off.json`(RAG off), 스크립트 `eval/run_e2e_probe.py`

서버: `LLM_BACKEND=fake`, `SUPERVISOR_VERSION=v2`, `LANGCHAIN_TRACING_V2=false`, 포트 8100.
`/health.rag` = `{enabled: true, embedder: "ollama:qwen3-embedding:0.6b", dim: 1024, docs: 6, cache_hit: true, min_score: 0.5, min_margin: 0.03, error: null}` — 1단계 인덱스(`index_sha256=3acb3580…`)를 재사용했다.

| ID | 질의 요지 | RAG on | RAG off (같은 코드) |
|---|---|---|---|
| E01 | gateway→payments 타임아웃 | `network-timeout` (rag, ok, 0.5450 / 0.0415) | `cpu-spike` (keyword, disabled) |
| E02 | auth-service 디스크 부족 | `disk-full` (rag, ok, 0.5580 / 0.1310) | `high-latency` (keyword, disabled) |
| E03 | auth-service p95 지연 | `high-latency` (rag, ok, 0.6413 / 0.2247) | `high-latency` (keyword, disabled) |
| C01 | 잡담 | `route=chat`, `incident_type=null` | 동일 |

- E2E 정확도: on **3/3**, off **1/3**. off 결과는 0단계 기준선 오분류(B07 `cpu-spike`, B10 `high-latency`)와 같은 방향이다.
- SSE `/chat/stream`: `ReplanCheck` 이벤트에 `target`, `classifier_source`, `classifier_reason`, `rag_score`, `rag_margin`이 실려 나오고 `FinalAnswer`에도 `incident_type`·`classifier_source`가 포함된다.
- `SUPERVISOR_VERSION=v1` 스모크: 서버는 뜨고 `/health.rag`도 노출되지만 legacy 경로는 분류를 쓰지 않으므로 metadata는 `null`이다(의도).

**측정 조건 주의**: E2E 입력에는 `, 원인 진단해주세요`를 덧붙였다. 기존 `fake` 라우터가 `장애|진단|다운|지연|급증|incident|티켓` 키워드로만 incident 경로를 타기 때문이며, RAG와 무관한 기존 동작이다. 그래서 **분류 정확도 주장은 동결 12문항(`eval/rag_probe.json`)으로만** 하고, E2E는 배선 증거로만 쓴다.

### 9.3 3단계 결과 — 데이터 확장과 ablation (2026-10-20)

측정 원본: `eval/ablation.json`, `eval/baseline_extended_keyword.json`, `eval/rag_probe_extended.json`, `eval/rag_probe_extended_on_base.json`, `eval/profile_probe.json`, `eval/e2e_probe_extended.json`

데이터: `data/monitoring.json`(base 6) 그대로 + `data/monitoring_extended.json`(12) 신규. 런북 6 + 신규 4 = 10종. 라벨 `eval/labels_extended.json` 40문항(10유형 × 4카테고리) **측정 전 동결**. 인덱스는 10문서 `index_sha256=bfdc27ec…`.

#### (1) 40문항 — 3군 비교

| 군 | 조건 | 정확도 | single | multi | ambiguous | no_system |
|---|---|---|---|---|---|---|
| A | keyword + base | 13/40 = 0.3250 | 6/10 | 6/10 | 0/10 | 1/10 |
| B | RAG + base | 34/40 = **0.8500** | 10/10 | 10/10 | 5/10 | 9/10 |
| C | RAG + extended | 34/40 = **0.8500** | 10/10 | 10/10 | 5/10 | 9/10 |
| – | keyword + extended (참고) | 13/40 = 0.3250 | 6/10 | 6/10 | 0/10 | 1/10 |

- **A→B = RAG 도입 효과: +0.5250.**
- **B→C = 데이터 확장 효과: 정확도 차이 0.** 40문항에서 예측이 문항 단위로 동일했다.

#### (2) 데이터 확장은 정확도가 아니라 coverage를 바꾼다

| 프로파일 | 시스템 | 40문항이 조회한 시스템 수 | unknown | unknown 비율 |
|---|---|---|---|---|
| base | 6 | 80 | 15 | **18.75%** |
| extended | 12 | 80 | 0 | **0.00%** |

E2E 확인(`eval/e2e_probe_base_profile.json`, `eval/e2e_probe_extended.json`):
- `DATA_PROFILE=base` + `search-service` 질의 → 분류는 `queue-backlog`(질의 텍스트로 맞힘)이지만 `systems_unknown=["search-service"]` — **모니터링 근거 없이** 답한 것이다.
- `DATA_PROFILE=extended` → 같은 질의에서 `systems_unknown=[]`, `/health.rag.docs=10`.

**해석(그대로 보고서에 쓴다)**: 이 40문항에서 데이터 확장이 정확도를 올리지 못한 이유는 라벨이 질의에 증상을 명시하고 RAG가 질의를 읽기 때문이다. 시스템 상태·알림은 보조 신호로 쓰였다. 따라서 "데이터를 늘려서 정확도가 올랐다"고 쓰면 **측정과 어긋난다**. 확장의 효과는 ① 새 시스템을 실제로 조사할 수 있음(coverage 18.75% → 0%) ② keyword가 표현 자체를 못 하는 4개 유형이 생김(A군 6/10, B군 10/10)으로 서술한다.

#### (3) 12문항 재측정 (10문서 인덱스)

`eval/rag_probe_after_expand.json` = **12/12 유지**(RAG 10, 폴백 2). 확장 전 `3acb3580…`(6문서)와 확장 후 `bfdc27ec…`(10문서)는 서로 다른 인덱스이며, 확장 전 수치는 이력으로만 남긴다.

#### (4) 임계값 재검증 — 유지 결정

| min_margin | 40문항 정확도 | RAG 판정 | 폴백 |
|---|---|---|---|
| 0.00 | 36/40 = 0.9000 | 38 | 2 |
| 0.01 | 36/40 = 0.9000 | 37 | 3 |
| 0.02 | 35/40 = 0.8750 | 35 | 5 |
| **0.03 (채택)** | **34/40 = 0.8500** | 34 | 6 |
| 0.04 | 34/40 = 0.8500 | 34 | 6 |
| 0.05 | 31/40 = 0.7750 | 31 | 9 |

`min_score`는 0.40~0.50에서 34/40으로 평탄, 0.55에서 32/40, 0.60에서 27/40이었다(`eval/rag_threshold_sweep_extended.json`).

**0.03을 유지한 이유**: 0.00으로 풀면 같은 40문항에서 2문항이 더 맞지만, 그 2문항(X24·X32)은 top1·top2가 0.0155·0.0000 차이인 **사실상 동점**이다. 1단계에서 B01이 바로 이런 동점에서 오답이었고 margin 게이트가 막았다. 이 데이터에서 최댓값을 좇으면 과적합이므로 0.03을 유지하고, **보수적 폴백 비용 2문항을 트레이드오프로 기록**한다.

### 9.5 최종 검증 — 문서 수치 ↔ 원본 일치 (2026-10-20, 마무리 단계)

`eval/check_reported_numbers.py`가 슬라이드·보고서·스프레드시트 본문·README·체크리스트에
적힌 수치가 측정 원본(`doc/reports/evidence/metrics/`)과 같은지 대조한다. **13/13 PASS.**

검사 중 실제 오류 1건을 잡았다: coverage(extended) 값을 base 실행 폴더에서 읽는 **원본 매핑 오류**였다.
값 자체는 맞았고 표기가 틀릴 뻔한 건이었다(0.00%가 아니라 18.75%로 인용될 상황).
고친 뒤 폴백률(15.00%)이 슬라이드·보고서·체크리스트에 없던 것도 함께 추가했다.
이 검사기는 이후 숫자를 바꾸면 바로 알려 주므로, 보고서 수치가 원본에서 벌어지는 일이 없다.

### 9.4 4단계 결과 — 평가 하네스 정식화 (2026-10-20)

측정 원본: `artifacts/runs/<run_id>/` (실행 1회 = 폴더 1개) → 요약 `doc/reports/evidence/{before_after.md,metrics/}`

#### (1) 무엇을 만들었나

| 파일 | 역할 |
|---|---|
| `eval/run_eval.py` | 통합 하네스. `--variant before-rag\|after-rag`, `--mode classify\|e2e`, `--repeat N`. 실행마다 `artifacts/runs/<run_id>/`에 `manifest.json`(조건·해시·git)·`metrics.json`(지표)·`requests.jsonl`·`responses.jsonl`·`notes.md` 생성 |
| `eval/metrics.py` | accuracy·macro-F1·혼동행렬·카테고리별·폴백률·커버리지·percentile·재현성 판정 (단위 테스트 대상) |
| `eval/make_before_after.py` | run 폴더 2개 → Before/After 표 + 요약 JSON 자동 생성 (숫자를 손으로 옮겨 적지 않는다) |
| `eval/e2e_cases.json` | E2E 고정 입력 1곳 (probe·하네스 공용) |
| `tests/` | unit 5종 + integration 2종 = **50개 통과** |
| `agent/rag/index.py::resolve_index_path` | `RAG_INDEX_PATH`로 인덱스 캐시 경로 교체 — 테스트가 측정 캐시를 덮어쓰지 않게 |

#### (2) Before/After (하네스 실행 1회 기준)

| 지표 | Before (keyword) | After (RAG) | 차이 |
|---|---|---|---|
| 40문항 정확도 | 13/40 = 0.3250 | 34/40 = 0.8500 | +0.5250 |
| macro-F1 | 0.2836 | 0.8521 | +0.5685 |
| 폴백률(keyword) | 100.00% | 15.00% | −85.00%p |
| 분류 지연 p50 | 0.0ms (0.01ms 미만) | 32.43ms | +32.43ms |
| 분류 지연 p95 | 0.0ms | 37.14ms | +37.14ms |
| E2E 5문항 | 1/5 = 0.2000 | 5/5 = 1.0000 | +0.8000 |
| E2E 요청 p50 | 750.76ms | 819.73ms | +68.97ms |
| 비용 | $0.000000 | $0.000000 | 0 (로컬 백엔드) |
| 재현성(2회 반복) | — | identical | — |

#### (3) 새로 드러난 사실 두 가지

1. **RAG의 비용은 임베딩 1회 호출이다.** 분류 지연 p50 +32.43ms, p95 +37.14ms. E2E 요청 전체로는 +68.97ms(요청 p50 750.76ms → 819.73ms). 실서버 응답 지연의 약 9% 수준.
2. **E2E 하네스가 SSE 근거를 잃는 버그를 잡았다.** `ReplanCheck`는 round 0에 `target`, round 1에 `incident_type`이 들어 있어 이벤트를 하나만 잡으면 근거가 반쪽이다. `eval/run_eval.py`는 두 라운드를 합친다. 이전 실행(`20261020-152539`, `20261020-152546`, `20261020-152647`, `20261020-152654`)은 이 버그 때문에 S01이 오분류로 잡혔다. 실패한 시도를 지우지 않고 `doc/reports/evidence/index.md`에 남겼다.
3. **서버 측 조건도 기록해야 한다.** `RAG_ENABLED`은 서버 프로세스의 환경이라 클라이언트 env만으로는 "같은 조건"을 증명할 수 없다. 하네스가 `/health`를 읽어 서버 상태(RAG on/off·임베더·인덱스 해시·임계값)를 manifest에 함께 남긴다.

#### (4) 한계 (이 단계가 만든 것)

- **테스트는 "개발셋"이다.** `tests/unit/test_keyword_classifier.py`는 keyword의 알려진 결함(규칙 순서: cpu가 timeout보다 앞)까지 **의도된 동작**으로 고정한다. 고치려면 기준선(`eval/baseline_keyword.json`)을 다시 측정해야 한다.
- **하네스는 로컬 백엔드 기준이다.** 비용 $0은 `fake`/`ollama`라서 그렇다. 실 API 비용은 `LLM_BACKEND=openai`로 다시 돌려야 한다.
- **지연 측정은 프로세스 내부 단일 실행 기준이다.** 동시 요청·워밍 상태는 반영하지 않는다.




## 10. 테스트 계획

- `tests/unit/test_rag_embedder.py` — HashingEmbedder 결정론(같은 입력 = 같은 벡터), L2 정규화
- `tests/unit/test_rag_index.py` — 캐시 무효화 4조건 각각, top-k 순서
- `tests/unit/test_rag_classifier.py` — 판정 5분기, 강제 저점수 폴백, keyword fallback 주입
- `tests/integration/test_graph_rag.py` — `replan_check_node`가 `deps.rag` 결과를 이벤트에 반영

## 11. 한계·리스크 (보고서 6장에 수치와 함께 기록)

| 리스크 | 내용 | 완화 |
|---|---|---|
| 작은 코퍼스 | runbook 10개 → 유사도 분포가 좁아 margin 판정이 흔들릴 수 있음 | margin 스윕 결과를 문서화, 폴백률 지표로 감시 |
| 임계값 민감도 | `MIN_SCORE` 0.01 변화로 분류가 바뀔 수 있음 | 민감도 표를 부록에 남김 |
| 임베딩 모델 의존 | `HashingEmbedder`로 떨어지면 품질이 급락 | `/health`·manifest에 임베더 기록, 비교는 같은 임베더에서만 |
| 지연 증가 | 질의 1회 임베딩 추가 (Ollama 로컬 호출) | 분류 p50/p95 측정, 인덱스는 기동 시 1회 |
| 질의-데이터 불일치 | 사용자 신고와 모니터링이 다를 때 라벨 근거가 약함 | 라벨에 `rationale` 기록(이미 적용), 불일치 문항을 별도 카테고리로 집계 |
| JSON 인덱스 | 스케일 아웃·동시 쓰기에 부적합 | 규모 근거와 함께 한계로 명시 |

## 12. 이 단계에서 하지 않는 것

- `agent/graph.py` 수정 (2단계)
- `server.py` 수정 (2단계)
- `data/monitoring_extended.json`·신규 runbook 4종·meta 10종 (3단계)
- `eval/run_eval.py`·`eval/metrics.py` 정식화 (4단계)

## 13. 승인 후 작성할 파일

| 파일 | 내용 |
|---|---|
| `agent/rag/__init__.py` | 패키지 |
| `agent/rag/embedder.py` | `OllamaEmbedder`, `HashingEmbedder`, `build_embedder()` |
| `agent/rag/index.py` | `RagIndex`, `build_index()`, `load_or_build()`, 검색 |
| `agent/rag/classifier.py` | `RagClassifier`, `ClassifyResult`, 입력 포맷 함수 |
| `data/runbooks/meta.json` | 6종 초기 메타 |
