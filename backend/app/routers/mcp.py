"""MCP / external API router (Section 4 & 12).

- /summary and /recommendations are authenticated with a long-lived API key
  (Authorization: Bearer <key>), separate from session JWTs.
- API-key management endpoints (create/list/revoke) use normal session auth and
  back the Settings screen.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user, get_user_from_api_key
from app.auth.password import hash_token
from app.auth.tokens import generate_api_key
from app.db.session import get_db
from app.engine.layouts import DEFAULT_LAYOUT_ID, get_layout
from app.errors import ProblemException
from app.models.api_key import ApiKey
from app.models.user import User
from app.schemas.mcp import (
    ApiKeyCreated,
    ApiKeyCreateRequest,
    ApiKeyInfo,
    ApiKeyList,
    McpRecommendations,
    McpSummary,
)
from app.services.mcp import build_recommendations, build_summary

router = APIRouter(prefix="/api/mcp", tags=["mcp"])


def _require_layout(layout_id: str) -> None:
    if get_layout(layout_id) is None:
        raise ProblemException(
            status_code=422, title="Unprocessable Entity",
            detail=f"Unknown layout '{layout_id}'.", type_="about:unknown-layout",
        )


# ── LLM-facing endpoints (API-key auth) ──────────────────────────────────────
@router.get("/summary", response_model=McpSummary)
async def summary(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_user_from_api_key),
    layout_id: str = Query(default=DEFAULT_LAYOUT_ID, max_length=64),
) -> McpSummary:
    _require_layout(layout_id)
    return await build_summary(db, user, layout_id)


@router.get("/recommendations", response_model=McpRecommendations)
async def recommendations(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_user_from_api_key),
    layout_id: str = Query(default=DEFAULT_LAYOUT_ID, max_length=64),
) -> McpRecommendations:
    _require_layout(layout_id)
    return await build_recommendations(db, user, layout_id)


# ── API-key management (session auth) ────────────────────────────────────────
@router.post("/keys", response_model=ApiKeyCreated, status_code=201)
async def create_api_key(
    payload: ApiKeyCreateRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ApiKeyCreated:
    full_key, prefix = generate_api_key()
    record = ApiKey(
        user_id=user.id,
        name=payload.name,
        prefix=prefix,
        token_hash=hash_token(full_key),
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)
    return ApiKeyCreated(
        id=str(record.id), name=record.name, prefix=record.prefix, api_key=full_key
    )


@router.get("/keys", response_model=ApiKeyList)
async def list_api_keys(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ApiKeyList:
    result = await db.execute(
        select(ApiKey).where(ApiKey.user_id == user.id).order_by(ApiKey.created_at.desc())
    )
    keys = [
        ApiKeyInfo(
            id=str(k.id),
            name=k.name,
            prefix=k.prefix,
            created_at=k.created_at,
            last_used_at=k.last_used_at,
            revoked_at=k.revoked_at,
        )
        for k in result.scalars().all()
    ]
    return ApiKeyList(keys=keys)


@router.delete("/keys/{key_id}", status_code=204, response_class=Response)
async def revoke_api_key(
    key_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Response:
    key = await db.get(ApiKey, key_id)
    if key is None or key.user_id != user.id:
        raise ProblemException(
            status_code=404, title="Not Found",
            detail="API key not found.", type_="about:not-found",
        )
    if key.revoked_at is None:
        key.revoked_at = datetime.now(timezone.utc)
        await db.commit()
    return Response(status_code=204)
