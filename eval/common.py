"""평가 공통 유틸 — 질의를 '실제 그래프가 만드는 collected'와 같게 재구성한다.

왜 필요한가
    `agent/graph.py::_classify_incident_type()`은 **질의문이 아니라 collected**를 읽는다.
    collected는 research 노드가 MCP Tool(`get_monitoring_status`)로 받은 모니터링 결과다.
    그래서 분류 정확도를 재려면 질의 → 조사 대상 시스템 → 모니터링 결과 순서로
    collected를 다시 만들어야 한다.

무엇을 그대로 재현했나 (D6: LLM_BACKEND=fake 고정)
    - 조사 대상 추출: `agent/fake_llm.py:40-47`의 정규식 + auth-service 폴백 + web-01 자동 추가
    - 응답 형태: `mcp_server.py:24-53`의 SystemStatus 필드
    - 응답 내용: `data/monitoring.json`의 status/alerts/cpu_base/memory_base

일부러 재현하지 않은 것
    - cpu_percent/memory_percent의 random jitter (분류기는 status·alerts만 읽으므로 무관)
    - last_checked 시각 (분류에 쓰이지 않음)
    → 이 두 가지를 재현하지 않는다는 사실이 측정 조건이다. 분류 로직이 이 필드를 읽기
      시작하면 이 파일도 함께 고쳐야 한다.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "data"
MONITORING_PATH = DATA_DIR / "monitoring.json"   # base 스냅샷(기준선)

if str(REPO_ROOT) not in sys.path:      # `agent.data_profile` — 프로파일 단일 결정 지점
    sys.path.insert(0, str(REPO_ROOT))

from agent.data_profile import known_systems, monitoring_path as profile_path   # noqa: E402

# `agent/fake_llm.py:40`과 같은 패턴. 다르게 바꾸면 라벨의 systems 검증이 깨져 알려준다.
SYSTEM_PATTERN = re.compile(r"[a-z][a-z0-9-]+-(?:service|\d+)")

INCIDENT_TYPES = (
    "high-latency", "cpu-spike", "memory-leak", "network-timeout", "disk-full",
    "db-down", "queue-backlog", "cert-expiry", "connection-pool", "replication-lag",
)
CATEGORIES = ("single", "multi", "ambiguous", "no_system")


def load_monitoring(path: Path | str | None = None,
                    profile: str | None = None) -> dict:
    """monitoring 데이터. path를 주면 그 파일, 아니면 DATA_PROFILE 기준 파일."""
    target = Path(path) if path is not None else profile_path(profile)
    return json.loads(target.read_text(encoding="utf-8"))


def systems_of(monitoring: dict) -> set[str]:
    return set(monitoring)


def sha256_of(path: Path | str) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def extract_targets(query: str, include_web01: bool = True) -> list[str]:
    """fake 백엔드의 plan()과 같은 규칙으로 조사 대상 시스템 목록을 만든다."""
    systems = SYSTEM_PATTERN.findall(query) or ["auth-service"]
    if include_web01 and "web-01" not in systems:
        systems.append("web-01")
    return list(dict.fromkeys(systems))


def build_collected(query: str, monitoring: dict) -> list[dict]:
    """질의 → collected. research 노드가 만드는 형태와 동일하게 맞춘다."""
    collected = []
    for name in extract_targets(query):
        base = monitoring.get(name)
        if base is None:
            data = {
                "system_name": name,
                "status": "unknown",
                "cpu_percent": 0.0,
                "memory_percent": 0.0,
                "last_checked": None,
                "alerts": [f"System '{name}' not found in monitoring"],
            }
        else:
            data = {
                "system_name": name,
                "status": base["status"],
                "cpu_percent": round(float(base["cpu_base"]), 1),
                "memory_percent": round(float(base["memory_base"]), 1),
                "last_checked": None,
                "alerts": list(base.get("alerts", [])),
            }
        collected.append({"source": "monitoring", "data": data})
    return collected


def load_labels(path: Path | str) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def validate_labels(labels: dict, monitoring: dict) -> list[str]:
    """실행 전에 라벨 형식을 검증한다. 실패하면 측정하지 않는다."""
    problems = []
    seen = set()
    for item in labels.get("items", []):
        rid = item.get("id")
        if not rid:
            problems.append("id 없는 항목")
            continue
        if rid in seen:
            problems.append(f"{rid}: id 중복")
        seen.add(rid)
        if item.get("category") not in CATEGORIES:
            problems.append(f"{rid}: category 값 오류 {item.get('category')!r}")
        if item.get("expected_type") not in INCIDENT_TYPES:
            problems.append(f"{rid}: expected_type 값 오류 {item.get('expected_type')!r}")
        elif not (DATA_DIR / "runbooks" / f"{item['expected_type']}.md").is_file():
            problems.append(f"{rid}: runbook 파일 없음 {item['expected_type']}.md")
        derived = extract_targets(item.get("query", ""))
        if item.get("systems") != derived:
            problems.append(
                f"{rid}: systems 불일치 — 라벨 {item.get('systems')} vs 재구성 {derived}")
        if not item.get("rationale"):
            problems.append(f"{rid}: rationale 비어 있음")
    if len(labels.get("items", [])) != labels.get("item_count"):
        problems.append(
            f"item_count 불일치 — 선언 {labels.get('item_count')} vs 실제 {len(labels.get('items', []))}")
    for name in monitoring:
        if not SYSTEM_PATTERN.fullmatch(name):
            problems.append(f"monitoring 키가 시스템 패턴과 불일치: {name}")
    return problems
