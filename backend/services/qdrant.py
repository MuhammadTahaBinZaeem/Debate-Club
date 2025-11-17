"""Qdrant vector search integration for argument memory."""
from __future__ import annotations

import hashlib
import logging
from typing import Iterable, List, Optional

import numpy as np

from backend.config import settings
from backend.models.session import Argument

try:  # pragma: no cover - optional
    from qdrant_client import QdrantClient
    from qdrant_client.http import models as qmodels
except Exception:  # pragma: no cover - library optional
    QdrantClient = None  # type: ignore[assignment]
    qmodels = None  # type: ignore[assignment]

_logger = logging.getLogger(__name__)
_COLLECTION_NAME = "letsee_arguments"
_client: Optional[QdrantClient] = None


def _ensure_client() -> Optional[QdrantClient]:
    global _client
    if not settings.qdrant_url or QdrantClient is None or qmodels is None:
        return None
    if _client is None:
        _client = QdrantClient(url=settings.qdrant_url, api_key=settings.qdrant_api_key or None)
        try:
            _client.get_collection(_COLLECTION_NAME)
        except Exception:  # pragma: no cover - network
            _client.recreate_collection(
                _COLLECTION_NAME,
                vectors_config=qmodels.VectorParams(size=64, distance=qmodels.Distance.COSINE),
            )
    return _client


def _text_to_embedding(text: str) -> List[float]:
    tokens = text.lower().split()
    vector = np.zeros(64, dtype=np.float32)
    for token in tokens:
        digest = hashlib.sha256(token.encode("utf-8")).hexdigest()
        bucket = int(digest[:4], 16) % 64
        vector[bucket] += 1.0
    norm = np.linalg.norm(vector)
    if norm:
        vector /= norm
    return vector.tolist()


def upsert_arguments(session_id: str, arguments: Iterable[Argument]) -> None:
    client = _ensure_client()
    if client is None:
        _logger.info("Skipping Qdrant upsert; client unavailable")
        return
    payload = []
    vectors = []
    ids = []
    for index, argument in enumerate(arguments):
        ids.append(int(hashlib.md5(f"{session_id}-{index}".encode("utf-8")).hexdigest()[:16], 16))
        payload.append(
            {
                "session_id": session_id,
                "turn": argument.turn_index,
                "role": argument.speaker_role.value,
                "content": argument.content,
            }
        )
        vectors.append(_text_to_embedding(argument.content))
    try:
        client.upsert(
            collection_name=_COLLECTION_NAME,
            points=qmodels.Batch(ids=ids, payloads=payload, vectors=vectors),
        )
    except Exception as exc:  # pragma: no cover - network
        _logger.exception("Failed to upsert embeddings to Qdrant: %s", exc)


def search_similar(content: str, limit: int = 5) -> List[dict]:
    client = _ensure_client()
    if client is None:
        return []
    vector = _text_to_embedding(content)
    try:
        results = client.search(
            collection_name=_COLLECTION_NAME,
            query_vector=vector,
            limit=limit,
        )
        return [hit.dict() for hit in results]
    except Exception as exc:  # pragma: no cover - network
        _logger.exception("Qdrant search failed: %s", exc)
        return []
