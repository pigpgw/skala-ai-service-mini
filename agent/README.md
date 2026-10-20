# agent/ — 런타임 코드 지도

에이전트 실행에 쓰이는 코드만 있는 폴더다. 실행 방법은 `../sh/README.md`, 전체 구조는 `../doc/README.md`를 본다.

## 그래프 흐름 (`graph.py`, `SUPERVISOR_VERSION=v2`)

```text
route ─┬─ chat ─────────────────────────────────────────→ chat_answer → END
       └─ incident → plan → gate → research → replan_check ─┐
                                              ↑  부족        │ 충분
                                              └──────────────┤
                                                             ▼
                                          analysis ─→ write ─→ validate ─┬─ 불합격 → write
                                          (task 없으면 스킵)             └─ 합격 → finalize → END
```

| 노드 | 하는 일 |
|---|---|
| `route` | 입력을 `chat` / `incident`로 분기 |
| `chat_answer` | 잡담·자기소개 응답 (토큰 스트리밍) |
| `plan` | 조사 task 계획 수립, 대상 시스템 클램프 |
| `gate` | 불필요·중복 task 제거 (`gate_removed`) |
| `research` | MCP Tool·Resource로 로그·메트릭·런북 수집 (병렬) |
| `replan_check` | 수집이 충분한지 판정, 부족하면 `research` 재진입 (`replan_rounds`) |
| `analysis` | 여러 시스템 비교 분석 (task 없으면 내부 스킵) |
| `write` | 수집 결과로 답변 초안 작성 |
| `validate` | 초안 검증, 불합격이면 `write`로 되돌림 (`validation_attempts`) |
| `finalize` | 최종 응답 확정 |

`SUPERVISOR_VERSION=v1`이면 그래프 대신 `supervisor_v1.py`의 선형 파이프라인이 돈다.

## 파일

| 파일 | 한 줄 설명 |
|---|---|
| `deps.py` | `SupervisorDeps`(fast_llm·quality_llm·mcp·session_store·version) — 노드 주입용 |
| `fake_llm.py` | 결정론 스텁 LLM. 기준선·테스트에서 같은 입력에 같은 출력 |
| `ollama_llm.py` | Ollama 실모델 백엔드 |
| `openai_llm.py` | OpenAI API 백엔드 (과금) |
| `mcp_client.py` | stdio MCP 클라이언트. `start()`/`stop()` 수명, `call_tool`, `read_resource`, `get_prompt` |
| `session_store.py` | SQLite 대화 이력. `load(thread_id)` / `append(...)` |
| `retry.py` | `with_retry(fn, ...) -> (결과, 재시도 횟수)` |
| `supervisor_v1.py` | legacy 선형 파이프라인 |

## 상태 (`AgentState`)

계획·수집·검증 결과가 모두 상태로 흐른다: `query` · `thread_id` · `history` · `route` · `needs_analysis` · `tasks` · `gate_removed` · `collected` · `replan_rounds` · `retry_count` · `draft` · `validation_attempts` · `validation_feedback` · `final` · `last_prompt` · `events`

`events`는 SSE(`GET /chat/stream`)로 나가는 진행 이벤트다. 화면에서 보이는 단계 표시가 이 값이다.
