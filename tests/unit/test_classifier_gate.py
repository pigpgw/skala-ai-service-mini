"""RAG 분류기 게이트 단위 테스트 — 5분기 판정이 약속대로 동작하는지.

판정 5분기 (doc/rag_design.md §6)
    disabled / index_unavailable / embed_failed / low_score / low_margin → keyword
    그 외 → rag

네트워크에 의존하지 않도록 `HashingEmbedder`와 임시 인덱스 경로를 쓴다.
(측정용 캐시 `data/runbook_index.json`을 건드리지 않는다.)
"""
from __future__ import annotations

import httpx
import pytest

from agent.rag.classifier import RagClassifier, format_query
from agent.rag.embedder import EmbeddingError, HashingEmbedder
from agent.rag.index import load_or_build

COLLECTED = [{
    "source": "monitoring",
    "data": {
        "system_name": "log-service",
        "status": "degraded",
        "alerts": ["disk usage 95% on /var/log", "disk space low"],
    },
}]


@pytest.fixture(scope="module")
def index(tmp_path_factory):
    cache = tmp_path_factory.mktemp("rag-index") / "index.json"
    return load_or_build(HashingEmbedder(), index_path=cache)


def _fallback(_collected) -> str:
    return "disk-full"


def test_format_query_has_four_sections():
    text = format_query("디스크 찼어요", COLLECTED)
    assert "[사용자 질문]" in text
    assert "[시스템]" in text and "log-service" in text
    assert "[상태]" in text and "degraded" in text
    assert "[알림]" in text and "disk usage 95%" in text


def test_disabled_falls_back_to_keyword(index):
    classifier = RagClassifier(index, HashingEmbedder(), enabled=False,
                               keyword_fallback=_fallback)
    result = classifier.classify("디스크 찼어요", COLLECTED)
    assert result.source == "keyword"
    assert result.reason == "disabled"
    assert result.incident_type == "disk-full"


def test_missing_index_falls_back_to_keyword():
    classifier = RagClassifier(None, HashingEmbedder(), keyword_fallback=_fallback)
    result = classifier.classify("디스크 찼어요", COLLECTED)
    assert result.source == "keyword"
    assert result.reason == "index_unavailable"


def test_embed_failure_falls_back_to_keyword(index):
    class BrokenEmbedder:
        name = "broken"
        dim = 8

        def embed(self, texts):
            raise EmbeddingError("테스트용 실패")

    classifier = RagClassifier(index, BrokenEmbedder(), keyword_fallback=_fallback)
    result = classifier.classify("디스크 찼어요", COLLECTED)
    assert result.source == "keyword"
    assert result.reason == "embed_failed"


def test_http_error_also_falls_back(index):
    class HttpBrokenEmbedder:
        name = "broken-http"
        dim = 8

        def embed(self, texts):
            raise httpx.ConnectError("연결 실패")

    classifier = RagClassifier(index, HttpBrokenEmbedder(), keyword_fallback=_fallback)
    result = classifier.classify("디스크 찼어요", COLLECTED)
    assert result.source == "keyword"
    assert result.reason == "embed_failed"


def test_low_score_falls_back_to_keyword(index):
    classifier = RagClassifier(index, HashingEmbedder(), min_score=0.99,
                               keyword_fallback=_fallback)
    result = classifier.classify("디스크 찼어요", COLLECTED)
    assert result.source == "keyword"
    assert result.reason == "low_score"
    assert result.score is not None          # 왜 미달인지 수치는 남긴다


def test_low_margin_falls_back_to_keyword(index):
    classifier = RagClassifier(index, HashingEmbedder(), min_score=0.0,
                               min_margin=1.01, keyword_fallback=_fallback)
    result = classifier.classify("디스크 찼어요", COLLECTED)
    assert result.source == "keyword"
    assert result.reason == "low_margin"


def test_confident_case_uses_rag(index):
    classifier = RagClassifier(index, HashingEmbedder(), min_score=0.0,
                               min_margin=0.0, keyword_fallback=_fallback)
    result = classifier.classify("디스크 찼어요", COLLECTED)
    assert result.source == "rag"
    assert result.reason == "ok"
    assert result.doc_id in {doc.id for doc in index.docs}
    assert result.score is not None and result.margin is not None
    assert result.elapsed_ms >= 0


def test_from_env_reads_threshold_environment(monkeypatch):
    monkeypatch.setenv("RAG_ENABLED", "false")
    monkeypatch.setenv("RAG_MIN_SCORE", "0.42")
    monkeypatch.setenv("RAG_MIN_MARGIN", "0.07")
    classifier = RagClassifier.from_env(None, HashingEmbedder(), keyword_fallback=_fallback)
    assert classifier.enabled is False
    assert classifier.min_score == 0.42
    assert classifier.min_margin == 0.07
