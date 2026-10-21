"""1단계 임시 측정 — RAG 분류기의 12문항 정확도와 3가지 동작 확인.

0단계 기준선(`eval/baseline_keyword.json`, 8/12 = 0.6667)과 **같은 12문항·같은
collected 재구성**(`eval/common.py`)을 쓴다. 4단계에서 `eval/run_eval.py`로 통합한다.

확인 항목 (doc/rag_design.md §9)
    1. 인덱스 캐시 재사용 — 두 번째 load_or_build()가 cache_hit=True
    2. 12문항 정확도 — 0.6667 초과
    3. 강제 저신뢰(RAG_MIN_SCORE=0.99) → keyword 결과와 동일, reason=low_score
    4. RAG_ENABLED=false → 기준선 파일과 문항별 예측 동일

실행:
    .venv/bin/python eval/run_rag_probe.py
    .venv/bin/python eval/run_rag_probe.py --embedder hashing
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
for path in (str(REPO_ROOT), str(HERE)):
    if path not in sys.path:
        sys.path.insert(0, path)

from agent.rag import RagClassifier, build_embedder, load_or_build      # noqa: E402
from agent.data_profile import monitoring_path as profile_path          # noqa: E402
from common import (                                                   # noqa: E402
    build_collected,
    load_labels,
    load_monitoring,
    sha256_of,
)

FORCED_MIN_SCORE = 0.99


def _git(*args: str) -> str | None:
    try:
        out = subprocess.run(["git", *args], cwd=REPO_ROOT, capture_output=True,
                             text=True, check=True)
        return out.stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def _run_items(classifier: RagClassifier, labels: dict, monitoring: dict) -> list[dict]:
    rows = []
    for item in labels["items"]:
        collected = build_collected(item["query"], monitoring)
        result = classifier.classify(item["query"], collected)
        rows.append({
            "id": item["id"],
            "category": item["category"],
            "query": item["query"],
            "expected_type": item["expected_type"],
            "predicted_type": result.incident_type,
            "correct": result.incident_type == item["expected_type"],
            "source": result.source,
            "reason": result.reason,
            "score": result.score,
            "margin": result.margin,
            "doc_id": result.doc_id,
            "candidates": [{"id": i, "score": s} for i, s in result.candidates],
            "elapsed_ms": result.elapsed_ms,
        })
    return rows


def _accuracy(rows: list[dict]) -> tuple[int, float]:
    correct = sum(1 for r in rows if r["correct"])
    total = len(rows)
    return correct, round(correct / total, 4) if total else 0.0


def main() -> int:
    parser = argparse.ArgumentParser(description="RAG 분류 1단계 측정")
    parser.add_argument("--labels", default=str(HERE / "baseline_labels.json"))
    parser.add_argument("--baseline", default=str(HERE / "baseline_keyword.json"))
    parser.add_argument("--out", default=str(HERE.parent / "artifacts" / "eval" / "rag_probe.json"))
    parser.add_argument("--embedder", default=None,
                        help="auto|ollama|hashing (기본: RAG_EMBEDDER 또는 auto)")
    parser.add_argument("--profile", default="base",
                        help="DATA_PROFILE 기준 모니터링 파일: base(6) | extended(12)")
    args = parser.parse_args()

    labels = load_labels(args.labels)
    monitoring = load_monitoring(profile=args.profile)
    baseline = json.loads(Path(args.baseline).read_text(encoding="utf-8"))
    baseline_predictions = {row["id"]: row["predicted_type"] for row in baseline["items"]}

    embedder = build_embedder(args.embedder)

    # 1) 첫 적재 — 빌드 또는 기존 캐시
    index_first = load_or_build(embedder)
    # 2) 두 번째 적재 — 캐시 재사용 확인
    index_second = load_or_build(embedder)

    main_classifier = RagClassifier.from_env(index_first, embedder)
    rows = _run_items(main_classifier, labels, monitoring)
    correct, accuracy = _accuracy(rows)

    # 3) 강제 저신뢰 → keyword 폴백
    forced = RagClassifier(index_first, embedder, min_score=FORCED_MIN_SCORE,
                           min_margin=main_classifier.min_margin)
    forced_rows = _run_items(forced, labels, monitoring)

    # 4) 비활성 → 기준선과 동일해야 한다
    disabled = RagClassifier(index_first, embedder, enabled=False)
    disabled_rows = _run_items(disabled, labels, monitoring)

    def same_predictions(candidate_rows: list[dict]) -> bool:
        return all(r["predicted_type"] == baseline_predictions[r["id"]] for r in candidate_rows)

    checks = {
        "cache_reuse": {
            "first_cache_hit": index_first.cache_hit,
            "second_cache_hit": index_second.cache_hit,
            "pass": bool(index_second.cache_hit),
        },
        "accuracy": {
            "correct": correct,
            "total": len(rows),
            "accuracy": accuracy,
            "baseline_accuracy": baseline["accuracy"],
            "pass": accuracy > baseline["accuracy"],
        },
        "forced_low_score": {
            "min_score": FORCED_MIN_SCORE,
            "reasons": sorted({r["reason"] for r in forced_rows}),
            "all_keyword_source": all(r["source"] == "keyword" for r in forced_rows),
            "same_as_keyword": same_predictions(forced_rows),
            "pass": (all(r["source"] == "keyword" for r in forced_rows)
                     and all(r["reason"] == "low_score" for r in forced_rows)
                     and same_predictions(forced_rows)),
        },
        "disabled": {
            "same_as_baseline": same_predictions(disabled_rows),
            "pass": same_predictions(disabled_rows),
        },
    }

    result = {
        "schema_version": 1,
        "variant": "after-rag",
        "stage": "1단계 임시 측정 (4단계에서 eval/run_eval.py로 통합)",
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "embedder": {
            "name": getattr(embedder, "name", "unknown"),
            "dim": getattr(embedder, "dim", None),
            "requested": args.embedder or "auto",
        },
        "index": {
            "docs": [doc.id for doc in index_first.docs],
            "doc_count": len(index_first.docs),
            "built_at": index_first.built_at,
            "index_sha256": index_first.index_sha256,
            "cache_hit_first": index_first.cache_hit,
            "cache_hit_second": index_second.cache_hit,
        },
        "thresholds": {
            "RAG_ENABLED": main_classifier.enabled,
            "RAG_MIN_SCORE": main_classifier.min_score,
            "RAG_MIN_MARGIN": main_classifier.min_margin,
            "top_k": main_classifier.top_k,
        },
        "monitoring_sha256": sha256_of(profile_path(args.profile)),
        "data_profile": args.profile,
        "dataset_sha256": sha256_of(Path(args.labels)),
        "baseline_file": Path(args.baseline).name,
        "git_commit": _git("rev-parse", "--short", "HEAD"),
        "git_dirty": bool(_git("status", "--porcelain", "--untracked-files=no")),
        "item_count": len(rows),
        "correct": correct,
        "accuracy": accuracy,
        "errors": [r["id"] for r in rows if not r["correct"]],
        "checks": checks,
        "items": rows,
        "fallback_prediction_diff": [
            {"id": r["id"], "baseline": baseline_predictions[r["id"]],
             "forced": f["predicted_type"], "disabled": d["predicted_type"]}
            for r, f, d in zip(rows, forced_rows, disabled_rows)
            if not (r["id"] and f["predicted_type"] == d["predicted_type"] == baseline_predictions[r["id"]])
        ],
    }

    out_path = Path(args.out)
    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n",
                        encoding="utf-8")

    print(f"embedder = {result['embedder']['name']} (dim={result['embedder']['dim']})")
    print(f"docs     = {', '.join(result['index']['docs'])}")
    print()
    print(f"{'ID':<4} {'expected':<16} {'predicted':<16} {'src':<8} {'reason':<18} "
          f"{'score':>7} {'margin':>7}  ok")
    print("-" * 88)
    for r in rows:
        score = "-" if r["score"] is None else f"{r['score']:.4f}"
        margin = "-" if r["margin"] is None else f"{r['margin']:.4f}"
        print(f"{r['id']:<4} {r['expected_type']:<16} {r['predicted_type']:<16} "
              f"{r['source']:<8} {r['reason']:<18} {score:>7} {margin:>7}  "
              f"{'O' if r['correct'] else 'X'}")
    print("-" * 88)
    print(f"accuracy = {correct}/{len(rows)} = {accuracy:.4f} "
          f"(baseline {baseline['accuracy']:.4f})")
    if result["errors"]:
        print(f"오분류: {', '.join(result['errors'])}")
    print()
    for name, check in checks.items():
        print(f"[{'PASS' if check['pass'] else 'FAIL'}] {name}")
    print(f"saved: {out_path}")
    return 0 if all(c["pass"] for c in checks.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
