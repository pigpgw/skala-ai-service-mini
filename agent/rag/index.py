"""RunBook 검색 인덱스 — 문서 텍스트 → 벡터 → JSON 캐시.

무효화(D3)는 "내용 해시"가 아니라 **파일 목록 + mtime + size + 임베더 이름**으로 판정한다.
이유: 기동 경로에서 runbook 본문 해시를 매번 계산하면 빌드 비용과 별 차이가 없고,
mtime/size는 편집·추가·삭제를 실용적으로 잡아낸다. 대신 재빌드 후 `index_sha256`을
manifest에 남겨 "이번 측정이 어떤 인덱스였는지"를 사후에 특정할 수 있게 한다.

생성물 `data/runbook_index.json`은 커밋하지 않는다(.gitignore).
"""
from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Sequence

SCHEMA_VERSION = 1

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
RUNBOOKS_DIR = REPO_ROOT / "data" / "runbooks"
META_PATH = RUNBOOKS_DIR / "meta.json"
INDEX_PATH = REPO_ROOT / "data" / "runbook_index.json"


def resolve_index_path() -> Path:
    """인덱스 캐시 경로. `RAG_INDEX_PATH`로 바꿀 수 있다.

    왜 바꿀 수 있게 했나: 테스트가 측정용 캐시(`data/runbook_index.json`)를 덮어쓰면
    "이번 측정의 인덱스가 뭐였는지"가 사라진다. 테스트는 임시 경로를 쓴다.
    """
    override = os.environ.get("RAG_INDEX_PATH", "").strip()
    return Path(override) if override else INDEX_PATH

VECTOR_DECIMALS = 6


@dataclass(frozen=True)
class RagDoc:
    id: str
    title: str
    text: str
    vector: tuple[float, ...]


@dataclass(frozen=True)
class RagIndex:
    embedder_name: str
    dim: int
    docs: tuple[RagDoc, ...]
    fingerprint: dict
    index_sha256: str
    built_at: str
    cache_hit: bool = False

    def search(self, query_vector: Sequence[float], k: int = 3) -> list[tuple[str, float]]:
        """정규화된 질의 벡터와의 내적(=cosine) 상위 k. 동점은 id 오름차순."""
        scores = [
            (doc.id, sum(q * v for q, v in zip(query_vector, doc.vector)))
            for doc in self.docs
        ]
        scores.sort(key=lambda pair: (-pair[1], pair[0]))
        return scores[:k]

    def document(self, doc_id: str) -> RagDoc | None:
        for doc in self.docs:
            if doc.id == doc_id:
                return doc
        return None


def _meta_entries(meta_path: Path) -> dict:
    try:
        payload = json.loads(meta_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    entries = payload.get("incident_types")
    return entries if isinstance(entries, dict) else {}


def _runbook_files(runbooks_dir: Path) -> dict[str, Path]:
    if not runbooks_dir.is_dir():
        return {}
    return {path.stem: path for path in sorted(runbooks_dir.glob("*.md"))}


def doc_text(doc_id: str, meta_entry: dict | None, body: str) -> str:
    """검색 대상 텍스트. meta가 있으면 증상·키워드를 앞에 붙여 재현율을 올린다."""
    entry = meta_entry or {}
    parts: list[str] = []
    title = str(entry.get("title") or "").strip()
    if title:
        parts.append(title)
    else:
        first_heading = next(
            (line.lstrip("# ").strip() for line in body.splitlines() if line.startswith("#")),
            doc_id,
        )
        parts.append(first_heading)
    for key in ("symptoms", "keywords", "aliases"):
        values = entry.get(key) or []
        if isinstance(values, list) and values:
            parts.append(", ".join(str(v) for v in values))
    parts.append(body)
    return "\n".join(p for p in parts if p)


def fingerprint(runbooks_dir: Path = RUNBOOKS_DIR,
                meta_path: Path = META_PATH) -> dict:
    def stat(path: Path) -> dict | None:
        try:
            info = path.stat()
        except OSError:
            return None
        return {"mtime": round(info.st_mtime, 3), "size": info.st_size}

    return {
        "meta": stat(meta_path),
        "runbooks": {name: stat(path) for name, path in _runbook_files(runbooks_dir).items()},
    }


def _digest(docs: Sequence[RagDoc]) -> str:
    payload = json.dumps(
        [{"id": d.id, "dim": len(d.vector), "vector": list(d.vector)} for d in docs],
        ensure_ascii=False, sort_keys=True, separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def build_index(embedder, runbooks_dir: Path | None = None,
                meta_path: Path | None = None,
                index_path: Path | None = None) -> RagIndex:
    """runbook 파일을 읽어 인덱스를 새로 만든다. 캐시는 쓰기만 한다."""
    runbooks_dir = runbooks_dir or RUNBOOKS_DIR
    meta_path = meta_path or META_PATH
    index_path = index_path or resolve_index_path()
    files = _runbook_files(runbooks_dir)
    if not files:
        raise FileNotFoundError(f"runbook 파일이 없습니다: {runbooks_dir}")
    meta = _meta_entries(meta_path)

    ids: list[str] = []
    texts: list[str] = []
    titles: list[str] = []
    for doc_id, path in files.items():
        body = path.read_text(encoding="utf-8")
        entry = meta.get(doc_id)
        texts.append(doc_text(doc_id, entry, body))
        ids.append(doc_id)
        titles.append(str((entry or {}).get("title") or doc_id))

    vectors = embedder.embed(texts)
    docs = tuple(
        RagDoc(
            id=doc_id,
            title=title,
            text=text,
            vector=tuple(round(float(x), VECTOR_DECIMALS) for x in vector),
        )
        for doc_id, title, text, vector in zip(ids, titles, texts, vectors)
    )
    dim = len(docs[0].vector)
    index = RagIndex(
        embedder_name=getattr(embedder, "name", "unknown"),
        dim=dim,
        docs=docs,
        fingerprint=fingerprint(runbooks_dir, meta_path),
        index_sha256=_digest(docs),
        built_at=datetime.now().astimezone().isoformat(timespec="seconds"),
        cache_hit=False,
    )
    _write_cache(index, index_path)
    return index


def _write_cache(index: RagIndex, index_path: Path) -> None:
    payload = {
        "schema_version": SCHEMA_VERSION,
        "embedder": {"name": index.embedder_name, "dim": index.dim, "normalized": True},
        "source": {"runbooks_dir": "data/runbooks", "meta": "data/runbooks/meta.json"},
        "fingerprint": index.fingerprint,
        "docs": [
            {"id": d.id, "title": d.title, "text": d.text, "vector": list(d.vector)}
            for d in index.docs
        ],
        "index_sha256": index.index_sha256,
        "built_at": index.built_at,
    }
    index_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = index_path.with_suffix(index_path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
                   encoding="utf-8")
    tmp.replace(index_path)   # 원자적 교체 — 중간에 깨진 인덱스를 읽지 않게.


def _cache_is_valid(cached: dict, embedder, current: dict) -> bool:
    if cached.get("schema_version") != SCHEMA_VERSION:
        return False
    embedder_info = cached.get("embedder") or {}
    if embedder_info.get("name") != getattr(embedder, "name", "unknown"):
        return False
    if cached.get("fingerprint") != current:
        return False
    docs = cached.get("docs")
    if not isinstance(docs, list) or not docs:
        return False
    dim = embedder_info.get("dim")
    return all(isinstance(d.get("vector"), list) and len(d["vector"]) == dim for d in docs)


def load_or_build(embedder, runbooks_dir: Path | None = None,
                  meta_path: Path | None = None,
                  index_path: Path | None = None) -> RagIndex:
    """캐시가 유효하면 읽고, 아니면 빌드한다. cache_hit으로 사실을 남긴다."""
    runbooks_dir = runbooks_dir or RUNBOOKS_DIR
    meta_path = meta_path or META_PATH
    index_path = index_path or resolve_index_path()
    current = fingerprint(runbooks_dir, meta_path)
    try:
        cached = json.loads(index_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        cached = None

    if cached and _cache_is_valid(cached, embedder, current):
        docs = tuple(
            RagDoc(id=d["id"], title=d["title"], text=d["text"],
                   vector=tuple(float(x) for x in d["vector"]))
            for d in cached["docs"]
        )
        return RagIndex(
            embedder_name=cached["embedder"]["name"],
            dim=int(cached["embedder"]["dim"]),
            docs=docs,
            fingerprint=cached["fingerprint"],
            index_sha256=cached.get("index_sha256") or _digest(docs),
            built_at=cached.get("built_at", ""),
            cache_hit=True,
        )
    return build_index(embedder, runbooks_dir, meta_path, index_path)
