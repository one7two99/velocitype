from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.session import WeakKeyInfo

_MAX_PROMPT = 8000


class CoachAnalysis(BaseModel):
    layout_id: str
    model: str
    generated_at: datetime
    analysis: str


class CoachDrill(BaseModel):
    layout_id: str
    model: str
    generated_at: datetime
    lesson: str
    word_count: int
    weak_keys: list[WeakKeyInfo]
    source: str  # "ollama" | "fallback"


class CoachStatus(BaseModel):
    reachable: bool
    model: str
    model_ready: bool


class PromptSet(BaseModel):
    analysis_system: str
    analysis_user: str
    drill_system: str
    drill_user: str


class PromptCustom(BaseModel):
    analysis_system: str | None = None
    analysis_user: str | None = None
    drill_system: str | None = None
    drill_user: str | None = None


class CoachPrompts(BaseModel):
    """Defaults plus the user's overrides (null = using the default)."""
    defaults: PromptSet
    custom: PromptCustom


class CoachPromptsUpdate(BaseModel):
    # Empty string / null clears the override (reverts to default).
    analysis_system: str | None = Field(default=None, max_length=_MAX_PROMPT)
    analysis_user: str | None = Field(default=None, max_length=_MAX_PROMPT)
    drill_system: str | None = Field(default=None, max_length=_MAX_PROMPT)
    drill_user: str | None = Field(default=None, max_length=_MAX_PROMPT)
