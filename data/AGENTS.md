# AGENTS.md — data/ (입력 데이터)

상위: 루트 `AGENTS.md`. 이 폴더의 파일은 **측정 기준선**이다. Before/After 비교의 입력이므로 측정 중에 내용을 바꾸면 앞선 측정이 무효가 된다.

## 동결 규칙

- 측정 세션을 시작한 뒤에는 이 폴더의 파일을 수정하지 않는다. 수정이 필요하면 측정을 끝내고, 이전 측정의 조건(파일 해시·수정 시각)을 체크리스트에 기록한 뒤 바꾼다.
- 데이터를 보강할 때(PDF 개선 예시 E8) 기존 파일을 덮어쓰지 않고 **새 파일로 추가**한다. 기존 파일은 기준선으로 남긴다.
- 파일명·키 이름은 코드와 연결돼 있다. 이름을 바꾸면 `agent/graph.py`, `agent/mcp_client.py`, `mcp_server.py`의 참조를 함께 확인한다.

## 내용

| 경로 | 내용 |
|---|---|
| `monitoring.json` | 시스템 6종 상태 (`status`, `cpu_base`, `memory_base`, `alerts`) — `get_monitoring_status` Tool의 응답 원본 |
| `monitoring_extended.json` | 시스템 12종 확장본(2026-10-20 신규). `DATA_PROFILE=extended`(기본)에서 사용. base 6종은 `monitoring.json`과 동일 값 |
| `runbooks/*.md` | 런북 10종 — MCP Resource `runbook://incident-response/{type}`의 본문 |
| `runbooks/meta.json` | 런북 10종의 `title`·`symptoms`·`keywords`·`aliases`·관련 `systems`. RAG 인덱스 텍스트 보강용 **추가** 메타(2026-10-20 신규, 기존 파일 무변경) |

- 시스템(base 6): `auth-service`, `web-01`, `payments-service`, `cache-service`, `gateway-service`, `log-service`
- 시스템(extended 추가 6): `search-service`, `notify-service`, `session-service`, `media-service`, `inventory-service`, `report-service`
- `billing-service`는 **넣지 않는다** — 회귀 질의 #8("목록에 없는 시스템명")의 검증 대상이다.
- 런북: `cpu-spike`, `db-down`, `disk-full`, `high-latency`, `memory-leak`, `network-timeout`, `queue-backlog`, `cert-expiry`, `connection-pool`, `replication-lag`
- 런북 파일명이 `incident_type` 문자열과 매칭된다. 임베딩·검색 개선(E1)을 하면 이 대응 관계가 Meta 정보가 되므로, 매핑 표를 문서에 남긴다.
- 파일 선택은 `agent/data_profile.py` 한 곳에서만 결정한다(`DATA_PROFILE=base|extended`, 기본 `extended`). 코드에 경로를 다시 하드코딩하지 않는다.

## 금지

- 개인정보, 실제 사내 데이터, API 키를 넣기
- 측정 중 기준선 파일 교체
- 생성물(임베딩·인덱스 결과 등)을 커밋. 만들면 `.gitignore`에 먼저 추가한다 (현재 `.gitignore`에는 `data/` 항목이 없다)
