# 증거 대조표 (주장 ↔ 증거 ↔ 재현 명령)

- 작성일: 2026-10-20
- 규칙: **아래 숫자는 원본 파일에서 읽었다.** 원본은 `artifacts/runs/<run_id>/` (커밋 안 함, 재생성 가능).
  표에 적힌 `doc/reports/evidence/metrics/<run_id>.json`은 원본에서 잘라낸 요약본(커밋 대상)이다.

| # | 주장 | 수치 | 증거 파일 | 재현 명령 | 작성일 |
|---|---|---|---|---|---|
| 1 | RAG 도입으로 40문항 분류 정확도가 올랐다 | 13/40 = 0.3250 → 34/40 = 0.8500 (+0.5250) | `artifacts/runs/20261020-152756_fake_{before,after}-rag/metrics.json`, 요약본 `doc/reports/evidence/metrics/20261020-152756_fake_*.json` | `.venv/bin/python eval/run_eval.py --variant before-rag --profile extended` / `--variant after-rag --profile extended --repeat 2` | 2026-10-20 |
| 2 | 유형 불균형도 줄었다 | macro-F1 0.2836 → 0.8521 (+0.5685) | 위와 동일 (`metrics.json`의 `macro_f1`, `per_type`) | 위와 동일 | 2026-10-20 |
| 3 | 실제 서버 경로(E2E)에서도 같게 개선된다 | 5문항 1/5 = 0.2000 → 5/5 = 1.0000 | `artifacts/runs/20261020-153204_fake_before-rag/`, `artifacts/runs/20261020-153211_fake_after-rag/` | 서버 기동 후 `.venv/bin/python eval/run_eval.py --variant after-rag --mode e2e` | 2026-10-20 |
| 4 | 데이터 확장(6→12시스템)의 효과는 **정확도가 아니라 커버리지**다 | unknown 18.75% → 0.00% (80회 조회 기준) | `artifacts/runs/20261020-152800_fake_{before,after}-rag/metrics.json`의 `coverage`, `eval/ablation.json` | `--profile base` / `--profile extended` 로 각각 실행 | 2026-10-20 |
| 5 | 데이터 확장은 분류 정확도를 바꾸지 못했다 (한계) | base 34/40 = 0.8500 ≡ extended 34/40 = 0.8500 | `doc/reports/evidence/before_after.md` 2·3절 | 위와 동일 | 2026-10-20 |
| 6 | RAG의 비용은 분류당 임베딩 1회 호출이다 | 분류 지연 p50 +32.43ms, p95 +37.14ms, 폴백률 15.00% | `artifacts/runs/20261020-152756_fake_{before,after}-rag/metrics.json`의 `latency`, `fallback` | 위와 동일 | 2026-10-20 |
| 6b | 실서버 요청 지연도 늘지만 10% 미만이다 | E2E 요청 p50 750.76ms → 819.73ms (+68.97ms) | `artifacts/runs/20261020-153204_fake_before-rag/`, `20261020-153211_fake_after-rag/`의 `latency` | 위와 동일 | 2026-10-20 |
| 7 | 같은 조건 2회 실행은 재현된다 | `reproducibility.identical = true` (2회 반복) | `artifacts/runs/20261020-152756_fake_after-rag/metrics.json`의 `reproducibility` | `--repeat 2` | 2026-10-20 |
| 8 | margin 게이트는 보수적 폴백 비용을 만든다 (한계) | 40문항에서 margin 0.03 → 34/40, 0.00 → 36/40 (2문항 차이) | `eval/rag_threshold_sweep_extended.json` | `.venv/bin/python eval/run_threshold_sweep.py --probe eval/rag_probe_extended.json --baseline eval/baseline_extended_keyword.json --out eval/rag_threshold_sweep_extended.json` | 2026-10-20 |
| 9 | 논리 변경은 테스트로 고정했다 | 테스트 50개 통과 (`pytest`) | `tests/unit/`, `tests/integration/` | `.venv/bin/python -m pytest` | 2026-10-20 |
| 10 | 프로파일 값이 MCP subprocess까지 전달된다 | base 6시스템 / extended 12시스템, `billing-service`는 계속 unknown | `eval/profile_probe.json`, `tests/integration/test_mcp_server.py` | `.venv/bin/python eval/run_profile_probe.py` | 2026-10-20 |
| 11 | 문서에 적힌 수치가 측정 원본과 일치한다 | 13개 주장 13/13 PASS (정확도·macro-F1·E2E·지연·커버리지·폴백률·재현성) | `eval/reported_numbers_check.json`, `doc/reports/rehearsal_log.md` | `.venv/bin/python eval/check_reported_numbers.py` | 2026-10-20 |
| 12 | 시연 경로가 실제로 동작한다 | health 0.03s · 채팅 3건 1.29s/0.81s/0.80s (high-latency·queue-backlog·billing-service 폴백) | `doc/reports/rehearsal_log.md`, `var/logs/rehearsal.log` | 서버 기동 후 위 4개 명령 실행 | 2026-10-20 |

## 이전 실행(인용하지 않음)

- `artifacts/runs/20261020-152539_fake_*`, `20261020-152546_fake_*`, `20261020-152647_fake_*`, `20261020-152654_fake_*` —
  E2E 하네스가 SSE `ReplanCheck` 이벤트를 라운드별로 덮어써 근거를 잃던 버그를 가진 실행이다.
  수정 후 재실행한 것이 위 표의 1·3번이다. 실패한 시도를 지우지 않고 남긴다(`doc/AGENTS.md` 금지 조항).
- `doc/reports/evidence/metrics/`에는 **위 표에서 인용한 run의 요약본만** 커밋한다.
  나머지 run의 원본은 `artifacts/runs/`(커밋 안 함)에 남아 있고, 재생성할 수 있다.
