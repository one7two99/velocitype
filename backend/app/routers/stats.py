"""Stats router: overview, per-key heatmap, progress time-series (Section 4)."""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from statistics import fmean

from fastapi import APIRouter, Depends, Query
from sqlalchemy import Numeric, cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.db.session import get_db
from app.engine import adaptive
from app.engine import ngrams as ngram_engine
from app.engine.layouts import DEFAULT_LAYOUT_ID, get_layout
from app.models.key_stat import KeyStat
from app.models.keystroke import Keystroke
from app.models.session import TypingSession
from app.models.user import User
from app.schemas.stats import (
    KeyHeatCell,
    KeyHeatmap,
    NgramRow,
    NgramTable,
    ProgressSeries,
    SessionStatPoint,
    SessionStatSeries,
    StatsOverview,
    TopError,
    TrendPoint,
)
from app.services.ngram_stats import build_ngram_metrics

router = APIRouter(prefix="/api/stats", tags=["stats"])


def _f(value) -> float | None:
    return float(value) if value is not None else None


# Rolling window (in inter-key intervals) used to derive intra-session speed.
# A short window smooths single-keystroke jitter while still exposing genuine
# bursts as the session's peak. Instantaneous speed over W intervals spanning
# dt ms is (W chars / 5) / (dt / 60000) == W * 12000 / dt, matching the app's
# per-key WPM convention (12000 / latency_ms).
_WPM_WINDOW = 5
_MAX_WPM_CAP = 300.0


def _session_speed(offsets: list[int]) -> tuple[float | None, float | None]:
    """Return (avg_wpm, max_wpm) computed from a session's keystroke offsets."""
    ts = sorted(offsets)
    n = len(ts)
    if n < 2:
        return None, None
    window = min(_WPM_WINDOW, n - 1)
    wpms: list[float] = []
    for i in range(window, n):
        dt = ts[i] - ts[i - window]
        if dt > 0:
            wpms.append(min(window * 12000.0 / dt, _MAX_WPM_CAP))
    if not wpms:  # every keystroke shared a timestamp; fall back to the full span
        span = ts[-1] - ts[0]
        if span <= 0:
            return None, None
        w = min((n - 1) * 12000.0 / span, _MAX_WPM_CAP)
        return w, w
    return fmean(wpms), max(wpms)


async def _daily_trend(
    db: AsyncSession, user_id: uuid.UUID, layout_id: str, since: datetime
) -> list[TrendPoint]:
    day = func.date(TypingSession.started_at).label("day")
    result = await db.execute(
        select(
            day,
            func.avg(TypingSession.wpm_net).label("wpm"),
            func.avg(TypingSession.accuracy).label("acc"),
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
    points: list[TrendPoint] = []
    for row in result.all():
        points.append(
            TrendPoint(
                date=row.day,
                wpm=round(_f(row.wpm), 2) if row.wpm is not None else None,
                accuracy=round(_f(row.acc), 4) if row.acc is not None else None,
            )
        )
    return points


@router.get("/overview", response_model=StatsOverview)
async def overview(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    layout_id: str = Query(default=DEFAULT_LAYOUT_ID, max_length=64),
) -> StatsOverview:
    base = (
        TypingSession.user_id == user.id,
        TypingSession.layout_id == layout_id,
        TypingSession.completed_at.is_not(None),
    )
    now = datetime.now(timezone.utc)
    since_30 = now - timedelta(days=30)

    agg = (
        await db.execute(
            select(
                func.count(TypingSession.id),
                func.coalesce(func.sum(TypingSession.duration_s), 0),
                func.max(TypingSession.wpm_net),
                func.max(TypingSession.accuracy),
                func.min(TypingSession.consistency),
            ).where(*base)
        )
    ).one()
    total_sessions, total_seconds, best_wpm, best_acc, best_cons = agg

    recent = (
        await db.execute(
            select(
                func.avg(TypingSession.wpm_net),
                func.avg(TypingSession.accuracy),
            ).where(*base, TypingSession.started_at >= since_30)
        )
    ).one()
    avg_wpm_30d, avg_acc_30d = recent

    # Top error keys (require a minimum sample so a single mistake isn't "worst").
    err_rate = cast(KeyStat.errors, Numeric) / func.nullif(KeyStat.attempts, 0)
    top = await db.execute(
        select(KeyStat.character, KeyStat.errors, KeyStat.attempts, err_rate.label("rate"))
        .where(
            KeyStat.user_id == user.id,
            KeyStat.layout_id == layout_id,
            KeyStat.attempts >= 5,
        )
        .order_by(err_rate.desc())
        .limit(5)
    )
    top_errors = [
        TopError(
            char=r.character,
            error_rate=round(_f(r.rate) or 0.0, 4),
            errors=r.errors,
            attempts=r.attempts,
        )
        for r in top.all()
    ]

    trend = await _daily_trend(db, user.id, layout_id, since_30)

    return StatsOverview(
        layout_id=layout_id,
        total_sessions=int(total_sessions or 0),
        total_time_minutes=round(float(total_seconds or 0) / 60.0, 2),
        best_wpm=round(_f(best_wpm), 2) if best_wpm is not None else None,
        avg_wpm_30d=round(_f(avg_wpm_30d), 2) if avg_wpm_30d is not None else None,
        avg_accuracy_30d=round(_f(avg_acc_30d), 4) if avg_acc_30d is not None else None,
        best_accuracy=round(_f(best_acc), 4) if best_acc is not None else None,
        best_consistency=round(_f(best_cons), 4) if best_cons is not None else None,
        wpm_trend=[TrendPoint(date=p.date, wpm=p.wpm) for p in trend],
        accuracy_trend=[TrendPoint(date=p.date, accuracy=p.accuracy) for p in trend],
        top_errors=top_errors,
    )


@router.get("/keys", response_model=KeyHeatmap)
async def key_heatmap(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    layout_id: str = Query(default=DEFAULT_LAYOUT_ID, max_length=64),
) -> KeyHeatmap:
    layout = get_layout(layout_id)
    result = await db.execute(
        select(KeyStat).where(
            KeyStat.user_id == user.id, KeyStat.layout_id == layout_id
        )
    )
    cells: list[KeyHeatCell] = []
    for r in result.scalars().all():
        error_rate = (r.errors / r.attempts) if r.attempts else 0.0
        consistency = adaptive.latency_consistency(
            _f(r.avg_latency_ms), r.latency_n, float(r.latency_sq_sum or 0.0)
        )
        cells.append(
            KeyHeatCell(
                character=r.character,
                hand=layout.hand_map.get(r.character) if layout else None,
                finger=layout.finger_map.get(r.character) if layout else None,
                attempts=r.attempts,
                errors=r.errors,
                error_rate=round(error_rate, 4),
                avg_latency_ms=_f(r.avg_latency_ms),
                consistency=round(consistency, 4) if consistency is not None else None,
            )
        )
    return KeyHeatmap(layout_id=layout_id, keys=cells)


@router.get("/ngrams", response_model=NgramTable)
async def ngram_table(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    layout_id: str = Query(default=DEFAULT_LAYOUT_ID, max_length=64),
) -> NgramTable:
    """Per-bigram table (class + rhythm consistency) for the Analysis page."""
    layout = get_layout(layout_id)
    metrics = await build_ngram_metrics(db, user.id, layout_id)
    rows: list[NgramRow] = []
    for m in metrics:
        cls = (
            ngram_engine.classify_bigram(m.ngram[0], m.ngram[1], layout)
            if layout is not None and len(m.ngram) >= 2
            else None
        )
        cons = ngram_engine.consistency(m.avg_latency_ms, m.latency_n, m.latency_sq_sum)
        wpm = (12000 / m.avg_latency_ms) if m.avg_latency_ms else None
        er = (m.errors / m.attempts) if m.attempts else 0.0
        hitch = (m.hitch_n / m.latency_n) if m.latency_n else None
        rows.append(
            NgramRow(
                ngram=m.ngram,
                cls=cls.value if cls else None,
                attempts=m.attempts,
                errors=m.errors,
                error_rate=round(er, 4),
                avg_latency_ms=m.avg_latency_ms,
                wpm=round(wpm, 1) if wpm else None,
                consistency=round(cons, 4) if cons is not None else None,
                hitch_rate=round(hitch, 4) if hitch is not None else None,
                latency_n=m.latency_n,
            )
        )
    return NgramTable(layout_id=layout_id, ngrams=rows)


@router.get("/progress", response_model=ProgressSeries)
async def progress(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    days: int = Query(default=30, ge=1, le=365),
    layout_id: str = Query(default=DEFAULT_LAYOUT_ID, max_length=64),
) -> ProgressSeries:
    since = datetime.now(timezone.utc) - timedelta(days=days)
    points = await _daily_trend(db, user.id, layout_id, since)
    return ProgressSeries(layout_id=layout_id, days=days, points=points)


@router.get("/sessions", response_model=SessionStatSeries)
async def session_series(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    layout_id: str = Query(default=DEFAULT_LAYOUT_ID, max_length=64),
) -> SessionStatSeries:
    """Per-session series over ALL completed sessions (that have keystrokes):
    distinct keys, intra-session average and peak WPM, and accuracy."""
    rows = await db.execute(
        select(
            TypingSession.id,
            TypingSession.started_at,
            TypingSession.accuracy,
            Keystroke.ts_offset_ms,
            Keystroke.expected_char,
        )
        .join(Keystroke, Keystroke.session_id == TypingSession.id)
        .where(
            TypingSession.user_id == user.id,
            TypingSession.layout_id == layout_id,
            TypingSession.completed_at.is_not(None),
        )
        .order_by(TypingSession.started_at, Keystroke.ts_offset_ms)
    )

    grouped: dict[uuid.UUID, dict] = {}
    order: list[uuid.UUID] = []
    for sid, started, acc, ts, ch in rows.all():
        g = grouped.get(sid)
        if g is None:
            g = {"started_at": started, "accuracy": acc, "offsets": [], "keys": set()}
            grouped[sid] = g
            order.append(sid)
        g["offsets"].append(ts)
        if ch and ch.strip():          # count real keys, not spaces/newlines
            g["keys"].add(ch)

    points: list[SessionStatPoint] = []
    for i, sid in enumerate(order, start=1):
        g = grouped[sid]
        avg_wpm, max_wpm = _session_speed(g["offsets"])
        acc = g["accuracy"]
        points.append(
            SessionStatPoint(
                index=i,
                started_at=g["started_at"],
                distinct_keys=len(g["keys"]),
                avg_wpm=round(avg_wpm, 1) if avg_wpm is not None else None,
                max_wpm=round(max_wpm, 1) if max_wpm is not None else None,
                accuracy=round(_f(acc), 4) if acc is not None else None,
            )
        )
    return SessionStatSeries(layout_id=layout_id, points=points)
