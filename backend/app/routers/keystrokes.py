"""Keystrokes router: bulk batch save on session completion (Section 4).

The canonical path for persisting a session's keystrokes and rolling them into
key_stats. Idempotent per session: a second batch for the same session is
rejected so aggregates are never double-counted.
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.db.session import get_db
from app.errors import ProblemException
from app.models.session import TypingSession
from app.models.user import User
from app.schemas.keystroke import KeystrokeBatch, KeystrokeBatchResponse
from app.services.key_stats import apply_keystrokes, session_has_keystrokes

router = APIRouter(prefix="/api/sessions", tags=["keystrokes"])


@router.post("/{session_id}/keystrokes", response_model=KeystrokeBatchResponse, status_code=201)
async def save_keystrokes(
    session_id: uuid.UUID,
    payload: KeystrokeBatch,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> KeystrokeBatchResponse:
    session = await db.get(TypingSession, session_id)
    if session is None or session.user_id != user.id:
        raise ProblemException(
            status_code=404, title="Not Found",
            detail="Session not found.", type_="about:not-found",
        )
    if await session_has_keystrokes(db, session.id):
        raise ProblemException(
            status_code=409, title="Conflict",
            detail="Keystrokes already recorded for this session.",
            type_="about:already-recorded",
        )

    saved, touched = await apply_keystrokes(db, session, payload.keystrokes)
    return KeystrokeBatchResponse(saved=saved, keys_updated=touched)
