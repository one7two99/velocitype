"""Coach router: local-LLM (Ollama) coaching — analysis + drill generation.

Session-authenticated. Runs inference against the self-hosted Ollama service; no
external LLM API is used.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query, Response, status as http_status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.config import get_settings
from app.db.session import get_db
from app.engine.layouts import DEFAULT_LAYOUT_ID, get_layout
from app.errors import ProblemException
from app.models.ai_config import UserAiConfig
from app.models.prompt import UserPrompt
from app.models.user import User
from app.schemas.coach import (
    AiConfig,
    AiConfigUpdate,
    CoachAnalysis,
    CoachDrill,
    CoachPrompts,
    CoachPromptsUpdate,
    CoachStatus,
    DrillRequest,
    ModelList,
    PromptCustom,
    PromptSet,
    PullRequest,
    PullStatus,
)
from app.schemas.mcp import McpSummary
from app.services import coach, crypto, llm, ollama
from app.services.llm import LLMError
from app.services.mcp import build_summary

_settings = get_settings()
router = APIRouter(prefix="/api/coach", tags=["coach"])


def _require_layout(layout_id: str) -> None:
    if get_layout(layout_id) is None:
        raise ProblemException(
            status_code=422, title="Unprocessable Entity",
            detail=f"Unknown layout '{layout_id}'.", type_="about:unknown-layout",
        )


def _coach_error(exc: LLMError) -> ProblemException:
    msg = str(exc)
    # A missing cloud key is a user-config problem, not a transient outage.
    if "api key" in msg.lower():
        return ProblemException(
            status_code=422,
            title="Unprocessable Entity",
            detail="Set your Mistral API key in Settings → AI Provider.",
            type_="about:coach-no-key",
        )
    return ProblemException(
        status_code=503,
        title="Service Unavailable",
        detail=(
            "The coaching model is not available. A local model may still be "
            f"downloading, or the cloud provider is unreachable. ({msg})"
        ),
        type_="about:coach-unavailable",
    )


@router.get("/status", response_model=CoachStatus)
async def coach_status(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> CoachStatus:
    return CoachStatus(**await coach.status(db, user))


async def _get_ai_config(db: AsyncSession, user: User) -> AiConfig:
    row = (
        await db.execute(select(UserAiConfig).where(UserAiConfig.user_id == user.id))
    ).scalar_one_or_none()
    return AiConfig(
        provider=(row.provider if row and row.provider else llm.OLLAMA),
        ollama_model=(row.ollama_model if row and row.ollama_model else _settings.ollama_model),
        mistral_model=(row.mistral_model if row and row.mistral_model else _settings.mistral_default_model),
        mistral_key_set=bool(row and row.mistral_api_key_enc),
        ollama_default=_settings.ollama_model,
        mistral_default=_settings.mistral_default_model,
    )


@router.get("/config", response_model=AiConfig)
async def get_config(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> AiConfig:
    return await _get_ai_config(db, user)


@router.put("/config", response_model=AiConfig)
async def put_config(
    payload: AiConfigUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> AiConfig:
    row = (
        await db.execute(select(UserAiConfig).where(UserAiConfig.user_id == user.id))
    ).scalar_one_or_none()
    if row is None:
        row = UserAiConfig(user_id=user.id)
        db.add(row)
    if payload.provider is not None:
        row.provider = payload.provider
    if payload.ollama_model is not None:
        row.ollama_model = payload.ollama_model or None
    if payload.mistral_model is not None:
        row.mistral_model = payload.mistral_model or None
    # null = leave key unchanged; "" = clear; non-empty = set (encrypted).
    if payload.mistral_api_key is not None:
        row.mistral_api_key_enc = (
            crypto.encrypt(payload.mistral_api_key) if payload.mistral_api_key else None
        )
    await db.commit()
    return await _get_ai_config(db, user)


@router.get("/models", response_model=ModelList)
async def list_models(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    provider: str = Query(default=""),
) -> ModelList:
    """Available models for a provider (defaults to the user's active provider)."""
    cfg = await coach.get_ai_config(db, user.id)
    if provider in llm.PROVIDERS and provider != cfg.provider:
        # Listing a provider that isn't the active one (e.g. previewing Mistral
        # models): reuse the stored key for Mistral.
        if provider == llm.MISTRAL:
            cfg = llm.LLMConfig(provider=llm.MISTRAL, model=cfg.model, api_key=cfg.api_key)
        else:
            cfg = llm.LLMConfig(provider=llm.OLLAMA, model=_settings.ollama_model)
    result = await llm.list_models(cfg)
    return ModelList(provider=cfg.provider, **result)


@router.post("/models/pull", response_model=PullStatus, status_code=http_status.HTTP_202_ACCEPTED)
async def pull_model(
    payload: PullRequest,
    response: Response,
    _: User = Depends(get_current_user),
) -> PullStatus:
    """Start downloading an Ollama model (background). Poll GET /models/pull."""
    name = payload.name.strip()
    if not ollama.pull_active(name):
        asyncio.create_task(ollama.pull_model(name))
    return PullStatus(**ollama.pull_progress(name))


@router.get("/models/pull", response_model=PullStatus)
async def pull_model_status(
    name: str = Query(..., min_length=1, max_length=128),
    _: User = Depends(get_current_user),
) -> PullStatus:
    return PullStatus(**ollama.pull_progress(name))


@router.get("/prompts", response_model=CoachPrompts)
async def get_prompts(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> CoachPrompts:
    """Default AI-coach prompts + this user's overrides (null = using default)."""
    row = (
        await db.execute(select(UserPrompt).where(UserPrompt.user_id == user.id))
    ).scalar_one_or_none()
    custom = PromptCustom(
        analysis_system=row.analysis_system if row else None,
        analysis_user=row.analysis_user if row else None,
        drill_system=row.drill_system if row else None,
        drill_user=row.drill_user if row else None,
    )
    return CoachPrompts(defaults=PromptSet(**coach.DEFAULT_PROMPTS), custom=custom)


@router.put("/prompts", response_model=CoachPrompts)
async def put_prompts(
    payload: CoachPromptsUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> CoachPrompts:
    """Upsert the user's prompt overrides. A null/empty field clears the override."""
    row = (
        await db.execute(select(UserPrompt).where(UserPrompt.user_id == user.id))
    ).scalar_one_or_none()
    if row is None:
        row = UserPrompt(user_id=user.id)
        db.add(row)
    # Empty string → None so it reverts to the default.
    row.analysis_system = payload.analysis_system or None
    row.analysis_user = payload.analysis_user or None
    row.drill_system = payload.drill_system or None
    row.drill_user = payload.drill_user or None
    await db.commit()
    return await get_prompts(db, user)


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
        text, model = await coach.analyze(db, user, layout_id)
    except LLMError as exc:
        raise _coach_error(exc)
    return CoachAnalysis(
        layout_id=layout_id,
        model=model,
        generated_at=datetime.now(timezone.utc),
        analysis=text,
    )


@router.post("/drill", response_model=CoachDrill)
async def drill(
    payload: DrillRequest | None = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    layout_id: str = Query(default=DEFAULT_LAYOUT_ID, max_length=64),
) -> CoachDrill:
    _require_layout(layout_id)
    focus_keys = payload.focus_keys if payload else None
    lesson, weak_keys, source, model = await coach.drill(
        db, user, layout_id, focus_keys=focus_keys
    )
    return CoachDrill(
        layout_id=layout_id,
        model=model,
        generated_at=datetime.now(timezone.utc),
        lesson=lesson,
        word_count=len(lesson.split()),
        weak_keys=weak_keys,
        source=source,
    )
