"""Sentence-transformer embedding wrapper.

Loaded lazily so unit tests don't pay model-load cost. The model is held as a
module-level singleton — `sentence-transformers` is not safe to share across
processes, so each Celery worker / API process gets its own.
"""

from __future__ import annotations

from threading import Lock
from typing import TYPE_CHECKING

from tcvn_copilot.config import get_settings
from tcvn_copilot.core.logging import get_logger

if TYPE_CHECKING:
    from sentence_transformers import SentenceTransformer

log = get_logger(__name__)

_model: "SentenceTransformer | None" = None
_lock = Lock()


def _load_model() -> "SentenceTransformer":
    global _model  # noqa: PLW0603
    with _lock:
        if _model is None:
            from sentence_transformers import SentenceTransformer

            name = get_settings().embedding_model
            log.info("loading_embedding_model", model=name)
            _model = SentenceTransformer(name, trust_remote_code=False)
        return _model


def embed_texts(texts: list[str], *, batch_size: int = 32) -> list[list[float]]:
    """Embed a batch of strings into a list of unit-normalised vectors."""
    if not texts:
        return []
    model = _load_model()
    vectors = model.encode(
        texts,
        batch_size=batch_size,
        normalize_embeddings=True,
        show_progress_bar=False,
        convert_to_numpy=True,
    )
    return [v.tolist() for v in vectors]


def embed_one(text: str) -> list[float]:
    return embed_texts([text])[0]
