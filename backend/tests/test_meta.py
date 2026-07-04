"""Version / health endpoint tests."""
from __future__ import annotations

from app.version import __version__


async def test_version_endpoint(client):
    resp = await client.get("/api/version")
    assert resp.status_code == 200
    assert resp.json() == {"version": __version__}


async def test_health_reports_version(client):
    resp = await client.get("/api/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["version"] == __version__
