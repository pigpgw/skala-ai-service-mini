"""지표 계산 단위 테스트 — 보고서 수치의 계산기를 고정한다.

macro-F1 계산이 틀리면 보고서의 모든 수치가 틀어진다. 기준값을 손으로 계산한
작은 예시로 대조한다.
"""
from __future__ import annotations

import metrics


def test_accuracy_counts_and_ratio():
    rows = [{"correct": True}, {"correct": False}, {"correct": True}]
    correct, accuracy = metrics.accuracy(rows)
    assert correct == 2
    assert accuracy == 0.6667
    assert metrics.accuracy([]) == (0, 0.0)


def test_percentile_linear_interpolation():
    values = [10, 20, 30, 40]
    assert metrics.percentile(values, 0) == 10.0
    assert metrics.percentile(values, 100) == 40.0
    assert metrics.percentile(values, 50) == 25.0
    assert metrics.percentile([7], 95) == 7.0
    assert metrics.percentile([], 50) == 0.0


def test_latency_summary_fields():
    summary = metrics.latency_summary([100.0, 200.0, 300.0])
    assert summary["count"] == 3
    assert summary["p50_ms"] == 200.0
    assert summary["p95_ms"] == 290.0
    assert summary["max_ms"] == 300.0
    assert metrics.latency_summary([])["count"] == 0


def test_per_type_scores_precision_recall():
    rows = [
        {"expected_type": "a", "predicted_type": "a", "correct": True},
        {"expected_type": "a", "predicted_type": "a", "correct": True},
        {"expected_type": "a", "predicted_type": "b", "correct": False},
        {"expected_type": "b", "predicted_type": "a", "correct": False},
    ]
    scores = metrics.per_type_scores(rows, ["a", "b"])
    assert scores["a"]["support"] == 3
    assert scores["a"]["precision"] == 0.6667      # TP 2 / (TP 2 + FP 1)
    assert scores["a"]["recall"] == 0.6667         # TP 2 / (TP 2 + FN 1)
    assert scores["a"]["f1"] == 0.6667
    assert scores["b"]["recall"] == 0.0


def test_macro_f1_excludes_zero_support_types():
    rows = [
        {"expected_type": "a", "predicted_type": "a", "correct": True},
        {"expected_type": "a", "predicted_type": "a", "correct": True},
    ]
    # "unused"는 support 0 → 평균에서 제외돼야 한다
    assert metrics.macro_f1(rows, ["a", "unused"]) == 1.0
    assert metrics.macro_f1([], ["a"]) == 0.0


def test_confusion_matrix_records_mispredictions():
    rows = [
        {"expected_type": "a", "predicted_type": "b"},
        {"expected_type": "a", "predicted_type": "a"},
        {"expected_type": "b", "predicted_type": "b"},
    ]
    matrix = metrics.confusion_matrix(rows, ["a", "b"])
    assert matrix["a"] == {"b": 1, "a": 1}
    assert matrix["b"] == {"b": 1}


def test_category_scores_and_fallback_rate():
    rows = [
        {"category": "single", "correct": True, "source": "rag"},
        {"category": "single", "correct": False, "source": "keyword"},
        {"category": "multi", "correct": True, "source": "keyword"},
    ]
    categories = metrics.category_scores(rows)
    assert categories["single"] == {"correct": 1, "total": 2, "accuracy": 0.5}
    fallback = metrics.fallback_rate(rows)
    assert fallback["fallback"] == 2
    assert fallback["fallback_rate"] == 0.6667


def test_coverage_counts_unknown_lookups():
    collected = [
        [{"source": "monitoring", "data": {"system_name": "a", "status": "degraded"}},
         {"source": "monitoring", "data": {"system_name": "b", "status": "unknown"}}],
        [{"source": "monitoring", "data": {"system_name": "c", "status": "healthy"}}],
    ]
    result = metrics.coverage(collected)
    assert result["system_lookups"] == 3
    assert result["unknown_lookups"] == 1
    assert result["unknown_rate"] == 0.3333
    assert result["unknown_systems"] == ["b"]


def test_reproducibility_detects_difference():
    same = metrics.reproducibility([{"a": "x"}, {"a": "x"}])
    assert same["identical"] is True
    diff = metrics.reproducibility([{"a": "x"}, {"a": "y"}])
    assert diff["identical"] is False
    assert diff["diffs"] == [{"repeat": 2, "id": "a", "first": "x", "other": "y"}]
