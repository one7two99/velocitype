from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, func, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class UserSettings(Base):
    """Per-user UI/training preferences, synced across the user's browsers.
    One row per user; created on first save. Defaults mirror the frontend store."""
    __tablename__ = "user_settings"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    theme: Mapped[str] = mapped_column(String(16), server_default="system", nullable=False)
    layout_id: Mapped[str] = mapped_column(
        String(64), server_default="ferris_sweep_colemak_dh", nullable=False
    )
    goal: Mapped[str] = mapped_column(String(16), server_default="time", nullable=False)
    duration_s: Mapped[int] = mapped_column(Integer, server_default=text("60"), nullable=False)
    word_count: Mapped[int] = mapped_column(Integer, server_default=text("25"), nullable=False)
    target_wpm: Mapped[int] = mapped_column(Integer, server_default=text("40"), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    user = relationship("User", back_populates="settings")
