from __future__ import annotations

from pydantic import BaseModel, Field


class KeystrokeIn(BaseModel):
    ts_offset_ms: int = Field(ge=0, description="ms since session start")
    expected_char: str = Field(min_length=1, max_length=8)
    actual_char: str = Field(min_length=0, max_length=8)
    correct: bool
    hold_ms: int | None = Field(default=None, ge=0)


class KeystrokeBatch(BaseModel):
    keystrokes: list[KeystrokeIn] = Field(min_length=1, max_length=100_000)


class KeystrokeBatchResponse(BaseModel):
    saved: int
    keys_updated: int
