"""Amendment endpoints."""

from datetime import date
from uuid import UUID

from curia_domain.db.models import AmendmentRow
from curia_domain.enums import PropositionStatus
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.app.dependencies import get_db
from apps.api.app.routers.v1._utils import fetch_one_or_404, fetch_paginated
from apps.api.app.schemas.common import PaginatedResponse
from apps.api.app.schemas.responses import AmendmentResponse

router = APIRouter(prefix="/amendments", tags=["amendments"])


@router.get("", response_model=PaginatedResponse[AmendmentResponse])
async def list_amendments(
    meeting_id: UUID | None = Query(None, description="Filter by meeting"),
    target_document_id: UUID | None = Query(None, description="Filter by target document"),
    status: PropositionStatus | None = Query(None, description="Filter by amendment status"),
    submitted_from: date | None = Query(None, description="Filter by submitted date lower bound"),
    submitted_to: date | None = Query(None, description="Filter by submitted date upper bound"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[AmendmentResponse]:
    """List all amendments."""
    stmt = select(AmendmentRow).order_by(AmendmentRow.submitted_date, AmendmentRow.id)

    if meeting_id is not None:
        stmt = stmt.where(AmendmentRow.meeting_id == meeting_id)
    if target_document_id is not None:
        stmt = stmt.where(AmendmentRow.target_document_id == target_document_id)
    if status is not None:
        stmt = stmt.where(AmendmentRow.status == status)
    if submitted_from is not None:
        stmt = stmt.where(AmendmentRow.submitted_date >= submitted_from)
    if submitted_to is not None:
        stmt = stmt.where(AmendmentRow.submitted_date <= submitted_to)

    return await fetch_paginated(db, stmt, AmendmentResponse, limit=limit, offset=offset)


@router.get("/{amendment_id}", response_model=AmendmentResponse)
async def get_amendment(
    amendment_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> AmendmentResponse:
    """Get a single amendment by ID."""
    return await fetch_one_or_404(
        db,
        select(AmendmentRow).where(AmendmentRow.id == amendment_id),
        AmendmentResponse,
        detail="Amendment not found",
    )
