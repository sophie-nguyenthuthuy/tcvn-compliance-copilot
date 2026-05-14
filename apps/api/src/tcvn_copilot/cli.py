"""Top-level CLI entrypoint.

Subcommands wrap the most common ops:
  tcvn-copilot ingest      → standards corpus ingest
  tcvn-copilot run-api     → uvicorn dev server
  tcvn-copilot run-worker  → celery worker
"""

from __future__ import annotations

import sys

import click


@click.group()
def main() -> None:
    """TCVN/QCVN Compliance Copilot."""


@main.command()
@click.option("--standard", "codes", multiple=True)
@click.option("--all", "all_", is_flag=True)
@click.option("--validate-only", is_flag=True)
@click.option("--force", is_flag=True)
def ingest(codes: tuple[str, ...], all_: bool, validate_only: bool, force: bool) -> None:
    """Re-ingest the standards corpus."""
    import asyncio

    from tcvn_copilot.rag.ingest import run

    rc = asyncio.run(
        run(codes=list(codes) or None, all_=all_, validate_only=validate_only, force=force)
    )
    sys.exit(rc)


@main.command("run-api")
@click.option("--host", default="0.0.0.0")  # noqa: S104
@click.option("--port", default=8000, type=int)
@click.option("--reload/--no-reload", default=False)
def run_api(host: str, port: int, reload: bool) -> None:
    """Start the FastAPI app (uvicorn)."""
    import uvicorn

    uvicorn.run("tcvn_copilot.main:app", host=host, port=port, reload=reload)


@main.command("run-worker")
@click.option("--concurrency", default=2, type=int)
def run_worker(concurrency: int) -> None:
    """Start a Celery worker."""
    from tcvn_copilot.workers.celery_app import celery_app

    celery_app.worker_main(argv=["worker", "--loglevel=info", f"--concurrency={concurrency}"])


if __name__ == "__main__":
    main()
