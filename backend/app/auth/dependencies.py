"""Authentication dependencies: session-cookie JWT and MCP API-key auth."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

import jwt
from fastapi import Depends, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.password import hash_token
from app.auth.tokens import decode_access_token
from app.config import get_settings
from app.db.session import get_db
from app.errors import ProblemException
from app.models.api_key import ApiKey
from app.models.user import User

_settings = get_settings()


def _unauthorized(detail: str) -> ProblemException:
    return ProblemException(
        status_code=401,
        title="Unauthorized",
        detail=detail,
        type_="about:unauthorized",
        headers={"WWW-Authenticate": "Bearer"},
    )


async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> User:
    """Resolve the authenticated user from the httpOnly access-token cookie."""
    token = request.cookies.get(_settings.access_cookie_name)
    if not token:
        raise _unauthorized("Not authenticated.")
    try:
        payload = decode_access_token(token)
    except jwt.ExpiredSignatureError as exc:
        raise _unauthorized("Access token expired.") from exc
    except jwt.PyJWTError as exc:
        raise _unauthorized("Invalid access token.") from exc

    try:
        user_id = uuid.UUID(payload["sub"])
    except (KeyError, ValueError) as exc:
        raise _unauthorized("Malformed token subject.") from exc

    user = await db.get(User, user_id)
    if user is None or not user.is_active:
        raise _unauthorized("User not found or inactive.")
    return user


async def get_user_from_api_key(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> User:
    """Resolve the user from an MCP ``Authorization: Bearer <api_key>`` header."""
    header = request.headers.get("authorization", "")
    scheme, _, value = header.partition(" ")
    if scheme.lower() != "bearer" or not value:
        raise _unauthorized("Missing or malformed API key.")

    token_hash = hash_token(value.strip())
    result = await db.execute(
        select(ApiKey).where(
            ApiKey.token_hash == token_hash,
            ApiKey.revoked_at.is_(None),
        )
    )
    api_key = result.scalar_one_or_none()
    if api_key is None:
        raise _unauthorized("Invalid API key.")

    user = await db.get(User, api_key.user_id)
    if user is None or not user.is_active:
        raise _unauthorized("User not found or inactive.")

    api_key.last_used_at = datetime.now(timezone.utc)
    await db.commit()
    return user
