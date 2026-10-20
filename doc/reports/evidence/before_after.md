# Before/After 비교 (원본 인용)

- 생성 시각: 2026-10-20T15:32:20+09:00
- 이 표의 모든 숫자는 `artifacts/runs/<run_id>/metrics.json`에서 읽었다.
- 같은 조건(동일 입력·동일 데이터·동일 임베더·동일 임계값)에서 2회 실행한 결과다.

### 40문항 분류 정확도 (DATA_PROFILE=extended, fake 백엔드)

| 항목 | Before | After | 차이 |
|---|---|---|---|
| 실행(run_id) | 20261020-152756_fake_before-rag | 20261020-152756_fake_after-rag | — |
| 정확도 | 13/40 = 0.3250 | 34/40 = 0.8500 | +0.5250 |
| macro-F1 | 0.2836 | 0.8521 | +0.5685 |
| 폴백률(keyword) | 100.00% | 15.00% | -85.00% |
| 조사 커버리지(unknown) | 0.00% | 0.00% | +0.00% |
| 지연 p50 | 0.0ms | 32.43ms | +32.43ms |
| 지연 p95 | 0.0ms | 37.14ms | +37.14ms |

**측정 조건**

- Before: backend=fake, profile=extended, dataset=`eval/labels_extended.json` (sha 994775da26ee), git=923514e, env={"LLM_BACKEND": "fake", "RAG_ENABLED": "true", "RAG_MIN_SCORE": "0.50", "RAG_MIN_MARGIN": "0.03"}
- After: backend=fake, profile=extended, dataset=`eval/labels_extended.json` (sha 994775da26ee), git=923514e, env={"LLM_BACKEND": "fake", "RAG_ENABLED": "true", "RAG_MIN_SCORE": "0.50", "RAG_MIN_MARGIN": "0.03"}

**재현 명령**

```bash
.venv/bin/python eval/run_eval.py --variant before-rag --profile extended
.venv/bin/python eval/run_eval.py --variant after-rag --profile extended --repeat 2
```

| 카테고리 | Before | After |
|---|---|---|
| single | 6/10 | 10/10 |
| multi | 6/10 | 10/10 |
| ambiguous | 0/10 | 5/10 |
| no_system | 1/10 | 9/10 |

**오분류**

- Before: X07→db-down, X08→db-down, X09→high-latency, X10→db-down, X17→db-down, X18→db-down, X19→high-latency, X20→db-down, X21→db-down, X22→db-down, X23→db-down, X24→db-down, X25→high-latency, X26→memory-leak, X27→network-timeout, X28→disk-full, X29→cpu-spike, X30→high-latency, X32→high-latency, X33→high-latency, X34→high-latency, X35→high-latency, X36→high-latency, X37→high-latency, X38→high-latency, X39→high-latency, X40→high-latency
- After: X22→db-down, X24→db-down, X25→high-latency, X26→memory-leak, X30→high-latency, X32→high-latency

원본: `artifacts/runs/20261020-152756_fake_before-rag/` · `artifacts/runs/20261020-152756_fake_after-rag/`

### 40문항 분류 정확도 (DATA_PROFILE=base, fake 백엔드)

| 항목 | Before | After | 차이 |
|---|---|---|---|
| 실행(run_id) | 20261020-152800_fake_before-rag | 20261020-152800_fake_after-rag | — |
| 정확도 | 13/40 = 0.3250 | 34/40 = 0.8500 | +0.5250 |
| macro-F1 | 0.2849 | 0.8537 | +0.5688 |
| 폴백률(keyword) | 100.00% | 20.00% | -80.00% |
| 조사 커버리지(unknown) | 18.75% | 18.75% | +0.00% |
| 지연 p50 | 0.0ms | 31.92ms | +31.92ms |
| 지연 p95 | 0.0ms | 34.54ms | +34.54ms |

**측정 조건**

- Before: backend=fake, profile=base, dataset=`eval/labels_extended.json` (sha 994775da26ee), git=923514e, env={"LLM_BACKEND": "fake", "RAG_ENABLED": "true", "RAG_MIN_SCORE": "0.50", "RAG_MIN_MARGIN": "0.03"}
- After: backend=fake, profile=base, dataset=`eval/labels_extended.json` (sha 994775da26ee), git=923514e, env={"LLM_BACKEND": "fake", "RAG_ENABLED": "true", "RAG_MIN_SCORE": "0.50", "RAG_MIN_MARGIN": "0.03"}

**재현 명령**

```bash
.venv/bin/python eval/run_eval.py --variant before-rag --profile base
.venv/bin/python eval/run_eval.py --variant after-rag --profile base
```

| 카테고리 | Before | After |
|---|---|---|
| single | 6/10 | 10/10 |
| multi | 6/10 | 10/10 |
| ambiguous | 0/10 | 5/10 |
| no_system | 1/10 | 9/10 |

**오분류**

- Before: X07→db-down, X08→db-down, X09→db-down, X10→db-down, X17→db-down, X18→db-down, X19→db-down, X20→db-down, X21→db-down, X22→db-down, X23→db-down, X24→db-down, X25→db-down, X26→memory-leak, X27→network-timeout, X28→disk-full, X29→cpu-spike, X30→high-latency, X32→high-latency, X33→high-latency, X34→high-latency, X35→high-latency, X36→high-latency, X37→high-latency, X38→high-latency, X39→high-latency, X40→high-latency
- After: X21→db-down, X22→db-down, X25→db-down, X26→memory-leak, X30→high-latency, X32→high-latency

원본: `artifacts/runs/20261020-152800_fake_before-rag/` · `artifacts/runs/20261020-152800_fake_after-rag/`

### E2E 5문항 (실서버 :8100, fake 백엔드)

| 항목 | Before | After | 차이 |
|---|---|---|---|
| 실행(run_id) | 20261020-153204_fake_before-rag | 20261020-153211_fake_after-rag | — |
| 정확도 | 1/5 = 0.2000 | 5/5 = 1.0000 | +0.8000 |
| 지연 p50 | 750.76ms | 819.73ms | +68.97ms |
| 지연 p95 | 1074.92ms | 1151.16ms | +76.24ms |
| 비용(USD) | 0.000000 | 0.000000 | +0.000000 |
| retry 합계 | 1 | 1 | — |

**측정 조건**

- Before: backend=fake, profile=extended, dataset=`eval/labels_extended.json` (sha 994775da26ee), git=923514e, env={"LLM_BACKEND": "fake", "DATA_PROFILE": "extended"}
  - Before 서버: RAG_ENABLED=False, embedder=None, docs=0, index=None, min_score=0.5, min_margin=0.03
- After: backend=fake, profile=extended, dataset=`eval/labels_extended.json` (sha 994775da26ee), git=923514e, env={"LLM_BACKEND": "fake", "DATA_PROFILE": "extended"}
  - After 서버: RAG_ENABLED=True, embedder=ollama:qwen3-embedding:0.6b, docs=10, index=bfdc27ec9b9f, min_score=0.5, min_margin=0.03

**재현 명령**

```bash
.venv/bin/python eval/run_eval.py --variant before-rag --mode e2e
.venv/bin/python eval/run_eval.py --variant after-rag --mode e2e
```

**오분류**

- Before: E01→cpu-spike, E02→high-latency, E04→db-down, S01→memory-leak
- After: 없음

원본: `artifacts/runs/20261020-153204_fake_before-rag/` · `artifacts/runs/20261020-153211_fake_after-rag/`

