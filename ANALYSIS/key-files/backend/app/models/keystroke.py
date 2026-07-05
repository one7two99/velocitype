from __future__ import annotations

import uuid

from sqlalchemy import BigInteger, Boolean, ForeignKey, Integer, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Keystroke(Base):
    __tablename__ = "keystrokes"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    ts_offset_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    expected_char: Mapped[str] = mapped_column(Text, nullable=False)
    actual_char: Mapped[str] = mapped_column(Text, nullable=False)
    correct: Mapped[bool] = mapped_column(Boolean, nullable=False)
    hold_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)

    session = relationship("TypingSession", back_populates="keystrokes")
