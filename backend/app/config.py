"""Application configuration via pydantic-settings.

All values come from the environment (Section 2: secrets via env only). JWT keys
are read from PEM files on disk (mounted as Docker secrets in production).
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", case_sensitive=False)

    env: str = Field(default="production")

    # ── Datastores ──────────────────────────────────────────────────────────
    database_url: str = Field(..., description="postgresql+asyncpg://...")
    redis_url: str = Field(..., description="redis://:pass@host:6379/0")

    # ── JWT (RS256, asymmetric) ─────────────────────────────────────────────
    jwt_private_key_path: str = Field(default="/run/secrets/jwt_private")
    jwt_public_key_path: str = Field(default="/run/secrets/jwt_public")
    jwt_algorithm: str = Field(default="RS256")
    jwt_issuer: str = Field(default="typeforge")
    access_token_expire_minutes: int = Field(default=15)
    refresh_token_expire_days: int = Field(default=30)

    # ── Cookies ─────────────────────────────────────────────────────────────
    cookie_secure: bool = Field(default=True)
    cookie_domain: str | None = Field(default=None)
    cookie_samesite: str = Field(default="strict")
    access_cookie_name: str = Field(default="tf_access")
    refresh_cookie_name: str = Field(default="tf_refresh")

    # ── CORS ────────────────────────────────────────────────────────────────
    cors_origins: str = Field(default="")

    # ── Rate limits (per IP) ────────────────────────────────────────────────
    rate_limit_login: int = Field(default=5)      # per minute
    rate_limit_register: int = Field(default=3)   # per minute
    rate_limit_window_s: int = Field(default=60)

    # ── Adaptive engine window ──────────────────────────────────────────────
    adaptive_session_window: int = Field(default=10)

    # ── Ollama (local LLM coaching) ─────────────────────────────────────────
    ollama_base_url: str = Field(default="http://ollama:11434")
    ollama_model: str = Field(default="qwen3.5:4b")
    ollama_timeout_s: float = Field(default=240.0)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_dev(self) -> bool:
        return self.env.lower() in {"dev", "development", "local"}

    @property
    def jwt_private_key(self) -> str:
        return _read_key(self.jwt_private_key_path)

    @property
    def jwt_public_key(self) -> str:
        return _read_key(self.jwt_public_key_path)


def _read_key(path: str) -> str:
    p = Path(path)
    if not p.exists():
        raise RuntimeError(
            f"JWT key not found at {path}. Run ./secrets/keygen.sh before starting."
        )
    return p.read_text()


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
