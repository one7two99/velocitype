"""N-gram ingest tests: pure bigram aggregation + DB persistence via the real
keystrokes endpoint (design §4). Uses a hand-built stream with a known SFB."""
from __future__ import annotations

import uuid

import pytest

from app.engine.layouts import FERRIS_SWEEP_COLEMAK_DH as COLEMAK
from app.engine.layouts import DEFAULT_LAYOUT_ID
from app.schemas.keystroke import KeystrokeIn
from app.services.ngram_stats import _bigram_aggregates


def _k(ts: int, ch: str, correct: bool = True, actual: str | None = None) -> KeystrokeIn:
    return KeystrokeIn(
        ts_offset_ms=ts,
        expected_char=ch,
        actual_char=actual if actual is not None else ch,
        correct=correct,
        hold_ms=None,
    )


# ── Pure aggregator (no DB) ──────────────────────────────────────────────────
def test_aggregate_sfb_boundary_and_error():
    # s=LM, c=LM on Colemak → "sc" is a same-finger bigram. A single space breaks
    # the chain; the last "sc" pair is an error (no IKI contributed).
    stream = [
        _k(0, "s"), _k(200, "c"),      # sc  (iki 200)
        _k(400, "s"),                  # cs  (iki 200)
        _k(600, "c"),                  # sc  (iki 200)
        _k(800, " "),                  # boundary → chain reset
        _k(1000, "s"),                 # prev reset → no bigram
        _k(1200, "c", correct=False, actual="x"),  # sc attempt, error, no iki
    ]
    agg = _bigram_aggregates(stream, COLEMAK)
    assert set(agg) == {"sc", "cs"}          # nothing spans the space boundary
    assert agg["sc"]["attempts"] == 3
    assert agg["sc"]["errors"] == 1
    assert agg["sc"]["ikis"] == [200.0, 200.0]  # correct pairs only
    assert agg["cs"]["attempts"] == 1
    assert agg["cs"]["ikis"] == [200.0]


def test_aggregate_iki_needs_both_correct():
    # cur incorrect → counted as attempt+error, but no IKI sample.
    agg = _bigram_aggregates([_k(0, "s"), _k(200, "c", correct=False)], COLEMAK)
    assert agg["sc"]["errors"] == 1
    assert agg["sc"]["ikis"] == []


def test_aggregate_returns_raw_iki_uncapped():
    # The aggregator does not apply the pause cap — that's done at upsert time.
    agg = _bigram_aggregates([_k(0, "s"), _k(5000, "c")], COLEMAK)
    assert agg["sc"]["ikis"] == [5000.0]


def test_aggregate_repeat_forms_bigram():
    agg = _bigram_aggregates([_k(0, "s"), _k(200, "s")], COLEMAK)
    assert "ss" in agg and agg["ss"]["ikis"] == [200.0]


# ── DB integration through the real /keystrokes endpoint ─────────────────────
async def _persisted(client, user_id, layout_id):
    """Read this user's ngram_stats straight from the DB."""
    from sqlalchemy import select
    from app.db.session import SessionLocal
    from app.models.ngram_stat import NgramStat

    async with SessionLocal() as db:
        rows = (
            await db.execute(
                select(NgramStat).where(
                    NgramStat.user_id == user_id, NgramStat.layout_id == layout_id
                )
            )
        ).scalars().all()
    return {r.ngram: r for r in rows}


async def test_ingest_persists_bigrams_merge_and_hitch(client, unique_user):
    await client.post("/api/auth/register", json=unique_user)
    uid = uuid.UUID((await client.get("/api/auth/me")).json()["id"])
    sid = (
        await client.post(
            "/api/sessions/start",
            json={"layout_id": DEFAULT_LAYOUT_ID, "mode": "adaptive", "duration_s": 30},
        )
    ).json()["session_id"]

    def payload(items):
        return {"keystrokes": [
            {"ts_offset_ms": ts, "expected_char": ch, "actual_char": a,
             "correct": ok, "hold_ms": None}
            for (ts, ch, a, ok) in items
        ]}

    # Batch 1 — establishes sc mean = 200ms (3 attempts, 1 error, 2 IKIs).
    b1 = [(0, "s", "s", True), (200, "c", "c", True), (400, "s", "s", True),
          (600, "c", "c", True), (800, " ", " ", True), (1000, "s", "s", True),
          (1200, "c", "x", False)]
    r1 = await client.post(f"/api/sessions/{sid}/keystrokes", json=payload(b1))
    assert r1.status_code == 201

    stats = await _persisted(client, uid, DEFAULT_LAYOUT_ID)
    assert "sc" in stats and "cs" in stats
    sc = stats["sc"]
    assert sc.attempts == 3 and sc.errors == 1
    assert sc.latency_n == 2 and float(sc.avg_latency_ms) == 200.0
    assert sc.hitch_n == 0  # no prior mean, no pause

    # Batch 2 — a NEW session (keystrokes may be submitted once per session). An
    # sc transition at 700ms: 700 > 2.5 × 200 → a hitch, merging into the running
    # mean: (200·2 + 700)/3 = 366.67.
    sid2 = (
        await client.post(
            "/api/sessions/start",
            json={"layout_id": DEFAULT_LAYOUT_ID, "mode": "adaptive", "duration_s": 30},
        )
    ).json()["session_id"]
    b2 = [(0, "s", "s", True), (700, "c", "c", True)]
    r2 = await client.post(f"/api/sessions/{sid2}/keystrokes", json=payload(b2))
    assert r2.status_code == 201

    sc = (await _persisted(client, uid, DEFAULT_LAYOUT_ID))["sc"]
    assert sc.attempts == 4 and sc.errors == 1
    assert sc.latency_n == 3
    assert float(sc.avg_latency_ms) == pytest.approx(366.67)
    assert sc.hitch_n == 1
