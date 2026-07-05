from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class UserAiConfig(Base):
    """Per-user AI provider configuration. NULL model fields fall back to the
    deployment defaults; ``mistral_api_key_enc`` holds the Fernet-encrypted key."""
    __tablename__ = "user_ai_config"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    provider: Mapped[str] = mapped_column(String(16), nullable=False, default="ollama")
    ollama_model: Mapped[str | None] = mapped_column(String(128), nullable=True)
    mistral_model: Mapped[str | None] = mapped_column(String(128), nullable=True)
    mistral_api_key_enc: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    user = relationship("User", back_populates="ai_config")
