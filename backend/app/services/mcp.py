"""Assemble MCP payloads (Section 12) from user stats + the adaptive engine."""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.engine.layouts import get_layout
from app.models.session import TypingSession
from app.models.user import User
from app.schemas.mcp import (
    LifetimeStats,
    McpRecommendations,
    McpSummary,
    Trend7d,
    WeakKey,
)
from app.services.key_stats import build_key_metrics, weakest_scored_keys


async def _lifetime(db: AsyncSession, user_id: uuid.UUID, layout_id: str) -> LifetimeStats:
    base = (
        TypingSession.user_id == user_id,
        TypingSession.layout_id == layout_id,
        TypingSession.completed_at.is_not(None),
    )
    now = datetime.now(timezone.utc)
    since_30 = now - timedelta(days=30)
    row = (
        await db.execute(
            select(
                func.count(TypingSession.id),
                func.coalesce(func.sum(TypingSession.duration_s), 0),
                func.max(TypingSession.wpm_net),
            ).where(*base)
        )
    ).one()
    recent = (
        await db.execute(
            select(
                func.avg(TypingSession.wpm_net),
                func.avg(TypingSession.accuracy),
            ).where(*base, TypingSession.started_at >= since_30)
        )
    ).one()
    return LifetimeStats(
        sessions=int(row[0] or 0),
        total_time_minutes=round(float(row[1] or 0) / 60.0, 1),
        best_wpm=round(float(row[2]), 1) if row[2] is not None else None,
        avg_wpm_30d=round(float(recent[0]), 1) if recent[0] is not None else None,
        avg_accuracy_30d=round(float(recent[1]), 3) if recent[1] is not None else None,
    )


async def _trend_7d(db: AsyncSession, user_id: uuid.UUID, layout_id: str) -> Trend7d:
    since = datetime.now(timezone.utc) - timedelta(days=7)
    day = func.date(TypingSession.started_at).label("day")
    result = await db.execute(
        select(
            day,
            func.avg(TypingSession.wpm_net),
            func.avg(TypingSession.accuracy),
        )
        .where(
            TypingSession.user_id == user_id,
            TypingSession.layout_id == layout_id,
            TypingSession.completed_at.is_not(None),
            TypingSession.started_at >= since,
        )
        .group_by(day)
        .order_by(day)
    )
    wpm: list[float] = []
    acc: list[float] = []
    for row in result.all():
        if row[1] is not None:
            wpm.append(round(float(row[1]), 1))
        if row[2] is not None:
            acc.append(round(float(row[2]), 3))
    return Trend7d(wpm=wpm, accuracy=acc)


async def _weak_keys(db: AsyncSession, user_id: uuid.UUID, layout_id: str, n: int = 5) -> list[WeakKey]:
    metrics = await build_key_metrics(db, user_id, layout_id)
    scored = await weakest_scored_keys(db, user_id, layout_id, n=n)
    lat = {m.character: m.avg_latency_ms for m in metrics}
    return [
        WeakKey(
            char=s.character,
            error_rate=round(s.error_rate, 3),
            avg_latency_ms=round(lat[s.character], 0) if lat.get(s.character) is not None else None,
        )
        for s in scored
        if s.score > 0.0
    ]


def _coach_prompt(user: User, lifetime: LifetimeStats, weak: list[WeakKey], trend: Trend7d) -> str:
    wk = ", ".join(w.char for w in weak) or "none identified yet"
    plateau = ""
    if len(trend.wpm) >= 2:
        delta = trend.wpm[-1] - trend.wpm[0]
        if abs(delta) < 1.0:
            plateau = f"User appears to be plateauing around {trend.wpm[-1]:.0f} WPM. "
        elif delta > 0:
            plateau = f"Rolling 7-day trend shows improvement (+{delta:.0f} WPM). "
        else:
            plateau = f"Rolling 7-day trend shows a dip ({delta:.0f} WPM). "
    avg = f"{lifetime.avg_wpm_30d:.0f}" if lifetime.avg_wpm_30d is not None else "unknown"
    return (
        f"User {user.username} is training at ~{avg} WPM (30-day avg). "
        f"{plateau}"
        f"Weak keys remain: {wk}. "
        "Suggest targeted drills focusing on these keys within realistic bigrams "
        "and trigrams, and recommend a session cadence."
    )


async def build_summary(db: AsyncSession, user: User, layout_id: str) -> McpSummary:
    layout = get_layout(layout_id)
    lifetime = await _lifetime(db, user.id, layout_id)
    weak = await _weak_keys(db, user.id, layout_id)
    trend = await _trend_7d(db, user.id, layout_id)
    return McpSummary(
        user=user.username,
        generated_at=datetime.now(timezone.utc),
        layout=layout.name if layout else layout_id,
        lifetime=lifetime,
        weak_keys=weak,
        trend_7d=trend,
        coach_prompt=_coach_prompt(user, lifetime, weak, trend),
    )


async def build_recommendations(db: AsyncSession, user: User, layout_id: str) -> McpRecommendations:
    layout = get_layout(layout_id)
    weak = await _weak_keys(db, user.id, layout_id)
    focus = ", ".join(w.char for w in weak) or "none"
    prompt = (
        f"Generate a targeted typing drill for {user.username} on "
        f"{layout.name if layout else layout_id}. Prioritise these weak keys: {focus}. "
        "Embed them in common English bigrams and trigrams (not random strings), "
        "weight them ~3x natural frequency, and keep the drill to ~60 seconds of "
        "typing. Return plain lesson text only."
    )
    return McpRecommendations(
        user=user.username,
        generated_at=datetime.now(timezone.utc),
        layout=layout.name if layout else layout_id,
        focus_keys=weak,
        prompt=prompt,
    )
