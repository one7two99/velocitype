"""key_stats aggregation + adaptive-metric assembly.

Bridges the persistence layer (keystrokes / key_stats) and the pure adaptive
engine. Everything here is async SQLAlchemy; the engine stays framework-free.
"""
from __future__ import annotations

import uuid
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.engine import adaptive
from app.engine.adaptive import KeyMetric, ScoredKey
from app.models.key_stat import KeyStat
from app.models.keystroke import Keystroke
from app.models.session import TypingSession
from app.schemas.keystroke import KeystrokeIn


async def _user_session_seq(db: AsyncSession, user_id: uuid.UUID) -> int:
    """Monotonic per-user session counter used for the recency term."""
    result = await db.execute(
        select(func.count(TypingSession.id)).where(TypingSession.user_id == user_id)
    )
    return int(result.scalar_one() or 0)


async def session_has_keystrokes(db: AsyncSession, session_id: uuid.UUID) -> bool:
    result = await db.execute(
        select(func.count(Keystroke.id)).where(Keystroke.session_id == session_id)
    )
    return int(result.scalar_one() or 0) > 0


def _per_key_aggregates(keystrokes: list[KeystrokeIn]) -> dict[str, dict]:
    """Fold a keystroke batch into per-character attempts/errors/latency samples.

    Latency for a keystroke is the inter-key interval (delta of ts_offset_ms from
    the previous keystroke), attributed to the character being typed. The first
    keystroke has no measurable latency and contributes none.
    """
    ordered = sorted(keystrokes, key=lambda k: k.ts_offset_ms)
    agg: dict[str, dict] = {}
    prev_ts: int | None = None
    for ks in ordered:
        char = ks.expected_char
        bucket = agg.setdefault(char, {"attempts": 0, "errors": 0, "lat_sum": 0.0, "lat_n": 0})
        bucket["attempts"] += 1
        if not ks.correct:
            bucket["errors"] += 1
        latency = None
        if ks.hold_ms is not None:
            latency = float(ks.hold_ms)
        elif prev_ts is not None:
            latency = float(max(0, ks.ts_offset_ms - prev_ts))
        if latency is not None:
            bucket["lat_sum"] += latency
            bucket["lat_n"] += 1
        prev_ts = ks.ts_offset_ms
    return agg


async def apply_keystrokes(
    db: AsyncSession,
    session: TypingSession,
    keystrokes: list[KeystrokeIn],
) -> tuple[int, int]:
    """Persist a keystroke batch and roll it into key_stats. Commits.

    Returns (keystrokes_saved, key_stats_rows_touched).
    """
    for ks in keystrokes:
        db.add(
            Keystroke(
                session_id=session.id,
                ts_offset_ms=ks.ts_offset_ms,
                expected_char=ks.expected_char,
                actual_char=ks.actual_char,
                correct=ks.correct,
                hold_ms=ks.hold_ms,
            )
        )

    seq = await _user_session_seq(db, session.user_id)
    agg = _per_key_aggregates(keystrokes)

    touched = 0
    for char, data in agg.items():
        stat = await db.get(KeyStat, (session.user_id, session.layout_id, char))
        if stat is None:
            avg_latency = (data["lat_sum"] / data["lat_n"]) if data["lat_n"] else None
            stat = KeyStat(
                user_id=session.user_id,
                layout_id=session.layout_id,
                character=char,
                attempts=data["attempts"],
                errors=data["errors"],
                avg_latency_ms=Decimal(str(round(avg_latency, 2))) if avg_latency is not None else None,
                last_session_seq=seq,
            )
            db.add(stat)
        else:
            # Weighted running mean over prior attempts + this batch's samples.
            if data["lat_n"]:
                prior_n = stat.attempts
                prior_avg = float(stat.avg_latency_ms) if stat.avg_latency_ms is not None else 0.0
                combined_n = prior_n + data["lat_n"]
                new_avg = (prior_avg * prior_n + data["lat_sum"]) / combined_n if combined_n else prior_avg
                stat.avg_latency_ms = Decimal(str(round(new_avg, 2)))
            stat.attempts += data["attempts"]
            stat.errors += data["errors"]
            stat.last_session_seq = seq
        touched += 1

    await db.commit()
    return len(keystrokes), touched


async def build_key_metrics(
    db: AsyncSession, user_id: uuid.UUID, layout_id: str
) -> list[KeyMetric]:
    result = await db.execute(
        select(KeyStat).where(
            KeyStat.user_id == user_id, KeyStat.layout_id == layout_id
        )
    )
    rows = result.scalars().all()
    current_seq = await _user_session_seq(db, user_id)
    metrics: list[KeyMetric] = []
    for r in rows:
        metrics.append(
            KeyMetric(
                character=r.character,
                attempts=r.attempts,
                errors=r.errors,
                avg_latency_ms=float(r.avg_latency_ms) if r.avg_latency_ms is not None else None,
                sessions_since_seen=max(0, current_seq - r.last_session_seq),
            )
        )
    return metrics


async def weakest_scored_keys(
    db: AsyncSession, user_id: uuid.UUID, layout_id: str, n: int = 5
) -> list[ScoredKey]:
    metrics = await build_key_metrics(db, user_id, layout_id)
    if not metrics:
        return []
    return adaptive.weakest_keys(metrics, n=n)
