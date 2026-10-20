# data/ — 입력 데이터

에이전트가 조사에 사용하는 모의 운영 데이터다. 측정 기준선이므로 측정 중에는 수정하지 않는다(규칙: `AGENTS.md`).

## monitoring.json

시스템 6종의 상태·CPU·메모리 기준값과 알림 문구. `MCP Tool get_monitoring_status`가 이 값을 읽어 응답한다.

| 시스템 | 상태 | 알림 요약 |
|---|---|---|
| `auth-service` | degraded | p95 latency 2.4s, connection pool 92% |
| `web-01` | healthy | 없음 |
| `payments-service` | degraded | CPU 91%, 인스턴스 응답 지연 |
| `cache-service` | degraded | 메모리 6시간 지속 상승 |
| `gateway-service` | degraded | upstream timeout(504), packet loss 3% |
| `log-service` | degraded | `/var/log` 95% |

## runbooks/

`MCP Resource runbook://incident-response/{type}`로 제공되는 대응 절차다.

| 파일 | incident_type | 상황 |
|---|---|---|
| `cpu-spike.md` | `cpu-spike` | CPU 급증 |
| `memory-leak.md` | `memory-leak` | 메모리 누수 |
| `disk-full.md` | `disk-full` | 디스크 부족 |
| `high-latency.md` | `high-latency` | 응답 지연 |
| `network-timeout.md` | `network-timeout` | 네트워크 타임아웃 |
| `db-down.md` | `db-down` | DB 장애 |

## 참고

- 입력 질의 세트는 `../doc/regression_test_queries.md`에 있다. 이 폴더에는 없다.
- 회귀 확인: `payments-service 결제 응답이 느려지고 CPU가 치솟았어요`, `cache-service 메모리 사용률이 계속 올라가고 있어요`, `log-service 디스크 공간이 부족하다는 알림이 왔어요`
