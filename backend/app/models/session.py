from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, func, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class TypingSession(Base):
    """A single practice session. Table name is ``sessions`` per Section 3;
    the Python class is ``TypingSession`` to avoid clashing with DB sessions."""
    __tablename__ = "sessions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    layout_id: Mapped[str] = mapped_column(String(64), nullable=False)
    mode: Mapped[str] = mapped_column(String(32), nullable=False)  # adaptive|fixed_text|custom
    duration_s: Mapped[int | None] = mapped_column(Integer, nullable=True)
    word_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    wpm_raw: Mapped[Decimal | None] = mapped_column(Numeric(6, 2), nullable=True)
    wpm_net: Mapped[Decimal | None] = mapped_column(Numeric(6, 2), nullable=True)
    accuracy: Mapped[Decimal | None] = mapped_column(Numeric(5, 4), nullable=True)
    consistency: Mapped[Decimal | None] = mapped_column(Numeric(5, 4), nullable=True)

    user = relationship("User", back_populates="sessions")
    keystrokes = relationship(
        "Keystroke", back_populates="session", cascade="all, delete-orphan"
    )
