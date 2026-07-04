from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from app.schemas.session import WeakKeyInfo


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
