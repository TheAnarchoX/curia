"""Motion endpoints."""

from datetime import date
from uuid import UUID

from curia_domain.db.models import MotionRow
from curia_domain.enums import PropositionStatus
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.app.dependencies import get_db
from apps.api.app.routers.v1._utils import fetch_one_or_404, fetch_paginated
from apps.api.app.schemas.common import PaginatedResponse
from apps.api.app.schemas.responses import MotionResponse

router = APIRouter(prefix="/motions", tags=["motions"])


@router.get("", response_model=PaginatedResponse[MotionResponse])
async def list_motions(
    meeting_id: UUID | None = Query(None, description="Filter by meeting"),
    agenda_item_id: UUID | None = Query(None, description="Filter by agenda item"),
    status: PropositionStatus | None = Query(None, description="Filter by motion status"),
    submitted_from: date | None = Query(None, description="Filter by submitted date lower bound"),
    submitted_to: date | None = Query(None, description="Filter by submitted date upper bound"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[MotionResponse]:
    """List all motions."""
    stmt = select(MotionRow).order_by(MotionRow.submitted_date, MotionRow.id)

    if meeting_id is not None:
        stmt = stmt.where(MotionRow.meeting_id == meeting_id)
    if agenda_item_id is not None:
        stmt = stmt.where(MotionRow.agenda_item_id == agenda_item_id)
    if status is not None:
        stmt = stmt.where(MotionRow.status == status)
    if submitted_from is not None:
        stmt = stmt.where(MotionRow.submitted_date >= submitted_from)
    if submitted_to is not None:
        stmt = stmt.where(MotionRow.submitted_date <= submitted_to)

    return await fetch_paginated(db, stmt, MotionResponse, limit=limit, offset=offset)


@router.get("/{motion_id}", response_model=MotionResponse)
async def get_motion(
    motion_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> MotionResponse:
    """Get a single motion by ID."""
    return await fetch_one_or_404(
        db,
        select(MotionRow).where(MotionRow.id == motion_id),
        MotionResponse,
        detail="Motion not found",
    )
