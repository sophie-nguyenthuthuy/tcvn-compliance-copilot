"""Standards corpus ingestion.

CLI entry-point:

    python -m tcvn_copilot.rag.ingest --bootstrap
    python -m tcvn_copilot.rag.ingest --standard QCVN_06_2022
    python -m tcvn_copilot.rag.ingest --all
    python -m tcvn_copilot.rag.ingest --validate-only

Reads `packages/standards-corpus/manifests/*.yml`, locates the raw PDF/text
source for each standard (must be supplied by the operator), chunks it, embeds
the chunks, and writes `Standard` + `StandardClause` + `StandardClauseEmbedding`
rows. Operations are idempotent: re-running with unchanged source skips the
embedding step.
"""

from __future__ import annotations

import asyncio
import hashlib
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

import click
import yaml
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from tcvn_copilot.config import get_settings
from tcvn_copilot.core.logging import configure_logging, get_logger
from tcvn_copilot.db.models import Standard, StandardClause, StandardClauseEmbedding
from tcvn_copilot.db.session import async_session_factory, dispose_engine, init_engine
from tcvn_copilot.rag.chunker import Chunk, chunk_standard
from tcvn_copilot.rag.embedder import embed_texts

log = get_logger(__name__)


@dataclass(slots=True)
class ManifestEntry:
    code: str
    title_vi: str
    title_en: str | None
    issuer: str
    version: str
    issued_at: date | None
    effective_at: date | None
    source_file: Path  # path relative to corpus root
    description: str | None
    tags: list[str]


def _corpus_root() -> Path:
    return Path(get_settings().standards_corpus_path)


def _load_manifest(path: Path) -> ManifestEntry:
    data: dict[str, Any] = yaml.safe_load(path.read_text(encoding="utf-8"))
    return ManifestEntry(
        code=data["code"],
        title_vi=data["title_vi"],
        title_en=data.get("title_en"),
        issuer=data.get("issuer", "Bộ Xây dựng"),
        version=str(data["version"]),
        issued_at=_parse_date(data.get("issued_at")),
        effective_at=_parse_date(data.get("effective_at")),
        source_file=Path(data["source_file"]),
        description=data.get("description"),
        tags=list(data.get("tags", [])),
    )


def _parse_date(v: Any) -> date | None:
    if v is None:
        return None
    if isinstance(v, date):
        return v
    return date.fromisoformat(str(v))


def _hash_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 16), b""):
            h.update(block)
    return h.hexdigest()


def _load_source_text(corpus_root: Path, entry: ManifestEntry) -> str:
    src = corpus_root / entry.source_file
    if not src.exists():
        raise FileNotFoundError(
            f"corpus source {src} missing for {entry.code}. "
            "TCVN/QCVN documents are not bundled — see packages/standards-corpus/README.md"
        )
    suffix = src.suffix.lower()
    if suffix in {".txt", ".md"}:
        return src.read_text(encoding="utf-8")
    if suffix == ".pdf":
        # Lazy import — pdf parsing only required when ingesting PDFs.
        import fitz  # type: ignore[import-not-found]

        with fitz.open(src) as doc:
            return "\n\n".join(page.get_text("text") for page in doc)
    raise ValueError(f"unsupported source format: {suffix}")


async def _ingest_one(session: AsyncSession, entry: ManifestEntry, *, force: bool) -> None:
    corpus_root = _corpus_root()
    src_path = corpus_root / entry.source_file
    source_hash = _hash_file(src_path) if src_path.exists() else None

    standard = await session.scalar(select(Standard).where(Standard.code == entry.code))
    if standard is None:
        standard = Standard(
            code=entry.code,
            title_vi=entry.title_vi,
            title_en=entry.title_en,
            issuer=entry.issuer,
            version=entry.version,
            issued_at=entry.issued_at,
            effective_at=entry.effective_at,
            description=entry.description,
            source_hash=source_hash,
        )
        session.add(standard)
        await session.flush()
    elif not force and standard.source_hash == source_hash:
        log.info("corpus_unchanged", code=entry.code)
        return
    else:
        standard.title_vi = entry.title_vi
        standard.title_en = entry.title_en
        standard.version = entry.version
        standard.issued_at = entry.issued_at
        standard.effective_at = entry.effective_at
        standard.description = entry.description
        standard.source_hash = source_hash

    # Wipe & reinsert clauses; embeddings cascade.
    await session.execute(
        StandardClause.__table__.delete().where(StandardClause.standard_id == standard.id)
    )

    log.info("loading_source", code=entry.code, path=str(src_path))
    raw = _load_source_text(corpus_root, entry)
    chunks: list[Chunk] = chunk_standard(raw, path=entry.code)
    log.info("chunked_standard", code=entry.code, n_chunks=len(chunks))

    if not chunks:
        log.warning("no_chunks_emitted", code=entry.code)
        return

    vectors = embed_texts([c.text for c in chunks])
    settings = get_settings()
    for chunk, vec in zip(chunks, vectors, strict=True):
        clause = StandardClause(
            standard_id=standard.id,
            clause_number=chunk.clause_number,
            title_vi=chunk.title,
            text_vi=chunk.text,
            ordinal=chunk.ordinal,
            path=chunk.path,
        )
        session.add(clause)
        await session.flush()
        session.add(
            StandardClauseEmbedding(
                clause_id=clause.id,
                model=settings.embedding_model,
                dim=settings.embedding_dim,
                embedding=vec,
            )
        )
    log.info("ingested_standard", code=entry.code, clauses=len(chunks))


async def _validate_manifest(entry: ManifestEntry) -> list[str]:
    errs: list[str] = []
    src = _corpus_root() / entry.source_file
    if not src.exists():
        errs.append(f"source missing: {src}")
    if not entry.version:
        errs.append("version is required")
    return errs


async def run(*, codes: list[str] | None, all_: bool, validate_only: bool, force: bool) -> int:
    configure_logging()
    init_engine()

    manifests_dir = _corpus_root() / "manifests"
    if not manifests_dir.exists():
        log.error("manifests_dir_missing", path=str(manifests_dir))
        return 2

    entries = [_load_manifest(p) for p in sorted(manifests_dir.glob("*.yml"))]
    if codes:
        entries = [e for e in entries if e.code in set(codes)]
    if not entries:
        log.warning("no_matching_manifests")
        return 1

    if validate_only:
        exit_code = 0
        for e in entries:
            errs = await _validate_manifest(e)
            if errs:
                exit_code = 1
                for err in errs:
                    log.error("manifest_invalid", code=e.code, error=err)
            else:
                log.info("manifest_ok", code=e.code)
        return exit_code

    async with async_session_factory() as session:
        try:
            for entry in entries:
                await _ingest_one(session, entry, force=force or all_)
            await session.commit()
        except Exception:
            await session.rollback()
            raise

    await dispose_engine()
    return 0


@click.command()
@click.option("--standard", "codes", multiple=True, help="Standard code(s) to ingest")
@click.option("--all", "all_", is_flag=True, help="Ingest every standard in the manifest")
@click.option("--bootstrap", is_flag=True, help="First-run alias for --all")
@click.option("--validate-only", is_flag=True, help="Validate manifests; do not write")
@click.option("--force", is_flag=True, help="Re-ingest even if source hash is unchanged")
def main(
    codes: tuple[str, ...],
    all_: bool,
    bootstrap: bool,
    validate_only: bool,
    force: bool,
) -> None:
    rc = asyncio.run(
        run(
            codes=list(codes) or None,
            all_=all_ or bootstrap,
            validate_only=validate_only,
            force=force,
        )
    )
    sys.exit(rc)


if __name__ == "__main__":
    main()
