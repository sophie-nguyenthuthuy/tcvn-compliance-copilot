"""Shared pytest fixtures.

We split unit (no I/O) from integration (postgres + redis). Integration tests
are gated by `pytest -m integration` and `INTEGRATION_DB_URL` in the env.
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator

import pytest
import pytest_asyncio


@pytest.fixture(scope="session", autouse=True)
def _env_defaults() -> None:
    """Populate env vars unit tests need before settings are imported."""
    os.environ.setdefault("ENVIRONMENT", "test")
    os.environ.setdefault(
        "DATABASE_URL", "postgresql+asyncpg://tcvn:tcvn@localhost:5432/tcvn_test"
    )
    os.environ.setdefault("REDIS_URL", "redis://localhost:6379/15")
    os.environ.setdefault("CELERY_BROKER_URL", "redis://localhost:6379/15")
    os.environ.setdefault("CELERY_RESULT_BACKEND", "redis://localhost:6379/15")
    os.environ.setdefault("S3_ACCESS_KEY", "test")
    os.environ.setdefault("S3_SECRET_KEY", "test")
    os.environ.setdefault("ANTHROPIC_API_KEY", "sk-ant-test")
    os.environ.setdefault("API_SECRET_KEY", "test-secret-key-with-enough-entropy")


@pytest_asyncio.fixture
async def client() -> AsyncIterator["AsyncClient"]:  # noqa: F821 — forward ref
    """ASGI test client against the FastAPI app."""
    from httpx import ASGITransport, AsyncClient

    from tcvn_copilot.main import create_app

    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
