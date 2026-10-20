"""keyword 분류기(개선 전 경로) 단위 테스트 — 현재 동작을 고정한 characterization.

`agent/graph.py::_classify_incident_type`는 "키워드 첫 매칭"이라 **규칙 순서가
결과를 좌우한다**. 이 테스트는 그 순서를 문서처럼 고정한다. 규칙을 바꾸면 이
테스트가 깨지고, 그때는 기준선 수치를 다시 측정해야 한다.
"""
from __future__ import annotations

from agent.graph import _classify_incident_type
from common import build_collected, load_monitoring


def _collected(query: str) -> list[dict]:
    return build_collected(query, load_monitoring(profile="base"))


def test_latency_signal_wins():
    assert _classify_incident_type(_collected("auth-service 응답이 느려요")) == "high-latency"


def test_pool_signal_maps_to_high_latency():
    # "pool" 규칙이 latency 뒤에 있지만 둘 다 high-latency로 간다
    assert _classify_incident_type(_collected("auth-service 커넥션 풀이 92%예요")) == "high-latency"


def test_cpu_signal():
    assert _classify_incident_type(_collected("payments-service CPU 93%예요")) == "cpu-spike"


def test_memory_signal():
    assert _classify_incident_type(_collected("cache-service 메모리 증가해요")) == "memory-leak"


def test_timeout_signal():
    assert _classify_incident_type(_collected("gateway-service 504 타임아웃")) == "network-timeout"


def test_disk_signal():
    assert _classify_incident_type(_collected("log-service 디스크 95%예요")) == "disk-full"


def test_down_signal():
    assert _classify_incident_type(_collected("inventory-service DB 다운")) == "db-down"


def test_no_match_falls_back_to_db_down():
    assert _classify_incident_type(_collected("web-01은 정상이에요")) == "db-down"


def test_known_defect_rule_order_puts_cpu_before_timeout():
    """B07 — gateway(타임아웃) + payments(CPU)가 섞이면 cpu가 먼저 잡힌다.

    이게 개선 전 기준선 8/12의 오분류 원인이다. RAG로 고쳤지만, keyword 경로가
    다시 이 모양이면(규칙 순서 복원) 회귀다.
    """
    collected = _collected("gateway-service에서 payments-service로 가는 요청이 타임아웃 나요")
    assert _classify_incident_type(collected) == "cpu-spike"


def test_unknown_system_alerts_do_not_match_any_rule():
    # 데이터에 없는 시스템 → 'not found' 알림 → 어떤 규칙도 안 걸려 db-down 폴백
    collected = build_collected("ghost-service 장애", load_monitoring(profile="base"))
    assert collected[0]["data"]["status"] == "unknown"
    assert _classify_incident_type(collected) == "db-down"
