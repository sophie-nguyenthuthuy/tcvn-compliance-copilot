from __future__ import annotations

from pydantic import BaseModel, ConfigDict, EmailStr, Field, SecretStr


class RegisterRequest(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=1, max_length=255)
    password: SecretStr = Field(min_length=12, max_length=128)
    organization: str | None = Field(default=None, max_length=255)


class LoginRequest(BaseModel):
    email: EmailStr
    password: SecretStr


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenPair(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
