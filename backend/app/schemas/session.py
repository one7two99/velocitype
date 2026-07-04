from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.keystroke import KeystrokeIn

SessionMode = Literal["adaptive", "fixed_text", "custom"]


class SessionStartRequest(BaseModel):
    layout_id: str = Field(min_length=1, max_length=64)
    mode: SessionMode = "adaptive"
    duration_s: int | None = Field(default=None, ge=1, le=3600)
    word_count: int | None = Field(default=None, ge=1, le=1000)
    custom_text: str | None = Field(default=None, max_length=20_000)
    target_wpm: int | None = Field(default=None, ge=10, le=300)

    @model_validator(mode="after")
    def _custom_requires_text(self) -> "SessionStartRequest":
        if self.mode == "custom" and not self.custom_text:
            raise ValueError("custom mode requires custom_text")
        return self


class WeakKeyInfo(BaseModel):
    char: str
    error_rate: float
    avg_latency_ms: float | None = None


class SessionStartResponse(BaseModel):
    session_id: uuid.UUID
    layout_id: str
    mode: SessionMode
    lesson: str
    weak_keys: list[WeakKeyInfo] = Field(default_factory=list)


class SessionCompleteRequest(BaseModel):
    wpm_raw: float = Field(ge=0, le=500)
    wpm_net: float = Field(ge=0, le=500)
    accuracy: float = Field(ge=0.0, le=1.0)
    consistency: float = Field(ge=0.0, le=1.0)
    duration_s: int | None = Field(default=None, ge=0, le=3600)
    target_wpm: int | None = Field(default=None, ge=10, le=300)
    # Optional inline keystroke batch; if omitted, post via /keystrokes first.
    keystrokes: list[KeystrokeIn] | None = Field(default=None, max_length=100_000)


class SessionMetrics(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    wpm_raw: float | None
    wpm_net: float | None
    accuracy: float | None
    consistency: float | None


class SessionCompleteResponse(BaseModel):
    session_id: uuid.UUID
    metrics: SessionMetrics
    weak_keys: list[WeakKeyInfo] = Field(default_factory=list)


class SessionSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    layout_id: str
    mode: str
    duration_s: int | None
    word_count: int | None
    started_at: datetime
    completed_at: datetime | None
    wpm_raw: float | None
    wpm_net: float | None
    accuracy: float | None
    consistency: float | None


class SessionDetail(SessionSummary):
    keystroke_count: int = 0


class SessionHistory(BaseModel):
    items: list[SessionSummary]
    page: int
    page_size: int
    total: int
