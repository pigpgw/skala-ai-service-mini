"""입력 데이터 무결성 테스트 — 측정 입력이 깨졌으면 측정을 하지 않는다.

`data/`는 Before/After 비교의 입력이므로, 여기서 깨지면 앞선 측정이 무효가 된다.
그래서 파일 내용 자체를 테스트한다.
"""
from __future__ import annotations

import json
import re

from agent.data_profile import load_monitoring

REPO_ROOT = __import__("pathlib").Path(__file__).resolve().parent.parent.parent
RUNBOOKS_DIR = REPO_ROOT / "data" / "runbooks"
META_PATH = RUNBOOKS_DIR / "meta.json"

SYSTEM_PATTERN = re.compile(r"[a-z][a-z0-9-]+-(?:service|\d+)")
VALID_STATUS = {"healthy", "degraded", "down"}


def test_monitoring_entries_have_required_fields():
    for profile in ("base", "extended"):
        monitoring = load_monitoring(profile)
        for name, entry in monitoring.items():
            assert SYSTEM_PATTERN.fullmatch(name), f"{name}: 시스템 이름 규칙 위반"
            assert entry["status"] in VALID_STATUS, f"{name}: status 값 이상 {entry['status']}"
            assert isinstance(entry["cpu_base"], (int, float))
            assert isinstance(entry["memory_base"], (int, float))
            assert isinstance(entry["alerts"], list)
            if entry["status"] in {"degraded", "down"}:
                assert entry["alerts"], f"{name}: 저하 상태인데 알림이 없다"


def test_meta_covers_every_runbook_file():
    meta = json.loads(META_PATH.read_text(encoding="utf-8"))
    entries = meta["incident_types"]
    files = {path.stem for path in RUNBOOKS_DIR.glob("*.md")}
    assert set(entries) == files, "meta와 런북 파일이 1:1로 대응하지 않는다"
    assert len(files) == 10


def test_meta_entries_have_search_metadata():
    meta = json.loads(META_PATH.read_text(encoding="utf-8"))
    for doc_id, entry in meta["incident_types"].items():
        assert entry.get("title"), f"{doc_id}: title 없음"
        assert entry.get("symptoms"), f"{doc_id}: symptoms 없음"
        assert entry.get("keywords"), f"{doc_id}: keywords 없음"
        assert entry.get("aliases") is not None, f"{doc_id}: aliases 없음"


def test_runbook_body_has_steps():
    for path in RUNBOOKS_DIR.glob("*.md"):
        body = path.read_text(encoding="utf-8")
        steps = [line for line in body.splitlines() if line.strip()[:1].isdigit()]
        assert len(steps) >= 3, f"{path.name}: 대응 단계가 너무 적다"


def test_new_types_have_own_systems_in_extended():
    monitoring = load_monitoring("extended")
    for name in ("search-service", "notify-service", "session-service",
                 "media-service", "inventory-service", "report-service"):
        assert name in monitoring
