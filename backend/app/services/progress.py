"""Progressive-unlock service: resolves each user's unlocked key set, updates it
when the active set is mastered, and exposes the settings the ingest/lesson code
needs. Async SQLAlchemy glue; the rules live in ``engine/unlock.py``."""
from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.engine import unlock
from app.engine.layouts import INITIAL_UNLOCKED, Layout, get_layout
from app.models.key_stat import KeyStat
from app.models.layout_progress import UserLayoutProgress
from app.models.user_settings import UserSettings

# Mirrors the settings defaults (used when the user has no settings row yet).
_SETTINGS_DEFAULTS = {
    "target_wpm": 40,
    "progressive_unlock": True,
    "unlock_threshold_pct": 90,
    "unlock_window_sessions": 3,
}


async def get_user_settings(db: AsyncSession, user_id: uuid.UUID) -> dict:
    """The unlock-relevant settings for a user (defaults if never saved)."""
    row = (
        await db.execute(select(UserSettings).where(UserSettings.user_id == user_id))
    ).scalar_one_or_none()
    if row is None:
        return dict(_SETTINGS_DEFAULTS)
    return {
        "target_wpm": row.target_wpm,
        "progressive_unlock": row.progressive_unlock,
        "unlock_threshold_pct": row.unlock_threshold_pct,
        "unlock_window_sessions": row.unlock_window_sessions,
    }


async def _progress_count(db: AsyncSession, user_id: uuid.UUID, layout_id: str) -> int:
    """Read-only unlocked_count (initial small set if the user has no row yet)."""
    row = (
        await db.execute(
            select(UserLayoutProgress).where(
                UserLayoutProgress.user_id == user_id,
                UserLayoutProgress.layout_id == layout_id,
            )
        )
    ).scalar_one_or_none()
    return row.unlocked_count if row else INITIAL_UNLOCKED


async def get_unlocked_chars(
    db: AsyncSession, user_id: uuid.UUID, layout: Layout, settings: dict
) -> list[str]:
    """Characters the user may practice. Progressive off → the whole layout."""
    if not settings.get("progressive_unlock", True):
        return layout.characters
    count = await _progress_count(db, user_id, layout.id)
    return unlock.unlocked_chars(layout.unlock_order, count)


async def unlock_state(db: AsyncSession, user_id: uuid.UUID, layout_id: str) -> dict:
    """Snapshot for the API/UI: order, count, unlocked chars, next locked char."""
    layout = get_layout(layout_id)
    settings = await get_user_settings(db, user_id)
    order = layout.unlock_order if layout else []
    if not settings["progressive_unlock"]:
        count = len(order)
    else:
        count = min(await _progress_count(db, user_id, layout_id), len(order))
    return {
        "progressive": settings["progressive_unlock"],
        "unlocked_count": count,
        "total": len(order),
        "unlock_order": order,
        "unlocked": order[:count],
        "next_char": order[count] if count < len(order) else None,
    }


async def reset_progression(db: AsyncSession, user_id: uuid.UUID, layout_id: str) -> None:
    """Restart the user's progression for a layout at the initial small set."""
    row = (
        await db.execute(
            select(UserLayoutProgress).where(
                UserLayoutProgress.user_id == user_id,
                UserLayoutProgress.layout_id == layout_id,
            )
        )
    ).scalar_one_or_none()
    if row is None:
        row = UserLayoutProgress(user_id=user_id, layout_id=layout_id)
        db.add(row)
    row.unlocked_count = INITIAL_UNLOCKED
    await db.commit()


async def advance_if_mastered(
    db: AsyncSession, user_id: uuid.UUID, layout_id: str, settings: dict
) -> str | None:
    """If the active key set is mastered, reveal the next key. Returns the newly
    unlocked character (or None). Does NOT commit — the caller does."""
    if not settings.get("progressive_unlock", True):
        return None
    layout = get_layout(layout_id)
    if layout is None:
        return None
    order = layout.unlock_order

    row = (
        await db.execute(
            select(UserLayoutProgress).where(
                UserLayoutProgress.user_id == user_id,
                UserLayoutProgress.layout_id == layout_id,
            )
        )
    ).scalar_one_or_none()
    count = row.unlocked_count if row else INITIAL_UNLOCKED
    if count >= len(order):
        return None

    streak_rows = (
        await db.execute(
            select(KeyStat.character, KeyStat.qualifying_streak).where(
                KeyStat.user_id == user_id, KeyStat.layout_id == layout_id
            )
        )
    ).all()
    streaks = {c: s for c, s in streak_rows}

    if not unlock.should_unlock_next(order, count, streaks, settings["unlock_window_sessions"]):
        return None

    newly = order[count]
    if row is None:
        row = UserLayoutProgress(user_id=user_id, layout_id=layout_id)
        db.add(row)
    row.unlocked_count = count + 1
    return newly
