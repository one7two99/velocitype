from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, func, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class UserLayoutProgress(Base):
    """Progressive-unlock state per (user, layout): how many keys of the layout's
    unlock_order are revealed. A large stored value grandfathers existing users to
    'all keys' (clamped at read time)."""
    __tablename__ = "user_layout_progress"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    layout_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    unlocked_count: Mapped[int] = mapped_column(Integer, server_default=text("6"), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    user = relationship("User", back_populates="layout_progress")
