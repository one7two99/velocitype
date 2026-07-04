"""Lesson generation service — glues user key metrics to the adaptive engine."""
from __future__ import annotations

import random
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.engine import adaptive
from app.engine.layouts import get_layout
from app.schemas.session import WeakKeyInfo
from app.services.key_stats import build_key_metrics


async def generate_adaptive_lesson(
    db: AsyncSession,
    user_id: uuid.UUID,
    layout_id: str,
    rng: random.Random | None = None,
) -> tuple[str, list[WeakKeyInfo]]:
    """Return (lesson_text, weak_keys). Falls back to a general lesson over the
    whole layout when the user has no history yet."""
    layout = get_layout(layout_id)
    if layout is None:
        raise ValueError(f"unknown layout '{layout_id}'")

    metrics = await build_key_metrics(db, user_id, layout_id)
    scored = adaptive.weakest_keys(metrics, n=5) if metrics else []
    # Only treat keys with a non-trivial score as genuinely "weak".
    weak_scored = [s for s in scored if s.score > 0.0]
    weak_chars = [s.character for s in weak_scored]

    lesson = adaptive.generate_lesson(
        weak_keys=weak_chars,
        layout_characters=layout.characters,
        rng=rng,
    )
    weak_info = [
        WeakKeyInfo(
            char=s.character,
            error_rate=round(s.error_rate, 4),
            avg_latency_ms=next(
                (m.avg_latency_ms for m in metrics if m.character == s.character), None
            ),
        )
        for s in weak_scored
    ]
    return lesson, weak_info
