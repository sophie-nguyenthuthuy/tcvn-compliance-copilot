"""Hybrid retriever over the standards corpus.

Two recall channels — dense (pgvector cosine) and lexical (pg_trgm) — fused
with reciprocal rank fusion. The retriever stays close to SQL so we don't
pay round-trip cost to an external vector service.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from sqlalchemy import bindparam, text
from sqlalchemy.ext.asyncio import AsyncSession

from tcvn_copilot.config import get_settings
from tcvn_copilot.rag.embedder import embed_one


@dataclass(slots=True)
class RetrievedClause:
    clause_id: UUID
    standard_code: str
    clause_number: str
    title: str | None
    text: str
    score: float


_DENSE_SQL = text(
    """
    SELECT
        c.id          AS clause_id,
        s.code        AS standard_code,
        c.clause_number,
        c.title_vi    AS title,
        c.text_vi     AS text,
        1 - (e.embedding <=> CAST(:query AS vector))  AS score
    FROM standard_clause_embeddings e
    JOIN standard_clauses c ON c.id = e.clause_id
    JOIN standards s        ON s.id = c.standard_id
    WHERE (:codes IS NULL OR s.code = ANY(:codes))
    ORDER BY e.embedding <=> CAST(:query AS vector)
    LIMIT :k
    """
).bindparams(bindparam("codes", expanding=False))


_LEXICAL_SQL = text(
    """
    SELECT
        c.id          AS clause_id,
        s.code        AS standard_code,
        c.clause_number,
        c.title_vi    AS title,
        c.text_vi     AS text,
        similarity(c.text_vi, :query) AS score
    FROM standard_clauses c
    JOIN standards s ON s.id = c.standard_id
    WHERE (:codes IS NULL OR s.code = ANY(:codes))
      AND c.text_vi % :query
    ORDER BY score DESC
    LIMIT :k
    """
)


async def retrieve(
    session: AsyncSession,
    query: str,
    *,
    standard_codes: list[str] | None = None,
    top_k: int | None = None,
) -> list[RetrievedClause]:
    """Run dense + lexical retrieval, fuse with RRF, return top_k."""
    settings = get_settings()
    k = top_k or settings.rag_top_k
    pool = settings.rag_rerank_top_n

    vector = embed_one(query)

    dense = await session.execute(
        _DENSE_SQL,
        {"query": vector, "k": pool, "codes": standard_codes},
    )
    lexical = await session.execute(
        _LEXICAL_SQL,
        {"query": query, "k": pool, "codes": standard_codes},
    )

    fused: dict[UUID, dict[str, Any]] = {}
    _rrf_merge(dense.mappings().all(), fused, weight=1.0)
    _rrf_merge(lexical.mappings().all(), fused, weight=0.7)

    ranked = sorted(fused.values(), key=lambda r: float(r["_score"]), reverse=True)[:k]
    return [
        RetrievedClause(
            clause_id=row["clause_id"],
            standard_code=str(row["standard_code"]),
            clause_number=str(row["clause_number"]),
            title=row["title"],
            text=str(row["text"]),
            score=float(row["_score"]),
        )
        for row in ranked
    ]


_RRF_CONSTANT = 60  # standard RRF k


def _rrf_merge(rows: Sequence[Any], target: dict[UUID, dict[str, Any]], *, weight: float) -> None:
    for rank, row in enumerate(rows, start=1):
        cid = row["clause_id"]
        rrf = weight / (_RRF_CONSTANT + rank)
        if cid in target:
            target[cid]["_score"] = float(target[cid]["_score"]) + rrf
        else:
            target[cid] = dict(row)
            target[cid]["_score"] = rrf
