# tcvn-copilot — API service

FastAPI service + Celery workers for the compliance copilot.

## Layout

```
src/tcvn_copilot/
├── api/             HTTP layer (routes, middleware, deps)
├── core/            Cross-cutting (logging, telemetry, security, errors)
├── db/              SQLAlchemy models + session + Alembic
├── domain/          Business logic (compliance engine, rules)
├── rag/             RAG pipeline (chunker, embedder, retriever, LLM, prompts, extractors)
├── schemas/         Pydantic DTOs (request/response)
├── services/        Storage, report rendering, etc. (stateful side-effects)
├── workers/         Celery app + tasks
├── cli.py           CLI entrypoint (`tcvn-copilot`)
├── config.py        pydantic-settings — the only place that reads env vars
└── main.py          FastAPI app factory + lifespan
```

Boundary rules:

- `api/` may call into `domain/`, `services/`, `schemas/`, `db/`. Never the
  other way around.
- `domain/` is pure-ish — no HTTP, no Celery imports. Talks to `rag/` and `db/`.
- `rag/` is independent of `db/` for retrieval; it reaches into `db/` only via
  injected sessions, never via globals.

## Running locally without Docker

```bash
uv sync --all-extras
uv run alembic upgrade head
uv run uvicorn tcvn_copilot.main:app --reload
```

For workers:
```bash
uv run celery -A tcvn_copilot.workers.celery_app worker --loglevel=info
```

## Tests

- `tests/unit/` — pure Python, no I/O. Always run in CI.
- `tests/integration/` — needs postgres + redis. Gated by `-m integration`.
- `tests/fixtures/` — sample drawings & extraction outputs for integration tests.
