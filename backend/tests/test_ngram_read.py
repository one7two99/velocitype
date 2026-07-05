"""Read-side tests: build_ngram_metrics + build_trigram_rollup (design §6).

Ingest goes through the real /keystrokes endpoint; the read functions are then
called against the same DB via SessionLocal."""
from __future__ import annotations

import uuid

from app.engine.layouts import DEFAULT_LAYOUT_ID


async def _register_and_uid(client, user):
    await client.post("/api/auth/register", json=user)
    return uuid.UUID((await client.get("/api/auth/me")).json()["id"])


async def _start(client):
    return (
        await client.post(
            "/api/sessions/start",
            json={"layout_id": DEFAULT_LAYOUT_ID, "mode": "adaptive", "duration_s": 30},
        )
    ).json()["session_id"]


def _payload(items):
    return {"keystrokes": [
        {"ts_offset_ms": ts, "expected_char": ch, "actual_char": ch,
         "correct": True, "hold_ms": None}
        for (ts, ch) in items
    ]}


async def _ngram_metrics(user_id):
    from app.db.session import SessionLocal
    from app.services.ngram_stats import build_ngram_metrics
    async with SessionLocal() as db:
        return await build_ngram_metrics(db, user_id, DEFAULT_LAYOUT_ID)


async def _trigram_rollup(user_id):
    from app.db.session import SessionLocal
    from app.services.ngram_stats import build_trigram_rollup
    async with SessionLocal() as db:
        return await build_trigram_rollup(db, user_id, DEFAULT_LAYOUT_ID)


async def test_build_ngram_metrics(client, unique_user):
    uid = await _register_and_uid(client, unique_user)
    sid = await _start(client)
    # s,c,s,c with one erroring pair (matches the ingest-test shape for "sc").
    ks = _payload([(0, "s"), (200, "c"), (400, "s"), (600, "c")])
    await client.post(f"/api/sessions/{sid}/keystrokes", json=ks)

    metrics = await _ngram_metrics(uid)
    by = {m.ngram: m for m in metrics}
    assert "sc" in by and "cs" in by
    sc = by["sc"]
    assert sc.n == 2
    assert sc.attempts == 2 and sc.errors == 0
    assert sc.latency_n == 2 and sc.avg_latency_ms == 200.0
    assert sc.sessions_since_seen == 0  # seen in the most recent session


async def test_build_trigram_rollup_classes(client, unique_user):
    uid = await _register_and_uid(client, unique_user)
    sid = await _start(client)
    # Each intended trigram is isolated by a space so exactly one triple forms:
    #   a s t = ROLL3 ; a t s = REDIRECT ; s c a = SFB_CHAIN ; a e r = ALT
    ks = _payload([
        (0, "a"), (200, "s"), (400, "t"), (600, " "),
        (800, "a"), (1000, "t"), (1200, "s"), (1400, " "),
        (1600, "s"), (1800, "c"), (2000, "a"), (2200, " "),
        (2400, "a"), (2600, "e"), (2800, "r"),
    ])
    await client.post(f"/api/sessions/{sid}/keystrokes", json=ks)

    roll = await _trigram_rollup(uid)
    assert roll["sessions_scanned"] == 1
    assert roll["total"] == 4
    bc = roll["by_class"]
    assert bc["ROLL3"]["count"] == 1
    assert bc["REDIRECT"]["count"] == 1
    assert bc["SFB_CHAIN"]["count"] == 1
    assert bc["ALT"]["count"] == 1
    assert bc["OTHER"]["count"] == 0
    assert bc["REDIRECT"]["pct"] == 25.0
    assert bc["ROLL3"]["avg_latency_ms"] == 400.0  # two clean 200ms IKIs
    assert roll["worst_redirect"] == "ats"
    assert roll["worst_sfb_chain"] == "sca"


async def test_trigram_rollup_empty_for_new_user(client, unique_user):
    uid = await _register_and_uid(client, unique_user)
    roll = await _trigram_rollup(uid)
    assert roll["total"] == 0
    assert roll["worst_redirect"] is None
    assert roll["by_class"]["REDIRECT"]["count"] == 0
