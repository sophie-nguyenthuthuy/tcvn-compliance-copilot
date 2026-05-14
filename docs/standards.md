# Standards corpus

The compliance copilot is only as good as the standards it knows. We treat the
corpus as a versioned, auditable artifact — not as scraped text.

## What's bundled vs. what isn't

**Bundled** (this repo, MIT-compatible):
- Manifests (`packages/standards-corpus/manifests/*.yml`) listing each
  standard's code, title, version, dates, tags.
- Sample synthetic clauses (`samples/`) used for CI tests.
- Ingestion + chunking + embedding pipeline.

**Not bundled** (operator-supplied):
- The actual standard PDFs/DOCXs. TCVN/QCVN texts are copyrighted by the
  Ministry of Construction (Bộ Xây dựng); redistribution requires licensing.

## Lifecycle of a standard

```
            ┌──── Manifest YAML ────┐
            │   code, version, date │
            └──────────┬────────────┘
                       │
                       ▼
        ┌────────  raw PDF/DOCX  ────────┐
        │     (operator supplies)        │
        └──────────────┬─────────────────┘
                       ▼
            ┌──── Ingest pipeline ────┐
            │ chunk → embed → upsert  │
            └──────────┬──────────────┘
                       ▼
        ┌──── Postgres + pgvector ────┐
        │ standards, clauses, embed.  │
        └─────────────────────────────┘
                       ▼
                 Available to RAG
```

## Re-ingestion

The pipeline is idempotent on `source_hash`:

```bash
make corpus-ingest                              # everything
make corpus-validate                             # manifests + source paths only
uv run python -m tcvn_copilot.rag.ingest \
    --standard QCVN_06_2022 --force              # one standard, force re-embed
```

Re-running with unchanged source skips the embedding step (saves cost +
preserves clause UUIDs, which findings reference).

## Adding a new standard

1. Drop the raw file under `packages/standards-corpus/raw/<CODE>/`.
2. Create `manifests/<CODE>.yml`:
   ```yaml
   code: TCVN_5687_2024
   title_vi: "Thông gió, điều hoà không khí — Tiêu chuẩn thiết kế"
   issuer: "Bộ Khoa học và Công nghệ"
   version: "2024"
   issued_at: 2024-06-30
   effective_at: 2024-12-01
   source_file: "raw/TCVN_5687_2024/TCVN-5687-2024.pdf"
   tags: [hvac, ventilation]
   ```
3. Run `make corpus-validate` to lint.
4. Run `make corpus-ingest` to (re-)embed.
5. (Optional) add deterministic rules in `apps/api/src/tcvn_copilot/domain/compliance/rules.py`
   for the quantitative checks. Add unit tests in `apps/api/tests/unit/test_rules.py`.

## Chunking strategy

Standards are *structurally* chunkable: each numbered article is a coherent
unit. The chunker (`apps/api/src/tcvn_copilot/rag/chunker.py`) splits on
clause headers like `3.2.4` or `Điều 5.`, then size-splits any clause that
exceeds `RAG_CHUNK_SIZE_TOKENS` (default 512).

This matters because the LLM is asked to cite by `clause_number` — keeping
chunks aligned to clauses means citations match the document.

## Versioning & supersession

Each `Standard` row carries a `version` (year) and a nullable
`superseded_by_id`. When a new version is published:

1. Ingest the new manifest under a new `code` (e.g. `TCVN_2737_2023`).
2. Update the old standard row to point `superseded_by_id` at the new one.
3. Compliance runs default to the latest non-superseded standard for each
   family unless the user explicitly pins a version.
