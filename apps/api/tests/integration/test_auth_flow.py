"""End-to-end auth flow: register → login → use token on a protected route.

Requires postgres + redis. Skipped by default; enable with `pytest -m integration`.
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_register_then_login(client) -> None:  # type: ignore[no-untyped-def]
    r = await client.post(
        "/auth/register",
        json={
            "email": "integration-test@example.com",
            "full_name": "Integration Test",
            "password": "a-strong-pw-123!",
            "organization": "Acme AEC",
        },
    )
    # If already registered from a previous run, 409 is acceptable.
    assert r.status_code in (201, 409)

    r = await client.post(
        "/auth/login",
        json={"email": "integration-test@example.com", "password": "a-strong-pw-123!"},
    )
    assert r.status_code == 200
    body = r.json()
    assert "access_token" in body
    assert "refresh_token" in body

    # Use the token on /projects
    token = body["access_token"]
    r = await client.get("/projects", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert isinstance(r.json(), list)
