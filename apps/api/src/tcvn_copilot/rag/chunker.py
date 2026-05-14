"""Clause-aware chunker for TCVN/QCVN documents.

Standards docs are *structurally* chunkable: each numbered clause is already a
coherent unit. We split by clause boundary first, then sub-chunk only if a
clause exceeds the embedding context window.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

import tiktoken

from tcvn_copilot.config import get_settings

_TOKEN_ENCODER = tiktoken.get_encoding("cl100k_base")


@dataclass(slots=True, frozen=True)
class Chunk:
    clause_number: str
    title: str | None
    text: str
    path: str | None
    ordinal: int
    token_count: int


# Matches Vietnamese standard clause headers:
#   "3.2.4 Lối thoát nạn"
#   "Điều 5. Phạm vi áp dụng"
_CLAUSE_HEAD = re.compile(
    r"""^
        (?:Điều\s+(?P<art>\d+(?:\.\d+)*)\.?|     # "Điều 5."
            (?P<num>\d+(?:\.\d+){0,4})\.?)         # "3.2.4"
        \s*
        (?P<title>[^\n]{0,200})
    """,
    re.MULTILINE | re.VERBOSE,
)


def _token_count(text: str) -> int:
    return len(_TOKEN_ENCODER.encode(text))


def chunk_standard(raw_text: str, *, path: str | None = None) -> list[Chunk]:
    """Split a standard document into per-clause chunks."""
    settings = get_settings()
    max_tokens = settings.rag_chunk_size_tokens
    overlap = settings.rag_chunk_overlap_tokens

    matches = list(_CLAUSE_HEAD.finditer(raw_text))
    if not matches:
        # No clauses detected — fall back to size-based chunking.
        return _size_chunks(raw_text, path=path, max_tokens=max_tokens, overlap=overlap)

    chunks: list[Chunk] = []
    for i, m in enumerate(matches):
        start = m.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(raw_text)
        body = raw_text[start:end].strip()
        clause_number = m.group("art") or m.group("num")
        title = (m.group("title") or "").strip() or None
        n_tokens = _token_count(body)
        if n_tokens <= max_tokens:
            chunks.append(
                Chunk(
                    clause_number=clause_number,
                    title=title,
                    text=body,
                    path=path,
                    ordinal=i,
                    token_count=n_tokens,
                )
            )
            continue

        # Long clause — split into overlapping windows but keep the clause head.
        sub = _size_chunks(body, path=path, max_tokens=max_tokens, overlap=overlap)
        for j, sc in enumerate(sub):
            chunks.append(
                Chunk(
                    clause_number=f"{clause_number}#{j}",
                    title=title,
                    text=sc.text,
                    path=path,
                    ordinal=i * 1000 + j,
                    token_count=sc.token_count,
                )
            )
    return chunks


def _size_chunks(
    text: str,
    *,
    path: str | None,
    max_tokens: int,
    overlap: int,
) -> list[Chunk]:
    tokens = _TOKEN_ENCODER.encode(text)
    step = max(1, max_tokens - overlap)
    out: list[Chunk] = []
    for i, start in enumerate(range(0, len(tokens), step)):
        window = tokens[start : start + max_tokens]
        body = _TOKEN_ENCODER.decode(window)
        out.append(
            Chunk(
                clause_number=f"chunk-{i}",
                title=None,
                text=body,
                path=path,
                ordinal=i,
                token_count=len(window),
            )
        )
    return out
