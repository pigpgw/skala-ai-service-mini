"""임계값 민감도 스윕 — 저장된 probe 결과의 top-3 후보만 다시 조합한다.

측정을 다시 돌리지 않는 이유: 임계값은 **이미 계산된 유사도**에 대한 필터이므로,
top-1/top-2 점수와 keyword 폴백 결과만 있으면 같은 결론을 재현할 수 있다.
(임베딩을 다시 호출하면 모델·캐시 상태가 달라져 "같은 측정"이 아니게 된다.)

실행:
    .venv/bin/python eval/run_threshold_sweep.py \
        --probe eval/rag_probe_extended.json \
        --baseline eval/baseline_extended_keyword.json \
        --out eval/rag_threshold_sweep_extended.json
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

MARGINS = [0.0, 0.01, 0.02, 0.03, 0.04, 0.05, 0.08]
SCORES = [0.40, 0.45, 0.50, 0.55, 0.60, 0.65]


def main() -> int:
    parser = argparse.ArgumentParser(description="임계값 민감도 스윕")
    parser.add_argument("--probe", required=True)
    parser.add_argument("--baseline", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    probe = json.loads(Path(args.probe).read_text(encoding="utf-8"))
    keyword = {r["id"]: r["predicted_type"]
               for r in json.loads(Path(args.baseline).read_text(encoding="utf-8"))["items"]}
    items = probe["items"]

    def evaluate(min_score: float, min_margin: float) -> dict:
        correct = 0
        rag = 0
        per_category: dict[str, list[int]] = {}
        for row in items:
            candidates = row["candidates"]
            top1_id, top1 = candidates[0]["id"], candidates[0]["score"]
            top2 = candidates[1]["score"] if len(candidates) > 1 else -1.0
            if top1 < min_score or (top1 - top2) < min_margin:
                predicted = keyword[row["id"]]
            else:
                predicted, rag = top1_id, rag + 1
            ok = int(predicted == row["expected_type"])
            correct += ok
            bucket = per_category.setdefault(row["category"], [0, 0])
            bucket[0] += ok
            bucket[1] += 1
        total = len(items)
        return {
            "min_score": min_score,
            "min_margin": min_margin,
            "correct": correct,
            "total": total,
            "accuracy": round(correct / total, 4) if total else 0.0,
            "rag_decisions": rag,
            "fallbacks": total - rag,
            "per_category": {k: {"correct": v[0], "total": v[1]} for k, v in per_category.items()},
        }

    margin_sweep = [evaluate(0.50, m) for m in MARGINS]
    score_sweep = [evaluate(s, 0.03) for s in SCORES]
    result = {
        "schema_version": 1,
        "probe": Path(args.probe).name,
        "baseline": Path(args.baseline).name,
        "note": ("저장된 top-3 후보로 계산한 민감도다. 임계값을 이 표의 최댓값으로 고르면 "
                 "같은 데이터에 과적합된다. 채택 규칙은 doc/rag_design.md §6.1."),
        "margin_sweep_min_score_0.50": margin_sweep,
        "score_sweep_min_margin_0.03": score_sweep,
    }
    Path(args.out).write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n",
                              encoding="utf-8")

    print(f"# {Path(args.probe).name} / {Path(args.baseline).name} (n={len(items)})")
    print("| min_margin | accuracy | RAG | 폴백 |")
    print("|---|---|---|---|")
    for row in margin_sweep:
        mark = "**" if row["min_margin"] == 0.03 else ""
        print(f"| {mark}{row['min_margin']:.2f}{mark} | {row['correct']}/{row['total']} = "
              f"{row['accuracy']:.4f} | {row['rag_decisions']} | {row['fallbacks']} |")
    print()
    print("| min_score | accuracy | RAG | 폴백 |")
    print("|---|---|---|---|")
    for row in score_sweep:
        mark = "**" if row["min_score"] == 0.50 else ""
        print(f"| {mark}{row['min_score']:.2f}{mark} | {row['correct']}/{row['total']} = "
              f"{row['accuracy']:.4f} | {row['rag_decisions']} | {row['fallbacks']} |")
    print()
    print("현재 채택값(0.50/0.03) 카테고리별:")
    current = next(r for r in margin_sweep if r["min_margin"] == 0.03)
    for name, stats in current["per_category"].items():
        print(f"  {name:<11} {stats['correct']}/{stats['total']}")
    print(f"saved: {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
