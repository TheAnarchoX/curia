"""Promise endpoints."""

from datetime import date
from uuid import UUID

from curia_domain.db.models import PromiseRow
from curia_domain.enums import PropositionStatus
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.app.dependencies import get_db
from apps.api.app.routers.v1._utils import fetch_one_or_404, fetch_paginated
from apps.api.app.schemas.common import PaginatedResponse
from apps.api.app.schemas.responses import PromiseResponse

router = APIRouter(prefix="/promises", tags=["promises"])


@router.get("", response_model=PaginatedResponse[PromiseResponse])
async def list_promises(
    maker_id: UUID | None = Query(None, description="Filter by maker"),
    meeting_id: UUID | None = Query(None, description="Filter by meeting"),
    status: PropositionStatus | None = Query(None, description="Filter by promise status"),
    made_from: date | None = Query(None, description="Filter by made date lower bound"),
    made_to: date | None = Query(None, description="Filter by made date upper bound"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[PromiseResponse]:
    """List all promises."""
    stmt = select(PromiseRow).order_by(PromiseRow.made_date, PromiseRow.id)

    if maker_id is not None:
        stmt = stmt.where(PromiseRow.maker_id == maker_id)
    if meeting_id is not None:
        stmt = stmt.where(PromiseRow.meeting_id == meeting_id)
    if status is not None:
        stmt = stmt.where(PromiseRow.status == status)
    if made_from is not None:
        stmt = stmt.where(PromiseRow.made_date >= made_from)
    if made_to is not None:
        stmt = stmt.where(PromiseRow.made_date <= made_to)

    return await fetch_paginated(db, stmt, PromiseResponse, limit=limit, offset=offset)


@router.get("/{promise_id}", response_model=PromiseResponse)
async def get_promise(
    promise_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> PromiseResponse:
    """Get a single promise by ID."""
    return await fetch_one_or_404(
        db,
        select(PromiseRow).where(PromiseRow.id == promise_id),
        PromiseResponse,
        detail="Promise not found",
    )
