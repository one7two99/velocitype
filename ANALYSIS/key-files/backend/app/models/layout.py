from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Layout(Base):
    """Keyboard layout definition. Seeded from ``app.engine.layouts`` on startup
    and served by ``GET /api/lessons/layouts`` (instruction l).

    Not one of the five Section 3 tables — added so layout definitions have a
    queryable home as the seed script requires.
    """
    __tablename__ = "layouts"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    hand_map: Mapped[dict] = mapped_column(JSONB, nullable=False)
    finger_map: Mapped[dict] = mapped_column(JSONB, nullable=False)
    thumb_keys: Mapped[list] = mapped_column(JSONB, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
