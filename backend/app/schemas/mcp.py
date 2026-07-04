from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class LifetimeStats(BaseModel):
    sessions: int
    total_time_minutes: float
    best_wpm: float | None
    avg_wpm_30d: float | None
    avg_accuracy_30d: float | None


class WeakKey(BaseModel):
    char: str
    error_rate: float
    avg_latency_ms: float | None


class Trend7d(BaseModel):
    wpm: list[float]
    accuracy: list[float]


class McpSummary(BaseModel):
    user: str
    generated_at: datetime
    layout: str
    lifetime: LifetimeStats
    weak_keys: list[WeakKey]
    trend_7d: Trend7d
    coach_prompt: str


class McpRecommendations(BaseModel):
    user: str
    generated_at: datetime
    layout: str
    focus_keys: list[WeakKey]
    prompt: str


# ── API key management (Settings) ────────────────────────────────────────────
class ApiKeyCreateRequest(BaseModel):
    name: str = Field(default="default", min_length=1, max_length=64)


class ApiKeyCreated(BaseModel):
    id: str
    name: str
    prefix: str
    api_key: str = Field(description="Full key — shown once, store it now.")


class ApiKeyInfo(BaseModel):
    id: str
    name: str
    prefix: str
    created_at: datetime
    last_used_at: datetime | None
    revoked_at: datetime | None


class ApiKeyList(BaseModel):
    keys: list[ApiKeyInfo]
