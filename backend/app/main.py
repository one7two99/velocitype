"""Velocitype API application factory."""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.db.redis import redis_client
from app.db.session import engine
from app.errors import register_exception_handlers
from app.routers import auth, coach, keystrokes, lessons, mcp, sessions, stats
from app.version import __version__

_settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    # Graceful shutdown of pooled connections.
    await engine.dispose()
    try:
        await redis_client.aclose()
    except Exception:
        pass


def create_app() -> FastAPI:
    app = FastAPI(
        title="Velocitype API",
        version=__version__,
        description="Adaptive touch-typing trainer for split keyboards.",
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
        redoc_url=None,
        lifespan=lifespan,
    )

    # CORS — explicit allowlist, credentials enabled for cookie auth (Section 2).
    if _settings.cors_origin_list:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=_settings.cors_origin_list,
            allow_credentials=True,
            allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            allow_headers=["Authorization", "Content-Type"],
        )

    register_exception_handlers(app)

    health = APIRouter(tags=["health"])

    @health.get("/api/health")
    async def healthcheck() -> dict:
        return {"status": "ok", "version": __version__}

    @health.get("/api/version")
    async def version() -> dict:
        return {"version": __version__}

    app.include_router(health)
    app.include_router(auth.router)
    app.include_router(sessions.router)
    app.include_router(keystrokes.router)
    app.include_router(stats.router)
    app.include_router(lessons.router)
    app.include_router(mcp.router)
    app.include_router(coach.router)

    return app


app = create_app()
