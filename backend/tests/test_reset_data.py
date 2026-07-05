"""POST /api/auth/me/reset — hard-deletes all user data, keeps the account."""
from __future__ import annotations

import uuid

from sqlalchemy import func, select

from app.engine.layouts import DEFAULT_LAYOUT_ID


async def _register(client, user):
    assert (await client.post("/api/auth/register", json=user)).status_code == 201
    return uuid.UUID((await client.get("/api/auth/me")).json()["id"])


async def _seed(client):
    """Create sessions/keystrokes/key_stats/ngram_stats + AI config + a prompt."""
    sid = (
        await client.post(
            "/api/sessions/start",
            json={"layout_id": DEFAULT_LAYOUT_ID, "mode": "adaptive", "duration_s": 30},
        )
    ).json()["session_id"]
    ks, ts = [], 0
    for _ in range(6):
        ks += [
            {"ts_offset_ms": ts, "expected_char": "s", "actual_char": "s", "correct": True, "hold_ms": None},
            {"ts_offset_ms": ts + 200, "expected_char": "c", "actual_char": "c", "correct": True, "hold_ms": None},
            {"ts_offset_ms": ts + 400, "expected_char": " ", "actual_char": " ", "correct": True, "hold_ms": None},
        ]
        ts += 600
    await client.post(f"/api/sessions/{sid}/keystrokes", json={"keystrokes": ks})
    await client.put("/api/coach/config", json={"provider": "mistral", "mistral_api_key": "sk-secret"})
    await client.put("/api/coach/prompts", json={"analysis_system": "custom"})


async def _counts(uid):
    from app.db.session import SessionLocal
    from app.models.ai_config import UserAiConfig
    from app.models.key_stat import KeyStat
    from app.models.keystroke import Keystroke
    from app.models.ngram_stat import NgramStat
    from app.models.prompt import UserPrompt
    from app.models.session import TypingSession
    from app.models.user import User

    async with SessionLocal() as db:
        async def n(model, col):
            return int((await db.execute(select(func.count()).select_from(model).where(col == uid))).scalar_one())
        return {
            "users": int((await db.execute(select(func.count()).select_from(User).where(User.id == uid))).scalar_one()),
            "sessions": await n(TypingSession, TypingSession.user_id),
            "key_stats": await n(KeyStat, KeyStat.user_id),
            "ngram_stats": await n(NgramStat, NgramStat.user_id),
            "ai_config": await n(UserAiConfig, UserAiConfig.user_id),
            "prompts": await n(UserPrompt, UserPrompt.user_id),
            "keystrokes": int(
                (await db.execute(
                    select(func.count()).select_from(Keystroke).join(
                        TypingSession, Keystroke.session_id == TypingSession.id
                    ).where(TypingSession.user_id == uid)
                )).scalar_one()
            ),
        }


async def test_reset_hard_deletes_all_data_keeps_account(client, unique_user):
    uid = await _register(client, unique_user)
    await _seed(client)

    before = await _counts(uid)
    assert before["sessions"] >= 1 and before["keystrokes"] >= 1
    assert before["key_stats"] >= 1 and before["ngram_stats"] >= 1
    assert before["ai_config"] == 1 and before["prompts"] == 1

    resp = await client.post("/api/auth/me/reset", json={"password": unique_user["password"]})
    assert resp.status_code == 200

    after = await _counts(uid)
    assert after["users"] == 1  # account kept
    for key in ("sessions", "keystrokes", "key_stats", "ngram_stats", "ai_config", "prompts"):
        assert after[key] == 0, f"{key} not hard-deleted: {after[key]}"

    # Still authenticated, and the profile reads as fresh.
    assert (await client.get("/api/auth/me")).status_code == 200
    cfg = (await client.get("/api/coach/config")).json()
    assert cfg["provider"] == "ollama" and cfg["mistral_key_set"] is False
    assert (await client.get("/api/stats/keys")).json()["keys"] == []


async def test_reset_wrong_password_keeps_data(client, unique_user):
    uid = await _register(client, unique_user)
    await _seed(client)
    resp = await client.post("/api/auth/me/reset", json={"password": "wrong-password-xx"})
    assert resp.status_code == 401
    assert (await _counts(uid))["sessions"] >= 1  # nothing deleted


async def test_reset_requires_auth(client):
    assert (await client.post("/api/auth/me/reset", json={"password": "x"})).status_code == 401
