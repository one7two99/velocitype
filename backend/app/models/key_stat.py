from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, func, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class KeyStat(Base):
    """Aggregated per-(user, layout, character) performance, updated after each
    session. Composite primary key per Section 3."""
    __tablename__ = "key_stats"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    layout_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    character: Mapped[str] = mapped_column(String(8), primary_key=True)
    attempts: Mapped[int] = mapped_column(Integer, server_default=text("0"), nullable=False)
    errors: Mapped[int] = mapped_column(Integer, server_default=text("0"), nullable=False)
    avg_latency_ms: Mapped[Decimal | None] = mapped_column(Numeric(8, 2), nullable=True)
    # Bookkeeping for the recency term of the adaptive score (Section 5).
    last_session_seq: Mapped[int] = mapped_column(Integer, server_default=text("0"), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    user = relationship("User", back_populates="key_stats")
