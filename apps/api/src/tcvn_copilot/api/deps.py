"""FastAPI dependency providers.

Centralised so route handlers can compose them via `Annotated[T, Depends(...)]`.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Annotated

import redis.asyncio as aioredis
from fastapi import Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession

from tcvn_copilot.config import Settings, get_settings
from tcvn_copilot.core.errors import AuthenticationError
from tcvn_copilot.core.security import decode_token
from tcvn_copilot.db.session import async_session_factory


async def get_db() -> AsyncIterator[AsyncSession]:
    """Yield an `AsyncSession`; commit on success, rollback on error."""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


_redis_pool: aioredis.Redis | None = None


async def get_redis() -> aioredis.Redis:
    global _redis_pool  # noqa: PLW0603
    if _redis_pool is None:
        settings = get_settings()
        _redis_pool = aioredis.from_url(
            str(settings.redis_url),
            encoding="utf-8",
            decode_responses=True,
        )
    return _redis_pool


SettingsDep = Annotated[Settings, Depends(get_settings)]
DbDep = Annotated[AsyncSession, Depends(get_db)]
RedisDep = Annotated[aioredis.Redis, Depends(get_redis)]


async def get_current_user_id(
    authorization: Annotated[str | None, Header()] = None,
) -> str:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise AuthenticationError("missing bearer token")
    token = authorization.split(" ", 1)[1].strip()
    try:
        payload = decode_token(token, expected_type="access")
    except Exception as exc:
        raise AuthenticationError(str(exc)) from exc
    return str(payload["sub"])


CurrentUserId = Annotated[str, Depends(get_current_user_id)]
