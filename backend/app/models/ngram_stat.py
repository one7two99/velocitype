from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Float, ForeignKey, Integer, Numeric, String, func, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class NgramStat(Base):
    """Aggregated per-(user, layout, ngram) performance. Mirrors ``key_stats``
    field-for-field so the online mean/variance and recency math are identical
    (design: docs/NGRAM_METRIC_MODEL.md §3). v1 persists bigrams (n=2); trigrams
    are derived on read."""
    __tablename__ = "ngram_stats"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    layout_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    ngram: Mapped[str] = mapped_column(String(8), primary_key=True)  # e.g. "sr"
    n: Mapped[int] = mapped_column(Integer, server_default=text("2"), nullable=False)

    attempts: Mapped[int] = mapped_column(Integer, server_default=text("0"), nullable=False)
    errors: Mapped[int] = mapped_column(Integer, server_default=text("0"), nullable=False)

    # Transition-time (IKI) aggregate → mean + spread → rhythm consistency.
    # Identical running-stats shape as key_stats.
    avg_latency_ms: Mapped[Decimal | None] = mapped_column(Numeric(8, 2), nullable=True)
    latency_n: Mapped[int] = mapped_column(Integer, server_default=text("0"), nullable=False)
    latency_sq_sum: Mapped[float] = mapped_column(Float, server_default=text("0"), nullable=False)

    # "Rhythm break" counter: correct-pair transitions whose IKI blew past this
    # ngram's running mean at ingest time. rate = hitch_n / latency_n.
    hitch_n: Mapped[int] = mapped_column(Integer, server_default=text("0"), nullable=False)

    last_session_seq: Mapped[int] = mapped_column(Integer, server_default=text("0"), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    user = relationship("User", back_populates="ngram_stats")
