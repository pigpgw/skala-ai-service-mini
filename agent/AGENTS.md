# AGENTS.md — agent/ (런타임 코드)

상위: 루트 `AGENTS.md`. 이 폴더 규칙이 더 구체적이면 이 문서를 따른다.
여기에는 **실행에 쓰이는 코드만** 둔다. 측정 산출물·초안·캡처는 이 폴더에 넣지 않는다.

## 파일

| 파일 | 역할 |
|---|---|
| `graph.py` | LangGraph v2 그래프 (`build_graph`, 노드 10개, `AgentState`) |
| `supervisor_v1.py` | legacy 선형 파이프라인 (`SUPERVISOR_VERSION=v1`) |
| `deps.py` | `SupervisorDeps` — 노드에 주입되는 의존성 묶음 |
| `fake_llm.py` | 결정론 백엔드 (`LLM_BACKEND=fake`) — 테스트·기준선용 |
| `ollama_llm.py` | 로컬 실모델 백엔드 |
| `openai_llm.py` | 실제 API 백엔드 (과금) |
| `mcp_client.py` | MCP stdio 클라이언트 (Tool·Resource·Prompt, ops/docs 세션) |
| `session_store.py` | SQLite 세션 저장소 (재시작 후에도 대화 유지) |
| `retry.py` | `with_retry` — 일시적 오류만 exponential backoff |

## 노드 계약

- 노드 함수는 상태를 받아 상태 조각(dict)을 돌려준다. 부수효과로 상태를 직접 바꾸지 않는다.
- 노드는 `functools.partial(node, deps=deps)`로 주입돼 `build_graph` 안에서 조립된다. 노드가 전역 변수나 closure 지역 변수에 의존하면 안 된다.
- 상태 키는 `AgentState(TypedDict, total=False)`에 있다. 노드가 읽고 쓰는 키를 새로 만들려면 먼저 `AgentState`에 추가한다.

| 키 | 의미 |
|---|---|
| `query`, `thread_id`, `history` | 입력과 대화 이력 |
| `route` | `chat` / `incident` 분기 결과 |
| `needs_analysis`, `tasks`, `gate_removed` | 계획·게이트 단계 |
| `collected`, `replan_rounds`, `retry_count` | 수집 결과와 재계획·재시도 횟수 (측정 지표) |
| `draft`, `validation_attempts`, `validation_feedback` | 작성·검증 반복 |
| `final`, `last_prompt`, `events` | 최종 응답, 사용한 프롬프트, SSE 이벤트 |

### 새 노드·엣지를 추가할 때

1. `AgentState`에 새 키를 추가한다.
2. 노드 함수를 만들고 `@traceable` 이름을 붙인다 (LangSmith에서 before/after 비교가 가능해야 한다).
3. `build_graph`에 `add_node` + `add_edge`/`add_conditional_edges`를 등록한다.
4. 회귀 질의 세트(`doc/regression_test_queries.md`)로 기존 경로가 안 깨졌는지 확인한다.

## 의존성 주입

- 새 의존성은 `SupervisorDeps`에 필드로 추가하고 `server.py` lifespan에서 만든다.
- 노드에서 `os.environ`을 직접 읽지 않는다. 환경에 따라 달라지는 값은 lifespan에서 한 번 읽어 deps로 넘긴다.
- LLM 인스턴스는 `server.py::_build_llms`에서만 만든다. 노드·그래프 안에서 새로 만들면 요청마다 비용과 지연이 늘고 "프로세스당 1회 생성"(Wave 1) 검증이 깨진다.

## LLM 백엔드

- `fake`/`ollama`/`openai`는 같은 메서드 집합과 `usd_per_1k_tokens`를 유지한다. 이 계약이 있어야 백엔드를 바꿔도 비용 지표를 같은 기준으로 비교할 수 있다.
- 새 백엔드를 추가하면 세 백엔드가 같은 인터페이스를 구현했는지 확인하고, 측정 조건에 백엔드 이름을 적는다.

## MCP

- MCP 호출은 `mcp_client.py`를 통해서만 한다. 노드에서 `mcp_server.py`를 직접 import하거나 subprocess를 새로 띄우지 않는다.
- Tool/Resource/Prompt는 먼저 `list_*`·`find_*`로 탐색한 뒤 요청한다. 이름을 문자열로 하드코딩하지 않는다.
- `server="ops"`가 실사용, `docs`는 decoy다. `docs`를 쓰기 시작하면 의도된 설계를 바꾸는 것이므로 체크리스트에 기록한다.

## 세션

- `SqliteSessionStore.DB_PATH`는 현재 `session.db`(repo 루트)다. 경로를 바꾸면 `sh/run_agent_*.sh`의 `rm -f session.db` 대상도 함께 바꾼다.
- 세션 이력은 LLM 프롬프트에 들어간다. 이력 길이를 바꾸는 개선(요약 압축 등)은 토큰·지연 지표로 측정한다.

## 재시도

- `with_retry`는 `asyncio.TimeoutError`만 재시도하고 `(결과, 재시도 횟수)`를 돌려준다. 재시도 횟수는 `retry_count`로 상태에 남아 측정 지표가 된다. 재시도 정책을 바꾸면 이 반환 형태를 유지한다.

## 금지

- 노드 안에서 blocking 호출로 이벤트 루프를 막는 코드
- API 키·토큰·프롬프트 원문 전체를 로그나 응답에 출력
- `tests/` 없이 로직을 바꾸고 "동작 확인"만 주장하기 (설계 P3에서 테스트 도입 예정)
- 측정용 분기를 코드에 하드코딩 (측정은 환경변수·variant 이름으로 구분)
