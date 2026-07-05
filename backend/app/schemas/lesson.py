from __future__ import annotations

from pydantic import BaseModel, Field

from app.schemas.session import WeakKeyInfo


class NextLessonResponse(BaseModel):
    layout_id: str
    lesson: str
    weak_keys: list[WeakKeyInfo] = Field(default_factory=list)
    word_count: int


class LayoutInfo(BaseModel):
    id: str
    name: str
    hand_map: dict[str, str]
    finger_map: dict[str, str]
    thumb_keys: list[str]


class LayoutList(BaseModel):
    layouts: list[LayoutInfo]


class UnlockState(BaseModel):
    progressive: bool
    unlocked_count: int
    total: int
    unlock_order: list[str]
    unlocked: list[str]
    next_char: str | None = None
