"""데이터 프로파일 단위 테스트 — base/extended 선택과 파일 규칙."""
from __future__ import annotations

import json

import pytest

from agent.data_profile import (
    DEFAULT_PROFILE,
    PROFILES,
    known_systems,
    load_monitoring,
    monitoring_path,
    profile_report,
    resolve_profile,
)

BASE_SYSTEMS = {"auth-service", "web-01", "payments-service",
                 "cache-service", "gateway-service", "log-service"}


def test_resolve_profile_accepts_known_values():
    assert resolve_profile("base") == "base"
    assert resolve_profile("extended") == "extended"
    assert resolve_profile(" EXTENDED ") == "extended"
    assert DEFAULT_PROFILE == "extended"


def test_resolve_profile_rejects_unknown_value():
    # 잘못된 값이 조용히 기본값으로 넘어가면 "측정 조건이 바뀐 채 같은 조건"이 된다
    with pytest.raises(ValueError):
        resolve_profile("everything")
    with pytest.raises(ValueError):
        resolve_profile("")


def test_monitoring_path_maps_profile_to_file():
    assert monitoring_path("base").name == "monitoring.json"
    assert monitoring_path("extended").name == "monitoring_extended.json"
    assert set(PROFILES) == {"base", "extended"}


def test_base_has_six_systems_and_extended_has_twelve():
    assert len(load_monitoring("base")) == 6
    assert len(load_monitoring("extended")) == 12
    assert known_systems("base") == BASE_SYSTEMS
    assert BASE_SYSTEMS < known_systems("extended")


def test_extended_keeps_base_values_identical():
    base = load_monitoring("base")
    extended = load_monitoring("extended")
    for name, value in base.items():
        assert extended[name] == value, f"{name} 값이 base와 달라졌다"


def test_billing_service_stays_unknown_for_regression_query():
    # 회귀 질의 #8 — 목록에 없는 시스템명을 물으면 unknown으로 답해야 한다
    assert "billing-service" not in known_systems("extended")
    assert "billing-service" not in known_systems("base")


def test_profile_report_shape():
    report = profile_report("extended")
    assert report["profile"] == "extended"
    assert report["file"] == "data/monitoring_extended.json"
    assert report["system_count"] == 12
    assert report["systems"] == sorted(known_systems("extended"))
