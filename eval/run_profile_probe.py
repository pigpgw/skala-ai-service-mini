"""프로파일이 subprocess(MCP)까지 실제로 도달하는지 확인한다.

왜 별도 확인이 필요한가
    `DATA_PROFILE`은 `mcp_server.py`가 **stdio subprocess**로 뜰 때 상속된다.
    코드만 보고 "전달된다"고 쓰면 안 되고, 실제 Tool 응답으로 확인해야 한다.
    또한 회귀 #8(`billing-service` = 목록에 없는 시스템)이 확장 후에도 유지되는지
    같은 호출로 확인한다.

실행:
    .venv/bin/python eval/run_profile_probe.py
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from agent.data_profile import known_systems, profile_report      # noqa: E402
from agent.mcp_client import MCPClient                            # noqa: E402

TARGETS = ["search-service", "inventory-service", "auth-service", "billing-service"]


async def probe(profile: str) -> dict:
    os.environ["DATA_PROFILE"] = profile
    client = MCPClient(flaky_first_tool_call=False)   # 측정용 — 데모용 지연 주입 제외
    await client.start()
    try:
        rows = []
        for name in TARGETS:
            data = await client.call_tool("get_monitoring_status", {"system_name": name})
            rows.append({
                "system": name,
                "status": data["status"],
                "alerts": data["alerts"],
                "known": data["status"] != "unknown",
            })
    finally:
        await client.stop()
    report = profile_report(profile)
    return {
        "profile": profile,
        "known_systems_count": len(known_systems(profile)),
        "file": report["file"],
        "targets": rows,
    }


async def main() -> int:
    results = [await probe("base"), await probe("extended")]
    checks = {
        "base_excludes_extended_system": {
            "pass": all(not row["known"] for row in results[0]["targets"]
                        if row["system"] in {"search-service", "inventory-service"}),
        },
        "extended_includes_new_systems": {
            "pass": all(row["known"] for row in results[1]["targets"]
                        if row["system"] in {"search-service", "inventory-service"}),
        },
        "regression_8_unknown_system": {
            "pass": all(not row["known"] for result in results
                        for row in result["targets"] if row["system"] == "billing-service"),
        },
    }
    payload = {
        "schema_version": 1,
        "stage": "3단계 데이터 프로파일 검증",
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "checks": checks,
        "results": results,
    }
    out = HERE / "profile_probe.json"
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    for result in results:
        print(f"[{result['profile']}] file={result['file']} systems={result['known_systems_count']}")
        for row in result["targets"]:
            print(f"   {row['system']:<20} status={row['status']:<8} known={row['known']}")
    print()
    for name, check in checks.items():
        print(f"[{'PASS' if check['pass'] else 'FAIL'}] {name}")
    print(f"saved: {out}")
    return 0 if all(c["pass"] for c in checks.values()) else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
