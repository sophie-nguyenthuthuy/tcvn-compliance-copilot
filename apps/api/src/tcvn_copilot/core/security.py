"""Password hashing + JWT issue/verify.

Argon2id for password hashes (preferred over bcrypt for new systems).
Short-lived access tokens + longer-lived refresh tokens.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any, Literal

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from jose import JWTError, jwt

from tcvn_copilot.config import get_settings

_hasher = PasswordHasher()
_JWT_ALGORITHM = "HS256"

TokenType = Literal["access", "refresh"]


class TokenError(Exception):
    """Raised when a JWT is invalid, expired, or has the wrong type."""


def hash_password(plain: str) -> str:
    return _hasher.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return _hasher.verify(hashed, plain)
    except VerifyMismatchError:
        return False


def needs_rehash(hashed: str) -> bool:
    return _hasher.check_needs_rehash(hashed)


def create_token(
    subject: str,
    token_type: TokenType,
    *,
    extra_claims: dict[str, Any] | None = None,
) -> str:
    settings = get_settings()
    now = datetime.now(tz=UTC)
    ttl = (
        timedelta(minutes=settings.api_access_token_ttl_minutes)
        if token_type == "access"
        else timedelta(days=settings.api_refresh_token_ttl_days)
    )
    claims: dict[str, Any] = {
        "sub": subject,
        "type": token_type,
        "iat": int(now.timestamp()),
        "exp": int((now + ttl).timestamp()),
    }
    if extra_claims:
        claims.update(extra_claims)
    return jwt.encode(
        claims,
        settings.api_secret_key.get_secret_value(),
        algorithm=_JWT_ALGORITHM,
    )


def decode_token(token: str, expected_type: TokenType) -> dict[str, Any]:
    settings = get_settings()
    try:
        payload = jwt.decode(
            token,
            settings.api_secret_key.get_secret_value(),
            algorithms=[_JWT_ALGORITHM],
        )
    except JWTError as exc:
        raise TokenError(f"invalid token: {exc}") from exc

    if payload.get("type") != expected_type:
        raise TokenError(f"expected {expected_type} token, got {payload.get('type')}")
    return payload
