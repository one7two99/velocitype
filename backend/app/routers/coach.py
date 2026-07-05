"""Coach router: local-LLM (Ollama) coaching — analysis + drill generation.

Session-authenticated. Runs inference against the self-hosted Ollama service; no
external LLM API is used.
"""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.config import get_settings
from app.db.session import get_db
from app.engine.layouts import DEFAULT_LAYOUT_ID, get_layout
from app.errors import ProblemException
from app.models.user import User
from app.schemas.coach import CoachAnalysis, CoachDrill, CoachStatus
from app.schemas.mcp import McpSummary
from app.services import coach
from app.services.mcp import build_summary
from app.services.ollama import OllamaError

_settings = get_settings()
router = APIRouter(prefix="/api/coach", tags=["coach"])


def _require_layout(layout_id: str) -> None:
    if get_layout(layout_id) is None:
        raise ProblemException(
            status_code=422, title="Unprocessable Entity",
            detail=f"Unknown layout '{layout_id}'.", type_="about:unknown-layout",
        )


def _unavailable(exc: OllamaError) -> ProblemException:
    return ProblemException(
        status_code=503,
        title="Service Unavailable",
        detail=(
            "The local coaching model is not available yet. It may still be "
            f"downloading. ({exc})"
        ),
        type_="about:coach-unavailable",
    )


@router.get("/status", response_model=CoachStatus)
async def coach_status(_: User = Depends(get_current_user)) -> CoachStatus:
    return CoachStatus(**await coach.status())


@router.get("/metrics", response_model=McpSummary)
async def coach_metrics(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    layout_id: str = Query(default=DEFAULT_LAYOUT_ID, max_length=64),
) -> McpSummary:
    """The exact stats the coach uses (transparency), for display in the UI."""
    _require_layout(layout_id)
    return await build_summary(db, user, layout_id)


@router.post("/analyze", response_model=CoachAnalysis)
async def analyze(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    layout_id: str = Query(default=DEFAULT_LAYOUT_ID, max_length=64),
) -> CoachAnalysis:
    _require_layout(layout_id)
    try:
        text = await coach.analyze(db, user, layout_id)
    except OllamaError as exc:
        raise _unavailable(exc)
    return CoachAnalysis(
        layout_id=layout_id,
        model=_settings.ollama_model,
        generated_at=datetime.now(timezone.utc),
        analysis=text,
    )


@router.post("/drill", response_model=CoachDrill)
async def drill(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    layout_id: str = Query(default=DEFAULT_LAYOUT_ID, max_length=64),
) -> CoachDrill:
    _require_layout(layout_id)
    lesson, weak_keys, source = await coach.drill(db, user, layout_id)
    return CoachDrill(
        layout_id=layout_id,
        model=_settings.ollama_model,
        generated_at=datetime.now(timezone.utc),
        lesson=lesson,
        word_count=len(lesson.split()),
        weak_keys=weak_keys,
        source=source,
    )
