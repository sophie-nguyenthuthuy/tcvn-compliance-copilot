"""Async SQLAlchemy engine + session factory.

`init_engine()` is called from the FastAPI lifespan to create the connection
pool. Sessions are produced via `async_session_factory()` and are scoped to a
single request by the `get_db` dependency.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from tcvn_copilot.config import get_settings

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def init_engine() -> AsyncEngine:
    global _engine, _session_factory  # noqa: PLW0603
    if _engine is not None:
        return _engine
    settings = get_settings()
    _engine = create_async_engine(
        str(settings.database_url),
        echo=settings.database_echo,
        pool_size=settings.database_pool_size,
        max_overflow=settings.database_max_overflow,
        pool_pre_ping=True,
        future=True,
    )
    _session_factory = async_sessionmaker(
        _engine,
        expire_on_commit=False,
        autoflush=False,
    )
    return _engine


def get_engine() -> AsyncEngine:
    if _engine is None:
        init_engine()
    assert _engine is not None  # noqa: S101
    return _engine


def async_session_factory() -> AsyncSession:
    if _session_factory is None:
        init_engine()
    assert _session_factory is not None  # noqa: S101
    return _session_factory()


async def dispose_engine() -> None:
    global _engine, _session_factory  # noqa: PLW0603
    if _engine is not None:
        await _engine.dispose()
        _engine = None
        _session_factory = None
