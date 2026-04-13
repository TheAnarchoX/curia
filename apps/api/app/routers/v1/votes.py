"""Vote endpoints."""

from datetime import date
from uuid import UUID

from curia_domain.db.models import VoteRow
from curia_domain.enums import VoteOutcome
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.app.dependencies import get_db
from apps.api.app.routers.v1._utils import fetch_one_or_404, fetch_paginated
from apps.api.app.schemas.common import PaginatedResponse
from apps.api.app.schemas.responses import VoteResponse

router = APIRouter(prefix="/votes", tags=["votes"])


@router.get("", response_model=PaginatedResponse[VoteResponse])
async def list_votes(
    decision_id: UUID | None = Query(None, description="Filter by decision"),
    proposition_type: str | None = Query(None, description="Filter by proposition type"),
    outcome: VoteOutcome | None = Query(None, description="Filter by vote outcome"),
    date_from: date | None = Query(None, description="Filter by vote date lower bound"),
    date_to: date | None = Query(None, description="Filter by vote date upper bound"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[VoteResponse]:
    """List all votes."""
    stmt = select(VoteRow).order_by(VoteRow.date, VoteRow.id)

    if decision_id is not None:
        stmt = stmt.where(VoteRow.decision_id == decision_id)
    if proposition_type is not None:
        stmt = stmt.where(VoteRow.proposition_type == proposition_type)
    if outcome is not None:
        stmt = stmt.where(VoteRow.outcome == outcome)
    if date_from is not None:
        stmt = stmt.where(VoteRow.date >= date_from)
    if date_to is not None:
        stmt = stmt.where(VoteRow.date <= date_to)

    return await fetch_paginated(db, stmt, VoteResponse, limit=limit, offset=offset)


@router.get("/{vote_id}", response_model=VoteResponse)
async def get_vote(
    vote_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> VoteResponse:
    """Get a single vote by ID."""
    return await fetch_one_or_404(
        db,
        select(VoteRow).where(VoteRow.id == vote_id),
        VoteResponse,
        detail="Vote not found",
    )
