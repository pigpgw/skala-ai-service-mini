"""평가 지표 계산 — 단위 테스트 대상 모듈.

왜 별도 파일인가
    지표 계산 로직이 스크립트 안에 흩어지면 "어떤 수치를 보고서에 썼는지"를
    검증할 방법이 없다. 여기 한 파일로 모으고 `tests/unit/test_metrics.py`로
    고정한다(예: F1 계산기가 틀리면 전체 보고서 수치가 틀어진다).

구하는 것
    - accuracy, macro-F1, 유형별 precision/recall/F1/support
    - 혼동 행렬(오분류가 어느 유형으로 갔는지)
    - 카테고리별 정확도, 폴백률, 커버리지(unknown 비율)
    - 지연 percentiles(p50/p95) — 선형 보간 방식이라 n=1도 정의된다
"""
from __future__ import annotations

from collections import Counter, defaultdict
from typing import Iterable, Sequence


def accuracy(rows: Sequence[dict]) -> tuple[int, float]:
    """(정답 수, 정확도). rows의 'correct' 필드를 신뢰한다."""
    if not rows:
        return 0, 0.0
    correct = sum(1 for row in rows if row.get("correct"))
    return correct, round(correct / len(rows), 4)


def percentile(values: Sequence[float], p: float) -> float:
    """선형 보간 percentiles. p는 0~100."""
    if not values:
        return 0.0
    ordered = sorted(float(v) for v in values)
    if len(ordered) == 1:
        return round(ordered[0], 2)
    rank = (p / 100) * (len(ordered) - 1)
    low = int(rank)
    high = min(low + 1, len(ordered) - 1)
    weight = rank - low
    return round(ordered[low] * (1 - weight) + ordered[high] * weight, 2)


def latency_summary(values: Sequence[float]) -> dict:
    if not values:
        return {"count": 0, "p50_ms": 0.0, "p95_ms": 0.0, "mean_ms": 0.0, "max_ms": 0.0}
    return {
        "count": len(values),
        "p50_ms": percentile(values, 50),
        "p95_ms": percentile(values, 95),
        "mean_ms": round(sum(values) / len(values), 2),
        "max_ms": round(max(values), 2),
    }


def per_type_scores(rows: Sequence[dict], types: Iterable[str]) -> dict:
    """유형별 precision/recall/F1/support. support=0 유형은 macro-F1에서 제외한다."""
    types = list(types)
    tp = Counter()
    predicted = Counter()
    actual = Counter()
    for row in rows:
        expected = row.get("expected_type")
        got = row.get("predicted_type")
        actual[expected] += 1
        predicted[got] += 1
        if expected == got:
            tp[expected] += 1

    scores = {}
    for name in types:
        support = actual.get(name, 0)
        tp_n = tp.get(name, 0)
        fp_n = predicted.get(name, 0) - tp_n
        fn_n = support - tp_n
        precision = tp_n / (tp_n + fp_n) if (tp_n + fp_n) else 0.0
        recall = tp_n / (tp_n + fn_n) if (tp_n + fn_n) else 0.0
        f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0
        scores[name] = {
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1": round(f1, 4),
            "support": support,
            "predicted_count": predicted.get(name, 0),
        }
    return scores


def macro_f1(rows: Sequence[dict], types: Iterable[str]) -> float:
    """유형별 F1 평균. support=0 유형은 평균에서 제외하고 제외 목록을 함께 알린다."""
    scores = per_type_scores(rows, types)
    used = [s["f1"] for s in scores.values() if s["support"] > 0]
    if not used:
        return 0.0
    return round(sum(used) / len(used), 4)


def confusion_matrix(rows: Sequence[dict], types: Iterable[str]) -> dict:
    """expected → predicted 카운트."""
    matrix: dict[str, Counter] = defaultdict(Counter)
    for row in rows:
        matrix[row.get("expected_type")][row.get("predicted_type")] += 1
    return {expected: dict(preds) for expected, preds in matrix.items()}


def category_scores(rows: Sequence[dict]) -> dict:
    """카테고리별 정확도."""
    buckets: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    for row in rows:
        bucket = buckets[row.get("category", "unknown")]
        bucket[1] += 1
        bucket[0] += int(bool(row.get("correct")))
    return {name: {"correct": ok, "total": total,
                   "accuracy": round(ok / total, 4) if total else 0.0}
            for name, (ok, total) in buckets.items()}


def fallback_rate(rows: Sequence[dict]) -> dict:
    """RAG을 쓰지 않고 keyword로 내려간 비율."""
    total = len(rows)
    fallback = sum(1 for row in rows if row.get("source") == "keyword")
    return {
        "total": total,
        "fallback": fallback,
        "fallback_rate": round(fallback / total, 4) if total else 0.0,
    }


def coverage(collected_rows: Sequence[Sequence[dict]]) -> dict:
    """모니터링 조회 중 데이터가 없어 unknown이 된 비율."""
    lookups = 0
    unknown = 0
    unknown_systems: set[str] = set()
    for collected in collected_rows:
        for entry in collected or []:
            if entry.get("source") != "monitoring":
                continue
            data = entry.get("data") or {}
            lookups += 1
            if data.get("status") == "unknown":
                unknown += 1
                unknown_systems.add(str(data.get("system_name")))
    return {
        "system_lookups": lookups,
        "unknown_lookups": unknown,
        "unknown_rate": round(unknown / lookups, 4) if lookups else 0.0,
        "unknown_systems": sorted(unknown_systems),
    }


def reproducibility(prediction_sets: Sequence[dict[str, str]]) -> dict:
    """반복 실행의 예측이 같은지. 다른 문항은 목록으로 남긴다."""
    if len(prediction_sets) < 2:
        return {"repeats": len(prediction_sets), "identical": True, "diffs": []}
    base = prediction_sets[0]
    diffs = []
    for index, other in enumerate(prediction_sets[1:], start=2):
        for item_id, predicted in base.items():
            if other.get(item_id) != predicted:
                diffs.append({"repeat": index, "id": item_id,
                              "first": predicted, "other": other.get(item_id)})
    return {"repeats": len(prediction_sets), "identical": not diffs, "diffs": diffs}
