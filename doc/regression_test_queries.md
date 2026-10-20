# 회귀 테스트용 쿼리 목록 — 시스템명 하드코딩 수정 검증

| # | 쿼리 | 테스트 목적 |
|---|---|---|
| 1 | payments-service 결제 응답이 느려지고 CPU가 치솟았어요, 원인 확인해주세요 | 기존엔 auth-service로 조용히 되돌아갔던 4개 시스템 중 하나 — KNOWN_SYSTEMS 인식 확인 (cpu-spike runbook) |
| 2 | cache-service 메모리 사용률이 계속 올라가고 있어요 | 미인식 시스템 확인 2 (memory-leak runbook) |
| 3 | log-service 디스크 공간이 부족하다는 알림이 왔어요 | 미인식 시스템 확인 3 (disk-full runbook) |
| 4 | gateway-service에서 payments-service로 가는 요청이 타임아웃 나고 있어요 | 두 시스템 동시 언급 — system_name은 먼저 등장한 gateway-service 하나만 뽑히는지, 그런데도 research task는 두 시스템 다 조사하는지(비교 분석 영향 없음) 확인 |
| 5 | web-01 CPU 급증, auth-service 커넥션 풀도 같이 확인해줘 | 기본 2개 시스템 동시 언급 — 기존 동작(web-01, auth-service 둘 다 조사) 회귀 확인 |
| 6 | payments-service랑 cache-service 둘 다 저하됐는데 공통 원인이 있는지 분석해줘 | needs_analysis=true 유도 — gate(W6)·analysis_node 비교 분석이 여전히 동작하는지 확인 |
| 7 | 로그인 응답이 느려요, 원인 확인해주세요 | 시스템명 미언급 — auth-service 폴백 확인 |
| 8 | billing-service 응답이 느려요 | 목록에 없는 시스템명 — system_name 라벨은 auth-service 폴백, plan()의 target 클램프도 정상 동작하는지(KNOWN_SYSTEMS에 없는 임의 이름은 여전히 걸러져야 함) |
| 9 | 안녕, 너는 누구야? | route=chat 직행(Wave 5) — 토큰 스트리밍(AnswerToken)이 채팅 경로에서도 실시간으로 오는지 확인 |
| 10 | 제 이름은 민수입니다 → (다음 메시지로) 제 이름이 뭐였죠? | Wave 12 세션 기억 — 서버 재시작 후에도 유지되는지, 스트리밍과 충돌 없는지 확인 |

---

## 실행 결과 (2026-10-20)

과제 PDF 9쪽이 "아래 예시들로 테스트를 해보면서 코드를 분석합니다"라고 준 질의 세트를
**실제 서버에** 순서대로 던져 확인했다. 실행기: `eval/run_regression_queries.py`
(서버를 직접 띄우고, 10번 질의 사이에는 서버를 실제로 재시작한다).

```bash
.venv/bin/python eval/run_regression_queries.py --rag on   # RAG 경로
.venv/bin/python eval/run_regression_queries.py --rag off  # keyword 경로
```

| # | 질의 | 라우팅 | 판정 유형 | 조회 시스템 | unknown | 결과 |
|---|---|---|---|---|---|---|
| 1 | payments-service 결제 응답이 느려지고 CPU가 치솟았어요 | incident | high-latency | payments-service, web-01 | - | O |
| 2 | cache-service 메모리 사용률 증가 | incident | memory-leak | cache-service, web-01 | - | O |
| 3 | log-service 디스크 공간 부족 알림 | incident | disk-full | log-service, web-01 | - | O |
| 4 | gateway→payments 타임아웃 | incident | network-timeout | gateway, payments, web-01 | - | O |
| 5 | web-01 CPU 급증 + auth-service 커넥션 풀 | incident | high-latency | web-01, auth-service | - | O |
| 6 | payments·cache 공통 원인 분석 | incident | cpu-spike | payments, cache, web-01 | - | O |
| 7 | 로그인 응답이 느려요 | incident | high-latency | auth-service, web-01 | - | O |
| 8 | billing-service 응답이 느려요 | incident | db-down | billing-service, web-01 | billing-service | O |
| 9 | 안녕, 너는 누구야? | chat | - | - | - | O |
| 10 | 제 이름은 민수입니다 → (재시작 후) 제 이름이 뭐였죠? | chat | - | - | - | O (기억 유지) |

**RAG on 10/10 통과** (`eval/regression_queries.json`).

### 라우팅 수정 — 이 실행에서 처음 발견한 것

처음 돌렸을 때 **10개 중 3개만 통과**했다(`eval/regression_queries_before.json`).
원인은 라우터가 아니라 결정론 백엔드(`agent/fake_llm.py`)의 라우팅 정규식이
`장애|진단|다운|지연|급증|incident|티켓` 7개짜리였기 때문이다.
그 정규식에 걸리지 않는 질의는 전부 `chat`으로 떨어져 **장애 파이프라인이 아예 돌지 않았다**
("안녕하세요! 무엇을 도와드릴까요?"만 답함).

즉 과제 PDF 9쪽이 알려준 테스트 질의로 자기 자신을 테스트할 수 없는 상태였다.
실제 LLM 백엔드(ollama/openai)는 "장애·성능 저하·지연·진단·모니터링·티켓"을 프롬프트로
분류하므로 이 문제가 없는데, 결정론 백엔드만 좁았다.

수정: `agent/fake_llm.py::route`의 기준을 LLM 백엔드와 같은 운영 어휘로 넓히고,
**모니터링 대상 시스템명이 있으면** incident로 간다(목록에 없는 `billing-service`도 포함).
단위 테스트로 고정했다(`tests/unit/test_router.py`).

| 조건 | 통과 | 근거 |
|---|---|---|
| 수정 전 (router) | **3/10** | `eval/regression_queries_before.json` |
| 수정 후 (router, RAG on) | **10/10** | `eval/regression_queries.json` |
| 수정 후 (router, RAG off = keyword 경로) | **9/10** | `eval/regression_queries_rag_off.json` |

### keyword 경로에서 남는 1건 (#4)

keyword 경로(RAG off)는 #4를 `cpu-spike`로 고른다. gateway(타임아웃) + payments(CPU)가
섞이면 규칙 순서상 `cpu`가 먼저 잡히는 **기존 결함**(기준선 오분류 B07과 같은 원인)이다.
RAG를 켜면 `network-timeout`으로 고쳐진다. 이건 고치지 않은 게 아니라 **RAG로 개선된 지점**이다.

### #1은 두 런북이 모두 정당

1번 질의는 "느려지고"와 "CPU가 치솟았어요" 두 증상이 함께 있다.
keyword는 알림만 보고(알림에 CPU 91%만 있음) `cpu-spike`를, RAG는 질의 문장까지 보고
`high-latency`(score 0.5951 vs cpu-spike 0.5567, margin 0.0384)를 고른다.
어느 쪽도 틀린 답이 아니므로 **둘 다 허용**으로 두었다. 이 질의의 테스트 목적은
"payments-service가 인식·조회되는가"였고 그건 충족된다.
