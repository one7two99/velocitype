from __future__ import annotations

from datetime import date, datetime

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
    consistency: float | None = None


class KeyHeatmap(BaseModel):
    layout_id: str
    keys: list[KeyHeatCell]


class NgramRow(BaseModel):
    ngram: str
    cls: str | None = None          # BigramClass value (SFB / ROLL_IN / …)
    attempts: int
    errors: int
    error_rate: float
    avg_latency_ms: float | None
    wpm: float | None               # transition speed = 12000 / avg_latency_ms
    consistency: float | None       # rhythm: 1 − CV of the bigram's IKIs
    hitch_rate: float | None        # hitch_n / latency_n
    latency_n: int


class NgramTable(BaseModel):
    layout_id: str
    ngrams: list[NgramRow]


class ProgressSeries(BaseModel):
    layout_id: str
    days: int
    points: list[TrendPoint]


class SessionStatPoint(BaseModel):
    index: int                      # 1-based chronological position
    started_at: datetime
    distinct_keys: int              # distinct (non-space) characters typed
    avg_wpm: float | None           # mean rolling-window speed within the session
    max_wpm: float | None           # peak rolling-window speed within the session
    accuracy: float | None


class SessionStatSeries(BaseModel):
    layout_id: str
    points: list[SessionStatPoint]
