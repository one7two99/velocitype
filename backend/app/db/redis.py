"""Async Redis client (rate limiting + short-lived session state)."""
from __future__ import annotations

from collections.abc import AsyncGenerator

import redis.asyncio as redis

from app.config import get_settings

_settings = get_settings()

# decode_responses=True → str in/out; fine for our counters and small values.
redis_client: redis.Redis = redis.from_url(
    _settings.redis_url,
    encoding="utf-8",
    decode_responses=True,
)


async def get_redis() -> AsyncGenerator[redis.Redis, None]:
    yield redis_client
