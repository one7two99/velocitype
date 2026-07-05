"""Integration tests for progressive unlocking through the real API."""
from __future__ import annotations

from app.engine.layouts import DEFAULT_LAYOUT_ID, INITIAL_UNLOCKED
from app.engine.layouts import FERRIS_SWEEP_COLEMAK_DH as COLEMAK

ORDER = COLEMAK.unlock_order
INITIAL_CHARS = set(ORDER[:INITIAL_UNLOCKED])  # e t a o i n


async def _register(client, user):
    assert (await client.post("/api/auth/register", json=user)).status_code == 201


async def _master_session(client):
    """One session typing the active keys fast + correct (qualifies for mastery)."""
    sid = (
        await client.post(
            "/api/sessions/start",
            json={"layout_id": DEFAULT_LAYOUT_ID, "mode": "adaptive", "duration_s": 30},
        )
    ).json()["session_id"]
    ks, ts = [], 0
    for _ in range(4):
        for ch in ORDER[:INITIAL_UNLOCKED]:
            ts += 100  # 100ms IKI → ~120 wpm, well above 90% of the 40 target
            ks.append({"ts_offset_ms": ts, "expected_char": ch, "actual_char": ch, "correct": True, "hold_ms": None})
    await client.post(f"/api/sessions/{sid}/keystrokes", json={"keystrokes": ks})
    return (
        await client.post(
            f"/api/sessions/{sid}/complete",
            json={"wpm_raw": 120, "wpm_net": 118, "accuracy": 1.0, "consistency": 0.95, "target_wpm": 40},
        )
    ).json()


async def test_new_user_starts_with_initial_set(client, unique_user):
    await _register(client, unique_user)
    st = (await client.get("/api/lessons/unlock")).json()
    assert st["progressive"] is True
    assert st["unlocked_count"] == INITIAL_UNLOCKED
    assert set(st["unlocked"]) == INITIAL_CHARS
    assert st["next_char"] == ORDER[INITIAL_UNLOCKED]  # 's'


async def test_next_lesson_only_uses_unlocked_letters(client, unique_user):
    await _register(client, unique_user)
    lesson = (await client.get("/api/lessons/next")).json()["lesson"]
    assert set(lesson.replace(" ", "")) <= INITIAL_CHARS


async def test_mastering_active_set_unlocks_next_key(client, unique_user):
    await _register(client, unique_user)
    # Default window N = 3: first two sessions don't unlock; the third does.
    r1 = await _master_session(client)
    assert r1["unlocked_char"] is None
    r2 = await _master_session(client)
    assert r2["unlocked_char"] is None
    r3 = await _master_session(client)
    assert r3["unlocked_char"] == ORDER[INITIAL_UNLOCKED]  # 's' revealed

    st = (await client.get("/api/lessons/unlock")).json()
    assert st["unlocked_count"] == INITIAL_UNLOCKED + 1
    assert ORDER[INITIAL_UNLOCKED] in st["unlocked"]


async def test_toggle_off_uses_full_keyboard(client, unique_user):
    await _register(client, unique_user)
    s = (await client.get("/api/settings")).json()
    keep = ("theme", "layout_id", "goal", "duration_s", "word_count", "target_wpm",
            "progressive_unlock", "unlock_threshold_pct", "unlock_window_sessions")
    body = {k: s[k] for k in keep}
    body["progressive_unlock"] = False
    await client.put("/api/settings", json=body)

    st = (await client.get("/api/lessons/unlock")).json()
    assert st["progressive"] is False
    assert st["unlocked_count"] == st["total"]
    # A lesson can now use letters beyond the initial set.
    lesson = (await client.get("/api/lessons/next")).json()["lesson"]
    assert not set(lesson.replace(" ", "")) <= INITIAL_CHARS


async def test_reset_progression(client, unique_user):
    await _register(client, unique_user)
    for _ in range(3):
        await _master_session(client)
    assert (await client.get("/api/lessons/unlock")).json()["unlocked_count"] > INITIAL_UNLOCKED
    reset = (await client.post("/api/lessons/unlock/reset")).json()
    assert reset["unlocked_count"] == INITIAL_UNLOCKED
