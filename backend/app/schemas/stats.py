from __future__ import annotations

from datetime import date

from pydantic import BaseModel


class TrendPoint(BaseModel):
    date: date
    wpm: float | None = None
    accuracy: float | None = None


class TopError(BaseModel):
    char: str
    error_rate: float
    errors: int
    attempts: int


class StatsOverview(BaseModel):
    layout_id: str
    total_sessions: int
    total_time_minutes: float
    best_wpm: float | None
    avg_wpm_30d: float | None
    avg_accuracy_30d: float | None
    best_accuracy: float | None
    best_consistency: float | None
    wpm_trend: list[TrendPoint]
    accuracy_trend: list[TrendPoint]
    top_errors: list[TopError]


class KeyHeatCell(BaseModel):
    character: str
    hand: str | None = None
    finger: str | None = None
    attempts: int
    errors: int
    error_rate: float
    avg_latency_ms: float | None


class KeyHeatmap(BaseModel):
    layout_id: str
    keys: list[KeyHeatCell]


class ProgressSeries(BaseModel):
    layout_id: str
    days: int
    points: list[TrendPoint]
