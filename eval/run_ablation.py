"""3단계 ablation — RAG 효과와 데이터 확장 효과를 분리한다.

측정 파일을 다시 계산하지 않고 **이미 저장된 원본**을 집계한다. 단, 데이터 커버리지
(모니터링 데이터가 없어 unknown이 된 시스템 비율)는 라벨+프로파일로 매번 재계산한다.

    A = keyword + base        eval/baseline_extended_keyword_base.json
    B = RAG + base            eval/rag_probe_extended_on_base.json
    C = RAG + extended        eval/rag_probe_extended.json
    (참고) keyword + extended  eval/baseline_extended_keyword.json

실행:
    .venv/bin/python eval/run_ablation.py
"""
from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parent
for path in (str(REPO_ROOT), str(HERE)):
    if path not in sys.path:
        sys.path.insert(0, path)

from common import build_collected, load_labels, load_monitoring   # noqa: E402

ARMS = [
    ("A", "keyword + base", "eval/baseline_extended_keyword_base.json"),
    ("B", "RAG + base", "eval/rag_probe_extended_on_base.json"),
    ("C", "RAG + extended", "eval/rag_probe_extended.json"),
    ("-", "keyword + extended (참고)", "eval/baseline_extended_keyword.json"),
]


def _by_category(items: list[dict]) -> dict:
    out: dict[str, dict] = {}
    for row in items:
        bucket = out.setdefault(row["category"], {"correct": 0, "total": 0})
        bucket["total"] += 1
        bucket["correct"] += int(bool(row["correct"]))
    return out


def _coverage(labels: dict, profile: str) -> dict:
    monitoring = load_monitoring(profile=profile)
    queried = unknown = 0
    unknown_systems: set[str] = set()
    for item in labels["items"]:
        for entry in build_collected(item["query"], monitoring):
            data = entry["data"]
            queried += 1
            if data["status"] == "unknown":
                unknown += 1
                unknown_systems.add(data["system_name"])
    return {
        "profile": profile,
        "systems_in_profile": len(monitoring),
        "queries": len(labels["items"]),
        "system_lookups": queried,
        "unknown_lookups": unknown,
        "unknown_rate": round(unknown / queried, 4) if queried else 0.0,
        "unknown_systems": sorted(unknown_systems),
    }


def main() -> int:
    labels = load_labels(HERE / "labels_extended.json")
    arms = []
    for key, name, path in ARMS:
        payload = json.loads((REPO_ROOT / path).read_text(encoding="utf-8"))
        arms.append({
            "arm": key,
            "variant": name,
            "file": path,
            "correct": payload["correct"],
            "total": payload["item_count"],
            "accuracy": payload["accuracy"],
            "per_category": _by_category(payload["items"]),
            "fallbacks": sum(1 for r in payload["items"] if r.get("source") == "keyword"),
        })

    coverage = {"base": _coverage(labels, "base"), "extended": _coverage(labels, "extended")}
    result = {
        "schema_version": 1,
        "stage": "3단계 ablation (RAG 효과 vs 데이터 확장 효과)",
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "dataset": "eval/labels_extended.json (40문항, 동결)",
        "arms": arms,
        "coverage": coverage,
        "notes": [
            "B-C 차이는 데이터 확장만의 효과다. 이 측정에서는 정확도 차이가 0이다.",
            "데이터 확장의 효과는 정확도가 아니라 coverage(unknown 비율)로 나타난다.",
            "A-B 차이는 RAG 도입 효과다.",
        ],
    }
    out = HERE / "ablation.json"
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"{'군':<3} {'조건':<26} {'정확도':>10}  카테고리별")
    print("-" * 96)
    for arm in arms:
        cats = " ".join(f"{k} {v['correct']}/{v['total']}"
                        for k, v in arm["per_category"].items())
        print(f"{arm['arm']:<3} {arm['variant']:<26} "
              f"{arm['correct']}/{arm['total']} {arm['accuracy']:.4f}  {cats}")
    print("-" * 96)
    for name, cov in coverage.items():
        print(f"coverage[{name}] systems={cov['systems_in_profile']} "
              f"lookups={cov['system_lookups']} unknown={cov['unknown_lookups']} "
              f"({cov['unknown_rate']:.2%}) {cov['unknown_systems']}")
    print(f"saved: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
