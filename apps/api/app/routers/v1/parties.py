"""Party endpoints."""

from datetime import date
from uuid import UUID

from curia_domain.db.models import PartyRow
from curia_domain.enums import JurisdictionLevel
from fastapi import APIRouter, Depends, Query
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.app.dependencies import get_db
from apps.api.app.routers.v1._utils import fetch_one_or_404, fetch_paginated
from apps.api.app.schemas.common import PaginatedResponse
from apps.api.app.schemas.responses import PartyResponse

router = APIRouter(prefix="/parties", tags=["parties"])


@router.get("", response_model=PaginatedResponse[PartyResponse])
async def list_parties(
    name: str | None = Query(None, description="Filter by party name"),
    abbreviation: str | None = Query(None, description="Filter by abbreviation"),
    scope_level: JurisdictionLevel | None = Query(None, description="Filter by scope level"),
    active_on: date | None = Query(None, description="Filter by an active date"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[PartyResponse]:
    """List all parties."""
    stmt = select(PartyRow).order_by(PartyRow.name, PartyRow.id)

    if name is not None:
        stmt = stmt.where(PartyRow.name.ilike(f"%{name}%"))
    if abbreviation is not None:
        stmt = stmt.where(PartyRow.abbreviation == abbreviation)
    if scope_level is not None:
        stmt = stmt.where(PartyRow.scope_level == scope_level)
    if active_on is not None:
        stmt = stmt.where(or_(PartyRow.active_from.is_(None), PartyRow.active_from <= active_on))
        stmt = stmt.where(or_(PartyRow.active_until.is_(None), PartyRow.active_until >= active_on))

    return await fetch_paginated(db, stmt, PartyResponse, limit=limit, offset=offset)


@router.get("/{party_id}", response_model=PartyResponse)
async def get_party(
    party_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> PartyResponse:
    """Get a single party by ID."""
    return await fetch_one_or_404(
        db,
        select(PartyRow).where(PartyRow.id == party_id),
        PartyResponse,
        detail="Party not found",
    )
