"""RunBook 임베딩 — Ollama 실모델 + 오프라인 Hashing 대체재.

왜 두 개인가
    비교 측정(LLM_BACKEND=fake)은 네트워크·모델 상태에 흔들리면 안 된다. Ollama가
    없거나 모델이 없으면 HashingEmbedder로 떨어지고, 이때는 **품질 주장을 하지 않는다**.
    실제로 무엇이 쓰였는지는 `name`으로 인덱스·/health·manifest에 남긴다. 기록 없는
    측정은 무효다.

계약 (classifier·index가 기대하는 것)
    name          인덱스 캐시 키. 모델이 바뀌면 재생성된다.
    dim           벡터 차원. Ollama는 첫 호출 전까지 None일 수 있다.
    embed(texts)  list[list[float]]. **L2 정규화된** 벡터를 돌려준다 → cosine = 내적.

환경변수
    RAG_EMBEDDER=auto|ollama|hashing   (기본 auto: ollama 시도 → 실패 시 hashing)
    RAG_EMBED_MODEL                    (기본 qwen3-embedding:0.6b)
    OLLAMA_BASE_URL                    (기본 http://127.0.0.1:11434)
"""
from __future__ import annotations

import hashlib
import math
import os
import re
from typing import Iterable, Sequence

import httpx

DEFAULT_MODEL = os.getenv("RAG_EMBED_MODEL", "qwen3-embedding:0.6b")
DEFAULT_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
HASH_DIM = 512

_LATIN = re.compile(r"[a-z0-9][a-z0-9_\-]*")
_HANGUL = re.compile(r"[가-힣]+")


class EmbeddingError(RuntimeError):
    """임베딩 호출 실패. classifier는 이 예외를 잡아 keyword로 폴백한다."""


def l2_normalize(vector: Sequence[float]) -> list[float]:
    norm = math.sqrt(sum(float(x) * float(x) for x in vector))
    if norm == 0.0:
        return [0.0 for _ in vector]
    return [float(x) / norm for x in vector]


def _tokens(text: str) -> list[str]:
    """영문/숫자 토큰 + 한글 문자 bigram.

    형태소 분석기 없이도 한국어 어절 일부 일치를 잡기 위한 최소 장치다.
    """
    lowered = text.lower()
    tokens = _LATIN.findall(lowered)
    for run in _HANGUL.findall(lowered):
        if len(run) == 1:
            tokens.append(run)
        else:
            tokens.extend(run[i:i + 2] for i in range(len(run) - 1))
    return tokens


class HashingEmbedder:
    """오프라인·결정론 임베더. 품질 비교의 근거로 쓰지 않는다.

    토큰 → blake2b(프로세스 간 동일) → 512차원 signed count → sublinear TF → L2.
    `PYTHONHASHSEED`에 의존하지 않으므로 실행마다 같은 벡터가 나온다.
    """

    name = f"hashing:blake2b-{HASH_DIM}"
    dim: int | None = HASH_DIM

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        return [self._embed_one(t) for t in texts]

    def _embed_one(self, text: str) -> list[float]:
        counts: dict[int, float] = {}
        for token in _tokens(text):
            digest = hashlib.blake2b(token.encode("utf-8"), digest_size=8).digest()
            value = int.from_bytes(digest, "big")
            index = value % HASH_DIM
            sign = 1.0 if (value // HASH_DIM) % 2 == 0 else -1.0
            counts[index] = counts.get(index, 0.0) + sign
        vector = [0.0] * HASH_DIM
        for index, count in counts.items():
            if count == 0.0:
                continue
            # sublinear TF — 같은 단어의 과도한 반복이 방향을 독점하지 않게.
            vector[index] = math.copysign(1.0 + math.log(abs(count)), count)
        return l2_normalize(vector)


class OllamaEmbedder:
    """Ollama 임베딩 모델. `/api/embed` 우선, 실패 시 `/api/embeddings` 폴백."""

    def __init__(self, model: str = DEFAULT_MODEL, base_url: str = DEFAULT_BASE_URL,
                 connect_timeout: float = 2.0, read_timeout: float = 30.0) -> None:
        self.model = model
        self.base_url = base_url.rstrip("/")
        self._timeout = httpx.Timeout(read_timeout, connect=connect_timeout)
        self.dim: int | None = None

    @property
    def name(self) -> str:
        return f"ollama:{self.model}"

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        items = list(texts)
        if not items:
            return []
        raw = self._embed_batch(items)
        if len(raw) != len(items):
            raise EmbeddingError(
                f"임베딩 개수 불일치: 요청 {len(items)} / 응답 {len(raw)}")
        vectors = [l2_normalize(v) for v in raw]
        self.dim = len(vectors[0])
        return vectors

    def _embed_batch(self, texts: list[str]) -> list[list[float]]:
        try:
            with httpx.Client(timeout=self._timeout) as client:
                response = client.post(f"{self.base_url}/api/embed",
                                       json={"model": self.model, "input": texts})
                if response.status_code == 200:
                    payload = response.json()
                    embeddings = payload.get("embeddings")
                    if isinstance(embeddings, list) and embeddings:
                        return embeddings
                # 구버전 서버·모델 호환: 문장 단위 엔드포인트로 폴백.
                return [self._embed_one(client, text) for text in texts]
        except httpx.HTTPError as exc:      # 연결·타임아웃·프로토콜
            raise EmbeddingError(f"Ollama 임베딩 호출 실패: {exc}") from exc
        except ValueError as exc:            # JSON 파싱
            raise EmbeddingError(f"Ollama 응답 파싱 실패: {exc}") from exc

    def _embed_one(self, client: httpx.Client, text: str) -> list[float]:
        response = client.post(f"{self.base_url}/api/embeddings",
                               json={"model": self.model, "prompt": text})
        response.raise_for_status()
        vector = response.json().get("embedding")
        if not isinstance(vector, list) or not vector:
            raise EmbeddingError("Ollama /api/embeddings 응답에 embedding이 없습니다")
        return vector

    def probe(self) -> None:
        """모델이 실제로 응답하는지 확인. 실패하면 EmbeddingError."""
        self.embed(["ping"])


def build_embedder(preference: str | None = None) -> object:
    """RAG_EMBEDDER 값에 따라 임베더를 만든다.

    auto(기본)는 Ollama 프로브 실패 시 HashingEmbedder로 대체한다.
    ollama를 명시하면 실패를 숨기지 않고 예외를 올린다 — "왜 품질이 낮지"를
    조용히 넘기지 않기 위해서다.
    """
    choice = (preference or os.getenv("RAG_EMBEDDER", "auto")).strip().lower()
    if choice == "hashing":
        return HashingEmbedder()
    if choice == "ollama":
        embedder = OllamaEmbedder()
        embedder.probe()
        return embedder
    if choice != "auto":
        raise ValueError(f"RAG_EMBEDDER 값이 올바르지 않습니다: {choice!r} (auto|ollama|hashing)")
    embedder = OllamaEmbedder()
    try:
        embedder.probe()
        return embedder
    except EmbeddingError:
        return HashingEmbedder()


def embedder_report(embedder: object) -> dict:
    """측정 기록용 요약 — /health·manifest에 그대로 넣는다."""
    return {
        "name": getattr(embedder, "name", "unknown"),
        "dim": getattr(embedder, "dim", None),
        "offline": isinstance(embedder, HashingEmbedder),
    }
