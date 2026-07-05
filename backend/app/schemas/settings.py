from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class UserSettingsBody(BaseModel):
    theme: Literal["dark", "light", "system"]
    layout_id: str = Field(min_length=1, max_length=64)
    goal: Literal["time", "words"]
    duration_s: int = Field(ge=5, le=600)
    word_count: int = Field(ge=5, le=500)
    target_wpm: int = Field(ge=10, le=300)
    # Progressive key unlocking (keybr-style).
    progressive_unlock: bool = True
    unlock_threshold_pct: int = Field(default=90, ge=50, le=100)
    unlock_window_sessions: int = Field(default=3, ge=1, le=10)


class UserSettingsResponse(UserSettingsBody):
    # False when the user has never saved settings (values are the defaults).
    saved: bool
