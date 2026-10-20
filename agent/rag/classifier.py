"""incident_type 판정 — RAG 우선, 실패 시 기존 keyword 폴백.

교체 범위는 `agent/graph.py::replan_check_node`의 **incident_type 선택 한 줄**이다.
`_classify_incident_type()`은 삭제하지 않는다. RAG가 확신하지 못하면 그 함수가 그대로
정답을 낸다 — 개선이 기존 동작을 깨지 않게 하는 안전장치다.

판정 5분기 (doc/rag_design.md §6)
    disabled / index_unavailable / embed_failed / low_score / low_margin  → keyword
    그 외                                                                → rag

임계값 기본값은 **가정**이다. 12문항 스윕으로 확정하기 전에는 보고서 수치로 쓰지 않는다.
"""
from __future__ import annotations

import os
import time
from dataclasses import dataclass, field
from typing import Callable, Sequence

import httpx

from .embedder import EmbeddingError
from .index import RagIndex

DEFAULT_MIN_SCORE = 0.50
DEFAULT_MIN_MARGIN = 0.03
DEFAULT_TOP_K = 3

RAG_SOURCE = "rag"
KEYWORD_SOURCE = "keyword"


@dataclass(frozen=True)
class ClassifyResult:
    incident_type: str
    source: str                     # "rag" | "keyword"
    reason: str                     # ok | disabled | index_unavailable | embed_failed | low_score | low_margin
    score: float | None = None      # top1 cosine
    margin: float | None = None     # top1 - top2
    doc_id: str | None = None
    candidates: tuple[tuple[str, float], ...] = field(default_factory=tuple)
    elapsed_ms: float = 0.0

    @property
    def used_rag(self) -> bool:
        return self.source == RAG_SOURCE


def _monitoring_items(collected: Sequence[dict]) -> list[dict]:
    items = []
    for entry in collected or []:
        if not isinstance(entry, dict) or entry.get("source") != "monitoring":
            continue
        data = entry.get("data")
        if isinstance(data, dict):
            items.append(data)
    return items


def format_query(query: str | None, collected: Sequence[dict]) -> str:
    """분류 입력 문자열. 포맷을 고정해야 Before/After 비교가 성립한다."""
    items = _monitoring_items(collected)
    systems = [str(item.get("system_name") or "unknown") for item in items]
    states = [f"{item.get('system_name') or 'unknown'}={item.get('status') or 'unknown'}"
              for item in items]
    alerts = []
    for item in items:
        values = item.get("alerts") or []
        text = ", ".join(str(v) for v in values if str(v).strip())
        if text:
            alerts.append(f"{item.get('system_name') or 'unknown'}: {text}")
    return "\n".join([
        f"[사용자 질문] {(query or '').strip() or '-'}",
        f"[시스템] {', '.join(systems) if systems else '-'}",
        f"[상태] {', '.join(states) if states else '-'}",
        f"[알림] {'; '.join(alerts) if alerts else '-'}",
    ])


def _default_keyword_fallback() -> Callable[[Sequence[dict]], str]:
    # 순환 import 회피: graph는 rag를 import하지 않지만, 호출 시점 import가 안전하다.
    from ..graph import _classify_incident_type
    return _classify_incident_type


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() not in {"0", "false", "no", "off", ""}


def _env_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    try:
        return float(raw)
    except ValueError:
        return default


class RagClassifier:
    def __init__(self, index: RagIndex | None, embedder,
                 *, enabled: bool = True,
                 min_score: float = DEFAULT_MIN_SCORE,
                 min_margin: float = DEFAULT_MIN_MARGIN,
                 keyword_fallback: Callable[[Sequence[dict]], str] | None = None,
                 top_k: int = DEFAULT_TOP_K) -> None:
        self.index = index
        self.embedder = embedder
        self.enabled = enabled
        self.min_score = float(min_score)
        self.min_margin = float(min_margin)
        self.top_k = int(top_k)
        self._keyword_fallback = keyword_fallback

    @classmethod
    def from_env(cls, index: RagIndex | None, embedder,
                 keyword_fallback: Callable[[Sequence[dict]], str] | None = None) -> "RagClassifier":
        return cls(
            index,
            embedder,
            enabled=_env_bool("RAG_ENABLED", True),
            min_score=_env_float("RAG_MIN_SCORE", DEFAULT_MIN_SCORE),
            min_margin=_env_float("RAG_MIN_MARGIN", DEFAULT_MIN_MARGIN),
            keyword_fallback=keyword_fallback,
        )

    def classify(self, query: str | None, collected: Sequence[dict]) -> ClassifyResult:
        started = time.perf_counter()

        def result(incident_type: str, source: str, reason: str, *,
                   score: float | None = None, margin: float | None = None,
                   doc_id: str | None = None,
                   candidates: Sequence[tuple[str, float]] = ()) -> ClassifyResult:
            return ClassifyResult(
                incident_type=incident_type,
                source=source,
                reason=reason,
                score=None if score is None else round(score, 4),
                margin=None if margin is None else round(margin, 4),
                doc_id=doc_id,
                candidates=tuple((str(i), round(float(s), 4)) for i, s in candidates),
                elapsed_ms=round((time.perf_counter() - started) * 1000, 2),
            )

        if not self.enabled:
            return result(self._fallback(collected), KEYWORD_SOURCE, "disabled")
        if self.index is None or not self.index.docs:
            return result(self._fallback(collected), KEYWORD_SOURCE, "index_unavailable")

        text = format_query(query, collected)
        try:
            vector = self.embedder.embed([text])[0]
        except (EmbeddingError, httpx.HTTPError):
            return result(self._fallback(collected), KEYWORD_SOURCE, "embed_failed")

        ranked = self.index.search(vector, k=max(2, self.top_k))
        top1_id, top1_score = ranked[0]
        top2_score = ranked[1][1] if len(ranked) > 1 else -1.0
        margin = top1_score - top2_score

        if top1_score < self.min_score:
            return result(self._fallback(collected), KEYWORD_SOURCE, "low_score",
                          score=top1_score, margin=margin, candidates=ranked)
        if margin < self.min_margin:
            return result(self._fallback(collected), KEYWORD_SOURCE, "low_margin",
                          score=top1_score, margin=margin, candidates=ranked)
        return result(top1_id, RAG_SOURCE, "ok", score=top1_score, margin=margin,
                      doc_id=top1_id, candidates=ranked)

    def _fallback(self, collected: Sequence[dict]) -> str:
        if self._keyword_fallback is None:
            self._keyword_fallback = _default_keyword_fallback()
        return self._keyword_fallback(collected)
