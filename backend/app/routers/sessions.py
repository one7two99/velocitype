"""Sessions router: start, complete, detail, history (Section 4)."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, Query
from sqlalchemy import delete, exists, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.db.session import get_db
from app.errors import ProblemException
from app.engine.layouts import get_layout
from app.models.keystroke import Keystroke
from app.models.session import TypingSession
from app.models.user import User
from app.schemas.session import (
    SessionCompleteRequest,
    SessionCompleteResponse,
    SessionDetail,
    SessionHistory,
    SessionMetrics,
    SessionStartRequest,
    SessionStartResponse,
    SessionSummary,
    WeakKeyInfo,
)
from app.services import progress
from app.services.key_stats import (
    apply_keystrokes,
    session_has_keystrokes,
    weakest_scored_keys,
)
from app.services.lessons import generate_adaptive_lesson

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


async def _get_owned_session(
    db: AsyncSession, session_id: uuid.UUID, user: User
) -> TypingSession:
    session = await db.get(TypingSession, session_id)
    if session is None or session.user_id != user.id:
        raise ProblemException(
            status_code=404, title="Not Found",
            detail="Session not found.", type_="about:not-found",
        )
    return session


@router.post("/start", response_model=SessionStartResponse, status_code=201)
async def start_session(
    payload: SessionStartRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> SessionStartResponse:
    if get_layout(payload.layout_id) is None:
        raise ProblemException(
            status_code=422, title="Unprocessable Entity",
            detail=f"Unknown layout '{payload.layout_id}'.", type_="about:unknown-layout",
        )

    # Sweep this user's abandoned, never-typed sessions before opening a new one.
    # A session row is created here at start but only gets metrics at complete, so
    # aborted starts (changing settings, opening the Trainer and leaving) would
    # otherwise pile up as null-metric rows in history. Only rows that were never
    # completed AND never received a keystroke are removed; genuine partial
    # attempts (with keystrokes) are kept.
    await db.execute(
        delete(TypingSession).where(
            TypingSession.user_id == user.id,
            TypingSession.completed_at.is_(None),
            ~exists().where(Keystroke.session_id == TypingSession.id),
        )
    )

    session = TypingSession(
        user_id=user.id,
        layout_id=payload.layout_id,
        mode=payload.mode,
        duration_s=payload.duration_s,
        word_count=payload.word_count,
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)

    # Size the lesson to the session goal so timed mode doesn't run out of text;
    # target_wpm makes key selection prioritise keys below the target speed.
    sizing = {
        "target_seconds": payload.duration_s,
        "min_words": payload.word_count,
        "target_wpm": payload.target_wpm,
    }

    weak: list[WeakKeyInfo] = []
    if payload.mode in ("custom", "coach_drill"):
        lesson = payload.custom_text or ""
    elif payload.mode == "adaptive":
        lesson, weak = await generate_adaptive_lesson(
            db, user.id, payload.layout_id, **sizing
        )
    else:  # fixed_text — a general, non-adaptive lesson over the whole layout
        lesson, _ = await generate_adaptive_lesson(
            db, user.id, payload.layout_id, **sizing
        )

    return SessionStartResponse(
        session_id=session.id,
        layout_id=session.layout_id,
        mode=payload.mode,
        lesson=lesson,
        weak_keys=weak,
    )


@router.post("/{session_id}/complete", response_model=SessionCompleteResponse)
async def complete_session(
    session_id: uuid.UUID,
    payload: SessionCompleteRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> SessionCompleteResponse:
    session = await _get_owned_session(db, session_id, user)
    if session.completed_at is not None:
        raise ProblemException(
            status_code=409, title="Conflict",
            detail="Session already completed.", type_="about:already-completed",
        )

    # Apply inline keystrokes if provided and none were posted separately.
    if payload.keystrokes and not await session_has_keystrokes(db, session.id):
        await apply_keystrokes(db, session, payload.keystrokes)

    session.completed_at = datetime.now(timezone.utc)
    session.wpm_raw = Decimal(str(round(payload.wpm_raw, 2)))
    session.wpm_net = Decimal(str(round(payload.wpm_net, 2)))
    session.accuracy = Decimal(str(round(payload.accuracy, 4)))
    session.consistency = Decimal(str(round(payload.consistency, 4)))
    if payload.duration_s is not None:
        session.duration_s = payload.duration_s
    await db.commit()
    await db.refresh(session)

    scored = await weakest_scored_keys(
        db, user.id, session.layout_id, n=5, target_wpm=payload.target_wpm
    )
    weak = [
        WeakKeyInfo(char=s.character, error_rate=round(s.error_rate, 4))
        for s in scored if s.score > 0.0
    ]

    # Progressive unlocking: reveal the next key if the active set is mastered.
    settings = await progress.get_user_settings(db, user.id)
    unlocked_char = await progress.advance_if_mastered(
        db, user.id, session.layout_id, settings
    )
    if unlocked_char is not None:
        await db.commit()

    return SessionCompleteResponse(
        session_id=session.id,
        metrics=SessionMetrics.model_validate(session),
        weak_keys=weak,
        unlocked_char=unlocked_char,
    )


@router.get("", response_model=SessionHistory)
async def session_history(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
) -> SessionHistory:
    # Only completed sessions carry metrics; incomplete/abandoned rows would show
    # as blank WPM/accuracy in the dashboard's "Recent Sessions", so exclude them.
    total = await db.scalar(
        select(func.count(TypingSession.id)).where(
            TypingSession.user_id == user.id,
            TypingSession.completed_at.is_not(None),
        )
    )
    result = await db.execute(
        select(TypingSession)
        .where(
            TypingSession.user_id == user.id,
            TypingSession.completed_at.is_not(None),
        )
        .order_by(TypingSession.started_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    items = [SessionSummary.model_validate(s) for s in result.scalars().all()]
    return SessionHistory(items=items, page=page, page_size=page_size, total=int(total or 0))


@router.get("/{session_id}", response_model=SessionDetail)
async def session_detail(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> SessionDetail:
    session = await _get_owned_session(db, session_id, user)
    ks_count = await db.scalar(
        select(func.count(Keystroke.id)).where(Keystroke.session_id == session.id)
    )
    detail = SessionDetail.model_validate(session)
    detail.keystroke_count = int(ks_count or 0)
    return detail
