from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_healthz(client) -> None:  # type: ignore[no-untyped-def]
    r = await client.get("/healthz")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert "version" in body
