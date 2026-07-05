"""User settings router: per-user UI/training preferences synced across browsers."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.models.user_settings import UserSettings
from app.schemas.settings import UserSettingsBody, UserSettingsResponse

router = APIRouter(prefix="/api/settings", tags=["settings"])

# Defaults mirror the frontend store (settingsStore.ts).
_DEFAULTS = {
    "theme": "system",
    "layout_id": "ferris_sweep_colemak_dh",
    "goal": "time",
    "duration_s": 60,
    "word_count": 25,
    "target_wpm": 40,
}


def _row_to_response(row: UserSettings) -> UserSettingsResponse:
    return UserSettingsResponse(
        theme=row.theme,
        layout_id=row.layout_id,
        goal=row.goal,
        duration_s=row.duration_s,
        word_count=row.word_count,
        target_wpm=row.target_wpm,
        saved=True,
    )


@router.get("", response_model=UserSettingsResponse)
async def get_settings(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> UserSettingsResponse:
    row = (
        await db.execute(select(UserSettings).where(UserSettings.user_id == user.id))
    ).scalar_one_or_none()
    if row is None:
        return UserSettingsResponse(**_DEFAULTS, saved=False)
    return _row_to_response(row)


@router.put("", response_model=UserSettingsResponse)
async def put_settings(
    payload: UserSettingsBody,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> UserSettingsResponse:
    row = (
        await db.execute(select(UserSettings).where(UserSettings.user_id == user.id))
    ).scalar_one_or_none()
    if row is None:
        row = UserSettings(user_id=user.id)
        db.add(row)
    row.theme = payload.theme
    row.layout_id = payload.layout_id
    row.goal = payload.goal
    row.duration_s = payload.duration_s
    row.word_count = payload.word_count
    row.target_wpm = payload.target_wpm
    await db.commit()
    return _row_to_response(row)
