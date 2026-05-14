from __future__ import annotations

import pytest

from tcvn_copilot.core.security import (
    TokenError,
    create_token,
    decode_token,
    hash_password,
    verify_password,
)


class TestPasswords:
    def test_hash_and_verify_round_trip(self) -> None:
        h = hash_password("correct horse battery staple")
        assert verify_password("correct horse battery staple", h) is True
        assert verify_password("wrong-password", h) is False

    def test_hash_is_random(self) -> None:
        assert hash_password("p@ssword") != hash_password("p@ssword")


class TestJwt:
    def test_access_token_round_trip(self) -> None:
        tok = create_token("user-1", "access")
        claims = decode_token(tok, expected_type="access")
        assert claims["sub"] == "user-1"
        assert claims["type"] == "access"

    def test_rejects_wrong_token_type(self) -> None:
        access = create_token("user-1", "access")
        with pytest.raises(TokenError):
            decode_token(access, expected_type="refresh")

    def test_garbage_token_rejected(self) -> None:
        with pytest.raises(TokenError):
            decode_token("not-a-token", expected_type="access")
