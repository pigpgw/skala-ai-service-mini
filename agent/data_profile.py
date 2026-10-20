"""데이터 프로파일 — base(6시스템) / extended(12시스템).

왜 필요한가
    `monitoring.json` 경로가 다섯 곳에 흩어져 있었다: `mcp_server.py:36`,
    `agent/graph.py:30`, `agent/ollama_llm.py:27`, `agent/openai_llm.py:36`,
    `eval/common.py:29`. 시스템을 12개로 늘릴 때 한 곳만 고치면 나머지가 6개
    목록으로 클램프해서 "이름만 늘고 조사 대상은 그대로"인 가짜 확장이 된다.
    여기서 한 번만 결정한다.

규칙
    - `data/monitoring.json`(base)은 **덮어쓰지 않는다**. 기준선·ablation 입력이다.
    - 확장은 `data/monitoring_extended.json` 새 파일로만 한다(`data/AGENTS.md`).
    - `DATA_PROFILE` 값이 잘못되면 조용히 기본값으로 넘어가지 않고 예외를 낸다.
      측정 조건이 바뀐 채로 "같은 조건"이라 기록되는 것이 가장 위험하기 때문이다.

환경변수
    DATA_PROFILE=extended(기본) | base
"""
from __future__ import annotations

import json
import os
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

PROFILES = {
    "base": "monitoring.json",
    "extended": "monitoring_extended.json",
}
DEFAULT_PROFILE = "extended"


def resolve_profile(explicit: str | None = None) -> str:
    """프로파일 이름 결정. 잘못된 값은 예외로 알린다(조용히 기본값으로 가지 않는다).

    `explicit`는 호출자가 직접 지정한 값이라 빈 문자열도 실수로 본다 → 예외.
    환경변수는 비어 있으면 "미설정"으로 보고 기본값을 쓴다.
    """
    if explicit is not None:
        name = explicit.strip().lower()
    else:
        name = (os.environ.get("DATA_PROFILE") or DEFAULT_PROFILE).strip().lower()
    if name not in PROFILES:
        raise ValueError(
            f"DATA_PROFILE 값이 올바르지 않습니다: {name!r} "
            f"(가능한 값: {', '.join(PROFILES)})")
    return name


def monitoring_path(profile: str | None = None) -> Path:
    return DATA_DIR / PROFILES[resolve_profile(profile)]


def load_monitoring(profile: str | None = None) -> dict:
    return json.loads(monitoring_path(profile).read_text(encoding="utf-8"))


def known_systems(profile: str | None = None) -> set[str]:
    """실패 시 하드코딩 폴백을 두지 않는다 — 데이터가 없으면 확장이 아니라 사고다."""
    return set(load_monitoring(profile))


def profile_report(profile: str | None = None) -> dict:
    name = resolve_profile(profile)
    return {
        "profile": name,
        "file": f"data/{PROFILES[name]}",
        "systems": sorted(known_systems(name)),
        "system_count": len(known_systems(name)),
    }
