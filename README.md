# TCVN/QCVN Compliance Copilot

> RAG-based AI copilot that reviews AEC drawings against Vietnamese building
> standards (QCVN 06 — Fire Safety, QCVN 10 — Accessibility, TCVN 2737 — Loads,
> and others) and produces structured non-compliance reports.

[![CI](https://github.com/sophie-nguyenthuthuy/tcvn-compliance-copilot/actions/workflows/ci.yml/badge.svg)](.github/workflows/ci.yml)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](apps/api/pyproject.toml)
[![Next.js](https://img.shields.io/badge/next.js-14-black.svg)](apps/web/package.json)

---

## What it does

Vietnamese AEC firms spend hundreds of hours per project manually checking
designs against TCVN/QCVN standards. This copilot automates the first pass:

1. **Ingest** — accepts PDF drawings, IFC/BIM files, and design documents.
2. **Extract** — pulls geometry, room schedules, egress paths, fixture lists,
   and structural data using OCR + parsers + vision-LLM.
3. **Retrieve** — runs a RAG pipeline over a curated corpus of TCVN/QCVN
   clauses (chunked by article, with citations preserved).
4. **Reason** — for each extracted element, identifies applicable clauses and
   evaluates compliance via deterministic rules + LLM-judged ambiguous cases.
5. **Report** — emits a structured non-compliance report (PDF + JSON) with
   clause citations, severity, and remediation suggestions.

### Standards currently in scope

| Code         | Title                                                        | Status    |
| ------------ | ------------------------------------------------------------ | --------- |
| QCVN 06:2022 | Quy chuẩn kỹ thuật quốc gia về An toàn cháy cho nhà & công trình | Active    |
| QCVN 10:2014 | Xây dựng công trình đảm bảo người khuyết tật tiếp cận sử dụng | Active    |
| TCVN 2737:2023 | Tải trọng và tác động — Tiêu chuẩn thiết kế                | Active    |
| QCVN 04:2021 | Nhà chung cư                                                 | Planned   |
| TCVN 5574:2018 | Thiết kế kết cấu bê tông & bê tông cốt thép                | Planned   |

See [docs/standards.md](docs/standards.md) for the full corpus manifest and
ingestion notes.

---

## Architecture

```
┌──────────────┐    ┌───────────────┐    ┌──────────────────┐
│  Next.js UI  │───▶│  FastAPI API  │───▶│  Celery workers  │
└──────────────┘    └───────┬───────┘    └────────┬─────────┘
                            │                     │
                  ┌─────────┼─────────┐           │
                  ▼         ▼         ▼           ▼
              Postgres   Redis    Object      Anthropic
              + pgvector queue   storage      Claude API
```

- **API** — FastAPI, async, OpenTelemetry-instrumented.
- **Workers** — Celery for long-running drawing parsing and RAG inference.
- **Vector store** — `pgvector` (single-DB simplicity; swap for Qdrant if scale demands).
- **LLM** — Anthropic Claude (`claude-opus-4-7` for reasoning, `claude-haiku-4-5` for extraction).
- **OCR** — Tesseract with `vie` traineddata; PaddleOCR fallback for complex tables.
- **CAD/BIM** — `ifcopenshell` for IFC; `ezdxf` for DXF; PyMuPDF for PDF drawings.

Full architecture in [docs/architecture.md](docs/architecture.md).

---

## Quick start

### Prerequisites

- Docker 24+ and Docker Compose v2
- Python 3.11+ (for local dev outside containers)
- Node.js 20+ (for the web app)
- An Anthropic API key

### Bring up the stack

```bash
cp .env.example .env
# edit .env and set ANTHROPIC_API_KEY

make bootstrap   # one-shot: build images, run migrations, seed corpus
make up          # start the full stack
make logs        # tail logs
```

The API will be at `http://localhost:8000` (docs: `/docs`) and the web app at
`http://localhost:3000`.

### Local development without Docker

```bash
# API
cd apps/api
uv sync --all-extras
uv run alembic upgrade head
uv run uvicorn tcvn_copilot.main:app --reload

# Web
cd apps/web
pnpm install
pnpm dev
```

### Run the test suite

```bash
make test          # unit + integration
make test-e2e      # end-to-end (requires running stack)
make lint          # ruff + mypy + eslint + tsc
```

---

## Project layout

```
.
├── apps/
│   ├── api/                  FastAPI service + RAG pipeline + workers
│   └── web/                  Next.js 14 app (App Router)
├── packages/
│   └── standards-corpus/     TCVN/QCVN source documents + chunking manifests
├── infra/
│   ├── docker/               Production Dockerfiles
│   ├── k8s/                  Kustomize base + overlays
│   └── terraform/            Cloud infra (placeholder)
├── docs/
│   ├── architecture.md       System design
│   ├── standards.md          Corpus curation & versioning
│   ├── api.md                API reference
│   └── adr/                  Architecture decision records
├── scripts/                  Operational scripts (seed, benchmark, export)
└── tests/e2e/                End-to-end Playwright suite
```

---

## Operating the standards corpus

The compliance copilot is only as good as its corpus. We treat the standards
library as a first-class artifact, versioned and re-ingestible:

```bash
# Re-ingest the entire corpus into pgvector
make corpus-ingest

# Re-ingest a single standard
uv run python -m tcvn_copilot.rag.ingest --standard QCVN_06_2022

# Validate manifest integrity (hashes, clause IDs, etc.)
uv run python -m tcvn_copilot.rag.ingest --validate-only
```

See [packages/standards-corpus/README.md](packages/standards-corpus/README.md)
for the corpus contribution guide.

---

## Security & compliance

- **No standards documents in this repo.** TCVN/QCVN texts are copyrighted by
  the Ministry of Construction. The manifest lists clause IDs, hashes, and
  ingestion metadata, but the original PDFs must be supplied by the operator.
- **PII** — drawings often contain client info; uploads are encrypted at rest
  and auto-purged per the retention policy in `apps/api/src/tcvn_copilot/config.py`.
- **Secrets** — never commit `.env`. The repo ships a `gitleaks` pre-commit hook
  and a CI secret-scan job.
- **Dependency scanning** — Dependabot, `pip-audit`, and `npm audit` run weekly.

Security disclosures: see [SECURITY.md](SECURITY.md).

---

## Contributing

Contributions welcome — especially from civil/structural engineers who can
help curate and validate standard interpretations. Start with
[CONTRIBUTING.md](CONTRIBUTING.md).

## License

Apache 2.0 — see [LICENSE](LICENSE).
