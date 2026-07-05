from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class UserPrompt(Base):
    """Per-user overrides for the AI-coach prompts. A NULL field means "use the
    built-in default"."""
    __tablename__ = "user_prompts"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    analysis_system: Mapped[str | None] = mapped_column(Text, nullable=True)
    analysis_user: Mapped[str | None] = mapped_column(Text, nullable=True)
    drill_system: Mapped[str | None] = mapped_column(Text, nullable=True)
    drill_user: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    user = relationship("User", back_populates="prompts")
