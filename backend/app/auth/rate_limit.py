"""Per-IP fixed-window rate limiting backed by Redis (Section 2).

Used as a FastAPI dependency factory:  Depends(rate_limiter("login", limit=5)).
Fails closed only for the limit check itself; if Redis is unreachable we log and
allow the request rather than lock users out (availability over strictness for a
rate limiter — the auth checks themselves still apply).
"""
from __future__ import annotations

from fastapi import Depends, Request

from app.config import get_settings
from app.db.redis import get_redis
from app.errors import ProblemException

_settings = get_settings()


def _client_ip(request: Request) -> str:
    # Caddy sets X-Forwarded-For; take the first hop. Fall back to peer address.
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def rate_limiter(bucket: str, limit: int, window_s: int | None = None):
    window = window_s or _settings.rate_limit_window_s

    async def _dependency(request: Request, redis=Depends(get_redis)) -> None:
        ip = _client_ip(request)
        key = f"ratelimit:{bucket}:{ip}"
        try:
            current = await redis.incr(key)
            if current == 1:
                await redis.expire(key, window)
        except Exception:
            # Redis down — do not block auth entirely.
            return
        if current > limit:
            ttl = await redis.ttl(key)
            raise ProblemException(
                status_code=429,
                title="Too Many Requests",
                detail=f"Rate limit exceeded. Try again in {max(ttl, 1)}s.",
                type_="about:rate-limit",
                headers={"Retry-After": str(max(ttl, 1))},
            )

    return _dependency
