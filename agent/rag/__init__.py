"""RAG 기반 RunBook 선택 (E1).

구성
    embedder.py   텍스트 → 벡터 (Ollama 실모델 / 오프라인 Hashing)
    index.py      runbook 문서 → 검색 인덱스 (+ JSON 캐시·무효화)
    classifier.py 질의+모니터링 → incident_type (판정 5분기, keyword 폴백)

설계: doc/rag_design.md
측정 기준선: eval/baseline_keyword.json (12문항 8/12)
"""
from .classifier import ClassifyResult, RagClassifier, format_query
from .embedder import EmbeddingError, HashingEmbedder, OllamaEmbedder, build_embedder
from .index import RagDoc, RagIndex, build_index, load_or_build

__all__ = [
    "ClassifyResult",
    "RagClassifier",
    "format_query",
    "EmbeddingError",
    "HashingEmbedder",
    "OllamaEmbedder",
    "build_embedder",
    "RagDoc",
    "RagIndex",
    "build_index",
    "load_or_build",
]
