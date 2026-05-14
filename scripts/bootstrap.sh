#!/usr/bin/env bash
# Idempotent first-run bootstrap: brings up infra, runs migrations, validates corpus.
set -euo pipefail

cd "$(dirname "$0")/.."

if [[ ! -f .env ]]; then
  echo "→ creating .env from .env.example"
  cp .env.example .env
  echo "⚠️  Edit .env and set ANTHROPIC_API_KEY before continuing."
  exit 1
fi

echo "→ building images"
docker compose build

echo "→ starting infra (postgres, redis, minio)"
docker compose up -d postgres redis minio
docker compose up minio-bootstrap

echo "→ running database migrations"
docker compose run --rm api alembic upgrade head

echo "→ validating standards corpus manifests"
docker compose run --rm api python -m tcvn_copilot.rag.ingest --validate-only || \
  echo "⚠️  corpus validation reported issues — supply raw standard files (see packages/standards-corpus/README.md) and re-run \`make corpus-ingest\`"

echo "✅ bootstrap complete. \`make up\` to start the full stack."
