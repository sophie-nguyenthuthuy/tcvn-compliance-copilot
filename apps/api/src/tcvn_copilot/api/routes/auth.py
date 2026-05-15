"""Authentication endpoints — register, login, refresh."""

from __future__ import annotations

from fastapi import APIRouter, status
from sqlalchemy import select

from tcvn_copilot.api.deps import DbDep
from tcvn_copilot.core.errors import AuthenticationError, ConflictError
from tcvn_copilot.core.security import (
    TokenError,
    create_token,
    decode_token,
    hash_password,
    verify_password,
)
from tcvn_copilot.db.models.user import User
from tcvn_copilot.schemas.auth import LoginRequest, RefreshRequest, RegisterRequest, TokenPair

router = APIRouter()


@router.post("/register", response_model=TokenPair, status_code=status.HTTP_201_CREATED)
async def register(payload: RegisterRequest, db: DbDep) -> TokenPair:
    existing = await db.scalar(select(User).where(User.email == payload.email))
    if existing:
        raise ConflictError("email already registered")

    user = User(
        email=payload.email,
        full_name=payload.full_name,
        password_hash=hash_password(payload.password.get_secret_value()),
        organization=payload.organization,
    )
    db.add(user)
    await db.flush()

    return TokenPair(
        access_token=create_token(str(user.id), "access"),
        refresh_token=create_token(str(user.id), "refresh"),
    )


@router.post("/login", response_model=TokenPair)
async def login(payload: LoginRequest, db: DbDep) -> TokenPair:
    user = await db.scalar(select(User).where(User.email == payload.email))
    if user is None or not verify_password(payload.password.get_secret_value(), user.password_hash):
        raise AuthenticationError("invalid email or password")
    if not user.is_active:
        raise AuthenticationError("account disabled")

    return TokenPair(
        access_token=create_token(str(user.id), "access"),
        refresh_token=create_token(str(user.id), "refresh"),
    )


@router.post("/refresh", response_model=TokenPair)
async def refresh(payload: RefreshRequest) -> TokenPair:
    try:
        claims = decode_token(payload.refresh_token, expected_type="refresh")
    except TokenError as exc:
        raise AuthenticationError(str(exc)) from exc

    sub = str(claims["sub"])
    return TokenPair(
        access_token=create_token(sub, "access"),
        refresh_token=create_token(sub, "refresh"),
    )
