"""0단계 — 개선 전(keyword) 분류 기준선 측정.

측정 대상은 현재 코드의 실제 함수 하나다:
    agent/graph.py::_classify_incident_type()

측정 조건(D6): LLM_BACKEND=fake 고정, data/monitoring.json 스냅샷 고정.
입력이 되는 collected는 eval/common.py가 실제 파이프라인과 같게 재구성한다.

실행:
    .venv/bin/python eval/run_baseline.py
    .venv/bin/python eval/run_baseline.py --out eval/baseline_keyword.run2.json
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parent
# agent.* 를 import하려면 저장소 루트가 sys.path에 있어야 한다.
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from agent.graph import _classify_incident_type   # noqa: E402  (측정 대상)
from agent.data_profile import monitoring_path as profile_path   # noqa: E402
from common import (                               # noqa: E402  (eval/ 기준 스크립트)
    INCIDENT_TYPES,
    build_collected,
    load_labels,
    load_monitoring,
    sha256_of,
    validate_labels,
)


def _git(*args: str) -> str | None:
    try:
        out = subprocess.run(["git", *args], cwd=REPO_ROOT, capture_output=True,
                             text=True, check=True)
        return out.stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def main() -> int:
    parser = argparse.ArgumentParser(description="keyword 분류 기준선 측정")
    parser.add_argument("--labels", default=str(HERE / "baseline_labels.json"))
    parser.add_argument("--out", default=str(HERE / "baseline_keyword.json"))
    parser.add_argument("--monitoring", default=None,
                        help="모니터링 파일 직접 지정 (기본: --profile 파일)")
    parser.add_argument("--profile", default="base",
                        help="DATA_PROFILE 기준 파일 선택: base(6) | extended(12)")
    args = parser.parse_args()

    labels_path = Path(args.labels)
    if args.monitoring:
        monitoring_path = Path(args.monitoring)
        profile_name = "custom"
    else:
        monitoring_path = profile_path(args.profile)
        profile_name = args.profile
    monitoring = load_monitoring(monitoring_path)
    labels = load_labels(labels_path)

    problems = validate_labels(labels, monitoring)
    if problems:
        print("라벨 검증 실패 — 측정하지 않습니다.", file=sys.stderr)
        for p in problems:
            print(f"  - {p}", file=sys.stderr)
        return 2

    rows = []
    for item in labels["items"]:
        collected = build_collected(item["query"], monitoring)
        predicted = _classify_incident_type(collected)
        rows.append({
            "id": item["id"],
            "category": item["category"],
            "query": item["query"],
            "systems": item["systems"],
            "expected_type": item["expected_type"],
            "predicted_type": predicted,
            "correct": predicted == item["expected_type"],
        })

    correct = sum(1 for r in rows if r["correct"])
    total = len(rows)
    accuracy = round(correct / total, 4) if total else 0.0

    result = {
        "schema_version": 1,
        "variant": "before-keyword",
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "classifier": "agent.graph._classify_incident_type",
        "llm_backend": "fake",
        "monitoring_file": str(monitoring_path.relative_to(REPO_ROOT))
        if monitoring_path.is_relative_to(REPO_ROOT) else str(monitoring_path),
        "monitoring_sha256": sha256_of(monitoring_path),
        "dataset": labels_path.name,
        "dataset_sha256": sha256_of(labels_path),
        "dataset_frozen_at": labels.get("frozen_at"),
        "data_profile": profile_name,
        "item_count": total,
        "correct": correct,
        "accuracy": accuracy,
        "errors": [r["id"] for r in rows if not r["correct"]],
        "git_commit": _git("rev-parse", "--short", "HEAD"),
        # 추적 중인 파일 변경만 본다 — 결과 JSON 생성 자체로 dirty가 흔들리지 않게.
        "git_dirty": bool(_git("status", "--porcelain", "--untracked-files=no")),
        "items": rows,
    }

    out_path = Path(args.out)
    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n",
                        encoding="utf-8")

    print(f"{'ID':<4} {'category':<10} {'expected':<16} {'predicted':<16} {'ok'}")
    print("-" * 60)
    for r in rows:
        print(f"{r['id']:<4} {r['category']:<10} {r['expected_type']:<16} "
              f"{r['predicted_type']:<16} {'O' if r['correct'] else 'X'}")
    print("-" * 60)
    print(f"accuracy = {correct}/{total} = {accuracy:.4f}")
    if result["errors"]:
        print(f"오분류: {', '.join(result['errors'])}")
    print(f"saved: {out_path}")
    assert all(r["predicted_type"] in INCIDENT_TYPES for r in rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
