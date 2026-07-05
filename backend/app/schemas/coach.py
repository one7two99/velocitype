from __future__ import annotations

from datetime import datetime
from typing import Literal

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
    provider: str
    reachable: bool
    model: str
    model_ready: bool


class AiConfig(BaseModel):
    """The user's AI provider config. The Mistral key is never returned; only
    whether one is stored."""
    provider: str
    ollama_model: str
    mistral_model: str
    mistral_key_set: bool
    ollama_default: str
    mistral_default: str


class AiConfigUpdate(BaseModel):
    provider: Literal["ollama", "mistral"] | None = None
    ollama_model: str | None = Field(default=None, max_length=128)
    mistral_model: str | None = Field(default=None, max_length=128)
    # null = leave unchanged, "" = clear the stored key, non-empty = set it.
    mistral_api_key: str | None = Field(default=None, max_length=256)


class ModelList(BaseModel):
    provider: str
    models: list[str]
    installed: list[str]
    reachable: bool


class PullRequest(BaseModel):
    name: str = Field(min_length=1, max_length=128)


class PullStatus(BaseModel):
    name: str
    status: str
    completed: bool
    percent: float | None = None
    error: str | None = None


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
