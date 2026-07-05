"""Test fixtures.

- Generates an ephemeral RS256 keypair and sets required env vars BEFORE the app
  package is imported, so config/db modules initialise cleanly.
- Integration fixtures target a Postgres test database (TEST_DATABASE_URL, or a
  localhost default). If it is unreachable, the dependent tests skip rather than
  fail — keeping the suite runnable anywhere while remaining real when a DB is
  present (e.g. in CI / `docker compose up`).
"""
from __future__ import annotations

import os
import tempfile
import uuid

import pytest

# ── Environment must be set before importing the app ─────────────────────────
_TMP = tempfile.mkdtemp(prefix="tf-test-")
_PRIV = os.path.join(_TMP, "jwt_private.pem")
_PUB = os.path.join(_TMP, "jwt_public.pem")


def _write_keys() -> None:
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import rsa

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    with open(_PRIV, "wb") as f:
        f.write(
            key.private_bytes(
                serialization.Encoding.PEM,
                serialization.PrivateFormat.PKCS8,
                serialization.NoEncryption(),
            )
        )
    with open(_PUB, "wb") as f:
        f.write(
            key.public_key().public_bytes(
                serialization.Encoding.PEM,
                serialization.PublicFormat.SubjectPublicKeyInfo,
            )
        )


_write_keys()

TEST_DB_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://velocitype_app:dev_app_change_me@localhost:5432/velocitype",
)
os.environ.setdefault("ENV", "development")
os.environ["DATABASE_URL"] = TEST_DB_URL
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/15")
os.environ["JWT_PRIVATE_KEY_PATH"] = _PRIV
os.environ["JWT_PUBLIC_KEY_PATH"] = _PUB
os.environ["COOKIE_SECURE"] = "false"
os.environ.setdefault("CORS_ORIGINS", "http://localhost")


@pytest.fixture
async def db_available() -> bool:
    """True if the test Postgres is reachable; otherwise skip the test."""
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import create_async_engine

    engine = create_async_engine(TEST_DB_URL)
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception as exc:  # noqa: BLE001
        pytest.skip(f"Test database unreachable: {exc}")
    finally:
        await engine.dispose()
    return True


@pytest.fixture
async def client(db_available):
    """httpx AsyncClient bound to the ASGI app against a schema-created test DB.

    The app's engine/redis clients are module-level singletons; pytest-asyncio
    runs each test in a fresh event loop, so we reset their connection pools
    within the test's own loop (avoiding 'event loop is closed') and flush the
    rate-limit keyspace so per-test request counts start clean.
    """
    from httpx import ASGITransport, AsyncClient

    from app.db.redis import redis_client
    from app.db.session import engine
    from app.main import app
    from app.models import Base

    try:
        await redis_client.flushdb()
    except Exception:
        pass  # rate limiting fails open; tests here don't depend on Redis

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    await engine.dispose()
    try:
        await redis_client.connection_pool.disconnect()
    except Exception:
        pass


@pytest.fixture
def unique_user() -> dict:
    tag = uuid.uuid4().hex[:8]
    return {
        "username": f"user_{tag}",
        "email": f"user_{tag}@example.com",
        "password": "correct-horse-battery",  # >= 12 chars
    }
