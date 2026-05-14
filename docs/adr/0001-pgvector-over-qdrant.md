# ADR 0001: Use pgvector instead of a dedicated vector database

- **Status**: Accepted
- **Date**: 2026-05-14
- **Deciders**: Founding team

## Context

We need a vector store for ~10k–50k standard-clause embeddings (BGE-M3, 1024-d).
Candidates: pgvector, Qdrant, Weaviate, Milvus.

## Decision

Use `pgvector` extension on the same Postgres instance that holds operational
data (users, projects, drawings, runs, findings).

## Consequences

**Positive**
- One fewer service to operate, monitor, back up, secure.
- Cross-joins between clause vectors and relational metadata (standard,
  tags, supersession) stay in SQL.
- HNSW in pgvector ≥ 0.5 gives sub-50ms p99 at our corpus size.
- Same backup story as the rest of the app.

**Negative**
- We pay Postgres I/O on every vector query. Not a problem at our scale; if
  the corpus grows past ~1M chunks, we'd reconsider.
- pgvector doesn't have payload filtering as ergonomic as Qdrant's. Our
  filters (`standard_codes`) are simple ANY-of-array — fine in SQL.

## Reconsider when

- Corpus exceeds 1M chunks, or
- We need >5k vector queries/sec, or
- We need hybrid sparse-dense fusion natively (Qdrant has BM25 + dense).

A `VectorStore` interface in `tcvn_copilot.rag.retriever` would make the swap
mechanical.
