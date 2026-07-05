"""GET/PUT /api/settings — per-user settings synced across browsers."""
from __future__ import annotations


async def _register(client, user):
    assert (await client.post("/api/auth/register", json=user)).status_code == 201


_VALID = {
    "theme": "dark",
    "layout_id": "corne_colemak_dh",
    "goal": "words",
    "duration_s": 30,
    "word_count": 50,
    "target_wpm": 65,
}


async def test_get_defaults_unsaved(client, unique_user):
    await _register(client, unique_user)
    body = (await client.get("/api/settings")).json()
    assert body["saved"] is False
    assert body["theme"] == "system"
    assert body["layout_id"] == "ferris_sweep_colemak_dh"
    assert body["target_wpm"] == 40


async def test_put_then_get_roundtrip(client, unique_user):
    await _register(client, unique_user)
    saved = await client.put("/api/settings", json=_VALID)
    assert saved.status_code == 200
    assert saved.json()["saved"] is True

    got = (await client.get("/api/settings")).json()
    assert got["saved"] is True
    for k, v in _VALID.items():
        assert got[k] == v

    # Idempotent update.
    upd = await client.put("/api/settings", json={**_VALID, "theme": "light"})
    assert upd.json()["theme"] == "light"


async def test_put_validates(client, unique_user):
    await _register(client, unique_user)
    bad = await client.put("/api/settings", json={**_VALID, "theme": "neon"})
    assert bad.status_code == 422
    bad2 = await client.put("/api/settings", json={**_VALID, "target_wpm": 5000})
    assert bad2.status_code == 422


async def test_settings_survive_reset(client, unique_user):
    """Preferences are kept when the user wipes their data (they're not metrics)."""
    await _register(client, unique_user)
    await client.put("/api/settings", json=_VALID)
    resp = await client.post("/api/auth/me/reset", json={"password": unique_user["password"]})
    assert resp.status_code == 200
    got = (await client.get("/api/settings")).json()
    assert got["saved"] is True and got["theme"] == "dark"


async def test_settings_requires_auth(client):
    assert (await client.get("/api/settings")).status_code == 401
    assert (await client.put("/api/settings", json=_VALID)).status_code == 401
