"""JWT (RS256) access tokens + opaque refresh/API-key generation.

Access tokens are short-lived signed JWTs (asymmetric RS256). Refresh tokens are
opaque random strings stored hashed with rotation (Section 2); their JWT-free
design means revocation is a single DB update.
"""
from __future__ import annotations

import secrets
import uuid
from datetime import datetime, timedelta, timezone

import jwt

from app.config import get_settings

_settings = get_settings()

ACCESS_TOKEN_TYPE = "access"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def create_access_token(user_id: uuid.UUID | str, username: str) -> str:
    now = _now()
    payload = {
        "sub": str(user_id),
        "username": username,
        "type": ACCESS_TOKEN_TYPE,
        "iss": _settings.jwt_issuer,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=_settings.access_token_expire_minutes)).timestamp()),
        "jti": secrets.token_hex(8),
    }
    return jwt.encode(payload, _settings.jwt_private_key, algorithm=_settings.jwt_algorithm)


def decode_access_token(token: str) -> dict:
    """Decode & verify an access token. Raises jwt.PyJWTError on any problem."""
    payload = jwt.decode(
        token,
        _settings.jwt_public_key,
        algorithms=[_settings.jwt_algorithm],
        issuer=_settings.jwt_issuer,
        options={"require": ["exp", "iat", "sub"]},
    )
    if payload.get("type") != ACCESS_TOKEN_TYPE:
        raise jwt.InvalidTokenError("wrong token type")
    return payload


def generate_refresh_token() -> str:
    """Opaque, URL-safe, high-entropy refresh token (stored hashed)."""
    return secrets.token_urlsafe(48)


def refresh_expiry() -> datetime:
    return _now() + timedelta(days=_settings.refresh_token_expire_days)


# ── MCP API keys ─────────────────────────────────────────────────────────────
API_KEY_PREFIX = "tf_mcp_"


def generate_api_key() -> tuple[str, str]:
    """Return (full_key, short_prefix). The full key is shown once; only its hash
    is stored. The prefix is a non-secret handle for display and DB lookup."""
    body = secrets.token_urlsafe(32)
    full = f"{API_KEY_PREFIX}{body}"
    prefix = full[: len(API_KEY_PREFIX) + 6]
    return full, prefix
