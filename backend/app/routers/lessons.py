"""Lessons router: next adaptive lesson + available layouts (Section 4)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.db.session import get_db
from app.engine.layouts import DEFAULT_LAYOUT_ID, get_layout
from app.errors import ProblemException
from app.models.layout import Layout
from app.models.user import User
from app.schemas.lesson import LayoutInfo, LayoutList, NextLessonResponse
from app.services.lessons import generate_adaptive_lesson

router = APIRouter(prefix="/api/lessons", tags=["lessons"])


@router.get("/next", response_model=NextLessonResponse)
async def next_lesson(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    layout_id: str = Query(default=DEFAULT_LAYOUT_ID, max_length=64),
) -> NextLessonResponse:
    if get_layout(layout_id) is None:
        raise ProblemException(
            status_code=422, title="Unprocessable Entity",
            detail=f"Unknown layout '{layout_id}'.", type_="about:unknown-layout",
        )
    lesson, weak = await generate_adaptive_lesson(db, user.id, layout_id)
    return NextLessonResponse(
        layout_id=layout_id,
        lesson=lesson,
        weak_keys=weak,
        word_count=len(lesson.split()),
    )


@router.get("/layouts", response_model=LayoutList)
async def available_layouts(db: AsyncSession = Depends(get_db)) -> LayoutList:
    """Served from the seeded ``layouts`` table."""
    result = await db.execute(select(Layout).order_by(Layout.id))
    layouts = [
        LayoutInfo(
            id=row.id,
            name=row.name,
            hand_map=row.hand_map,
            finger_map=row.finger_map,
            thumb_keys=row.thumb_keys,
        )
        for row in result.scalars().all()
    ]
    return LayoutList(layouts=layouts)
