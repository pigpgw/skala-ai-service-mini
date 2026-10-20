# AGENTS.md — tests/ (테스트)

상위: 루트 `AGENTS.md`. 여기에는 **검증 코드만** 둔다. 측정 원본·보고서는 `doc/`·`artifacts/`에 둔다.

## 파일

| 경로 | 역할 |
|---|---|
| `conftest.py` | `agent`·`eval` 모듈을 임포트할 수 있게 `sys.path` 정리 |
| `unit/test_metrics.py` | 지표 계산기 (accuracy·macro-F1·혼동행렬·percentile) |
| `unit/test_data_profile.py` | `DATA_PROFILE=base|extended` 선택 규칙 |
| `unit/test_monitoring_data.py` | `data/` 입력 무결성 (시스템 6/12, 런북 10종 1:1 대응) |
| `unit/test_classifier_gate.py` | RAG 판정 5분기(disabled·index_unavailable·embed_failed·low_score·low_margin) |
| `unit/test_keyword_classifier.py` | keyword 경로의 현재 동작을 고정한 characterization |
| `integration/test_mcp_server.py` | MCP stdio subprocess — Tool·Resource·Prompt, 프로파일 상속 |
| `integration/test_api.py` | FastAPI TestClient — `/health`·`/version`·`/chat`·`/chat/stream` 계약 |

## 규칙

- **네트워크에 의존하지 않는다.** RAG 임베딩은 `HashingEmbedder` + 임시 인덱스 경로를 쓴다.
- **측정용 캐시를 건드리지 않는다.** `data/runbook_index.json`을 테스트가 덮어쓰면 "이번 측정의 인덱스가 뭐였는지"가 사라진다.
  인덱스 경로는 `RAG_INDEX_PATH` 환경변수로 바꾼다(`agent/rag/index.py::resolve_index_path`).
- **RAG는 꺼고 API를 테스트한다.** RAG 경로 자체는 `unit/test_classifier_gate.py`가 담당한다.
  (`RAG_ENABLED=0` + `LLM_BACKEND=fake` 고정)
- characterization 테스트(현재 동작을 고정한 것)는 **의도된 동작**이다. 규칙을 바꿀 때는
  기준선(`eval/baseline_keyword.json`)을 다시 측정하고 함께 고친다.

## 실행

```bash
.venv/bin/pip install -r requirements-dev.txt   # 최초 1회
.venv/bin/python -m pytest                      # 전체
.venv/bin/python -m pytest tests/unit           # 단위만
```

`pytest.ini`가 `testpaths = tests`와 `-q --strict-markers`를 지정한다.

## 금지

- 테스트가 실제 측정 결과를 "기대값"으로 하드코딩하는 것(측정 원본은 `artifacts/`에 있다)
- 테스트가 `data/` 파일을 수정하는 것(측정 입력은 동결이다)
- 테스트가 `.env`·API 키를 읽는 것
