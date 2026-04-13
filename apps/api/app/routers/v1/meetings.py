"""Meeting endpoints."""

from datetime import UTC, date, datetime, time, timedelta
from uuid import UUID

from curia_domain.db.models import GoverningBodyRow, MeetingRow
from curia_domain.enums import MeetingStatus
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.app.dependencies import get_db
from apps.api.app.routers.v1._utils import fetch_one_or_404, fetch_paginated
from apps.api.app.schemas.common import PaginatedResponse
from apps.api.app.schemas.responses import MeetingResponse

router = APIRouter(prefix="/meetings", tags=["meetings"])


@router.get("", response_model=PaginatedResponse[MeetingResponse])
async def list_meetings(
    governing_body_id: UUID | None = Query(None, description="Filter by governing body"),
    institution_id: UUID | None = Query(None, description="Filter by institution"),
    status: MeetingStatus | None = Query(None, description="Filter by meeting status"),
    start_date_from: date | None = Query(None, description="Filter by start date lower bound"),
    start_date_to: date | None = Query(None, description="Filter by start date upper bound"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[MeetingResponse]:
    """List all meetings."""
    stmt = select(MeetingRow).order_by(MeetingRow.scheduled_start, MeetingRow.id)

    if institution_id is not None:
        stmt = stmt.join(GoverningBodyRow, MeetingRow.governing_body_id == GoverningBodyRow.id).where(
            GoverningBodyRow.institution_id == institution_id
        )
    if governing_body_id is not None:
        stmt = stmt.where(MeetingRow.governing_body_id == governing_body_id)
    if status is not None:
        stmt = stmt.where(MeetingRow.status == status)
    if start_date_from is not None:
        start_datetime_from = datetime.combine(start_date_from, time.min, tzinfo=UTC)
        stmt = stmt.where(MeetingRow.scheduled_start >= start_datetime_from)
    if start_date_to is not None:
        start_datetime_to = datetime.combine(
            start_date_to + timedelta(days=1),
            time.min,
            tzinfo=UTC,
        )
        stmt = stmt.where(MeetingRow.scheduled_start < start_datetime_to)

    return await fetch_paginated(db, stmt, MeetingResponse, limit=limit, offset=offset)


@router.get("/{meeting_id}", response_model=MeetingResponse)
async def get_meeting(
    meeting_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> MeetingResponse:
    """Get a single meeting by ID."""
    return await fetch_one_or_404(
        db,
        select(MeetingRow).where(MeetingRow.id == meeting_id),
        MeetingResponse,
        detail="Meeting not found",
    )
