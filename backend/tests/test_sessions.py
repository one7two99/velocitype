"""Session lifecycle tests (integration; skip if no test DB).

Covers start -> keystrokes -> complete, metric persistence, key_stats
aggregation feeding the adaptive lesson, and validation errors.
"""
from __future__ import annotations

import pytest

from app.engine.layouts import DEFAULT_LAYOUT_ID


async def _register(client, user):
    resp = await client.post("/api/auth/register", json=user)
    assert resp.status_code == 201


async def test_start_session_returns_lesson(client, unique_user):
    await _register(client, unique_user)
    resp = await client.post(
        "/api/sessions/start",
        json={"layout_id": DEFAULT_LAYOUT_ID, "mode": "adaptive"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["lesson"]
    assert body["layout_id"] == DEFAULT_LAYOUT_ID


async def test_start_rejects_unknown_layout(client, unique_user):
    await _register(client, unique_user)
    resp = await client.post(
        "/api/sessions/start",
        json={"layout_id": "does_not_exist", "mode": "adaptive"},
    )
    assert resp.status_code == 422


async def test_full_session_flow_persists_metrics(client, unique_user):
    await _register(client, unique_user)
    start = await client.post(
        "/api/sessions/start",
        json={"layout_id": DEFAULT_LAYOUT_ID, "mode": "adaptive", "duration_s": 60},
    )
    session_id = start.json()["session_id"]

    keystrokes = {
        "keystrokes": [
            {"ts_offset_ms": 0, "expected_char": "t", "actual_char": "t", "correct": True, "hold_ms": 90},
            {"ts_offset_ms": 200, "expected_char": "h", "actual_char": "g", "correct": False, "hold_ms": 120},
            {"ts_offset_ms": 480, "expected_char": "e", "actual_char": "e", "correct": True, "hold_ms": 80},
        ]
    }
    ks = await client.post(f"/api/sessions/{session_id}/keystrokes", json=keystrokes)
    assert ks.status_code == 201
    assert ks.json()["saved"] == 3

    # A second batch for the same session is rejected (idempotency).
    dup = await client.post(f"/api/sessions/{session_id}/keystrokes", json=keystrokes)
    assert dup.status_code == 409

    complete = await client.post(
        f"/api/sessions/{session_id}/complete",
        json={"wpm_raw": 62.5, "wpm_net": 58.0, "accuracy": 0.9667, "consistency": 0.94},
    )
    assert complete.status_code == 200
    metrics = complete.json()["metrics"]
    assert metrics["wpm_raw"] == pytest.approx(62.5)
    assert metrics["accuracy"] == pytest.approx(0.9667, abs=1e-4)

    # Completing twice is a conflict.
    again = await client.post(
        f"/api/sessions/{session_id}/complete",
        json={"wpm_raw": 1, "wpm_net": 1, "accuracy": 1.0, "consistency": 1.0},
    )
    assert again.status_code == 409

    # History reflects the session.
    hist = await client.get("/api/sessions?page=1&page_size=10")
    assert hist.status_code == 200
    assert hist.json()["total"] >= 1


async def test_coach_drill_mode_session(client, unique_user):
    await _register(client, unique_user)
    # coach_drill requires custom_text (like custom).
    missing = await client.post(
        "/api/sessions/start",
        json={"layout_id": DEFAULT_LAYOUT_ID, "mode": "coach_drill"},
    )
    assert missing.status_code == 422

    start = await client.post(
        "/api/sessions/start",
        json={
            "layout_id": DEFAULT_LAYOUT_ID,
            "mode": "coach_drill",
            "custom_text": "the and for with that",
        },
    )
    assert start.status_code == 201
    assert start.json()["mode"] == "coach_drill"
    assert start.json()["lesson"] == "the and for with that"

    # The mode is persisted and surfaced in history for the dashboard tag.
    sid = start.json()["session_id"]
    await client.post(
        f"/api/sessions/{sid}/complete",
        json={"wpm_raw": 40, "wpm_net": 38, "accuracy": 1.0, "consistency": 0.9},
    )
    hist = await client.get("/api/sessions?page=1&page_size=5")
    assert hist.json()["items"][0]["mode"] == "coach_drill"


async def test_complete_validation_error(client, unique_user):
    await _register(client, unique_user)
    start = await client.post(
        "/api/sessions/start",
        json={"layout_id": DEFAULT_LAYOUT_ID, "mode": "adaptive"},
    )
    session_id = start.json()["session_id"]
    # accuracy out of [0,1] -> 422
    resp = await client.post(
        f"/api/sessions/{session_id}/complete",
        json={"wpm_raw": 60, "wpm_net": 55, "accuracy": 1.5, "consistency": 0.9},
    )
    assert resp.status_code == 422


async def test_stats_and_keys_after_session(client, unique_user):
    await _register(client, unique_user)
    start = await client.post(
        "/api/sessions/start",
        json={"layout_id": DEFAULT_LAYOUT_ID, "mode": "adaptive", "duration_s": 30},
    )
    session_id = start.json()["session_id"]
    await client.post(
        f"/api/sessions/{session_id}/keystrokes",
        json={"keystrokes": [
            {"ts_offset_ms": 0, "expected_char": "q", "actual_char": "q", "correct": True},
            {"ts_offset_ms": 300, "expected_char": "q", "actual_char": "w", "correct": False},
        ]},
    )
    await client.post(
        f"/api/sessions/{session_id}/complete",
        json={"wpm_raw": 40, "wpm_net": 38, "accuracy": 0.5, "consistency": 0.8},
    )

    keys = await client.get(f"/api/stats/keys?layout_id={DEFAULT_LAYOUT_ID}")
    assert keys.status_code == 200
    chars = {c["character"]: c for c in keys.json()["keys"]}
    assert "q" in chars
    assert chars["q"]["attempts"] == 2
    assert chars["q"]["errors"] == 1


async def test_per_key_consistency_reported(client, unique_user):
    await _register(client, unique_user)
    start = await client.post(
        "/api/sessions/start",
        json={"layout_id": DEFAULT_LAYOUT_ID, "mode": "adaptive", "duration_s": 30},
    )
    session_id = start.json()["session_id"]
    # 7 't' keystrokes with steady ~100ms spacing → high consistency, enough samples.
    ks = [
        {"ts_offset_ms": i * 100, "expected_char": "t", "actual_char": "t", "correct": True}
        for i in range(7)
    ]
    await client.post(f"/api/sessions/{session_id}/keystrokes", json={"keystrokes": ks})
    await client.post(
        f"/api/sessions/{session_id}/complete",
        json={"wpm_raw": 60, "wpm_net": 58, "accuracy": 1.0, "consistency": 0.95},
    )

    keys = await client.get(f"/api/stats/keys?layout_id={DEFAULT_LAYOUT_ID}")
    t = {c["character"]: c for c in keys.json()["keys"]}["t"]
    assert t["consistency"] is not None
    assert 0.0 <= t["consistency"] <= 1.0
    assert t["consistency"] > 0.9  # steady spacing → very consistent


async def _session_row_count(username: str) -> int:
    """Total session rows in the DB for a user (incl. incomplete/untyped)."""
    from sqlalchemy import func, select

    from app.db.session import SessionLocal
    from app.models.session import TypingSession
    from app.models.user import User

    async with SessionLocal() as db:
        uid = await db.scalar(select(User.id).where(User.username == username))
        return int(
            await db.scalar(
                select(func.count(TypingSession.id)).where(
                    TypingSession.user_id == uid
                )
            )
            or 0
        )


async def test_history_excludes_incomplete_sessions(client, unique_user):
    await _register(client, unique_user)
    start = await client.post(
        "/api/sessions/start",
        json={"layout_id": DEFAULT_LAYOUT_ID, "mode": "adaptive"},
    )
    session_id = start.json()["session_id"]

    # An incomplete session (no metrics) must not surface in history.
    hist = await client.get("/api/sessions?page=1&page_size=10")
    assert hist.json()["total"] == 0
    assert hist.json()["items"] == []

    await client.post(
        f"/api/sessions/{session_id}/complete",
        json={"wpm_raw": 40, "wpm_net": 38, "accuracy": 0.95, "consistency": 0.9},
    )
    hist2 = await client.get("/api/sessions?page=1&page_size=10")
    assert hist2.json()["total"] == 1


async def test_start_sweeps_abandoned_untyped_sessions(client, unique_user):
    await _register(client, unique_user)
    j = {"layout_id": DEFAULT_LAYOUT_ID, "mode": "adaptive"}

    await client.post("/api/sessions/start", json=j)   # A (untyped)
    await client.post("/api/sessions/start", json=j)    # sweeps A, creates B
    assert await _session_row_count(unique_user["username"]) == 1

    # A session that received keystrokes is a genuine attempt → NOT swept.
    c = await client.post("/api/sessions/start", json=j)  # sweeps B, creates C
    cid = c.json()["session_id"]
    await client.post(
        f"/api/sessions/{cid}/keystrokes",
        json={"keystrokes": [
            {"ts_offset_ms": 0, "expected_char": "t", "actual_char": "t", "correct": True, "hold_ms": 90},
        ]},
    )
    await client.post("/api/sessions/start", json=j)      # creates D; C (typed) survives
    assert await _session_row_count(unique_user["username"]) == 2


async def test_session_series_reports_keys_speed_accuracy(client, unique_user):
    await _register(client, unique_user)
    start = await client.post(
        "/api/sessions/start",
        json={"layout_id": DEFAULT_LAYOUT_ID, "mode": "adaptive", "duration_s": 30},
    )
    session_id = start.json()["session_id"]
    # 6 keystrokes over 4 distinct keys ("t","h","e"," " excluded), steady 100ms.
    ks = [
        {"ts_offset_ms": 0, "expected_char": "t", "actual_char": "t", "correct": True},
        {"ts_offset_ms": 100, "expected_char": "h", "actual_char": "h", "correct": True},
        {"ts_offset_ms": 200, "expected_char": "e", "actual_char": "e", "correct": True},
        {"ts_offset_ms": 300, "expected_char": " ", "actual_char": " ", "correct": True},
        {"ts_offset_ms": 400, "expected_char": "t", "actual_char": "t", "correct": True},
        {"ts_offset_ms": 500, "expected_char": "o", "actual_char": "o", "correct": True},
    ]
    await client.post(f"/api/sessions/{session_id}/keystrokes", json={"keystrokes": ks})
    await client.post(
        f"/api/sessions/{session_id}/complete",
        json={"wpm_raw": 60, "wpm_net": 58, "accuracy": 0.97, "consistency": 0.95},
    )

    resp = await client.get(f"/api/stats/sessions?layout_id={DEFAULT_LAYOUT_ID}")
    assert resp.status_code == 200
    points = resp.json()["points"]
    assert len(points) == 1
    p = points[0]
    assert p["index"] == 1
    assert p["distinct_keys"] == 4          # {t,h,e,o}; space excluded, t repeats
    assert p["accuracy"] == pytest.approx(0.97, abs=1e-4)
    # Steady 100ms spacing → ~120 WPM (12000/100); avg and max both present.
    assert p["avg_wpm"] is not None and p["max_wpm"] is not None
    assert p["avg_wpm"] == pytest.approx(120.0, abs=1.0)
    assert p["max_wpm"] >= p["avg_wpm"]
