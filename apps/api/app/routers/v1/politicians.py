"""Politician endpoints."""

from uuid import UUID

from curia_domain.db.models import PoliticianRow
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.app.dependencies import get_db
from apps.api.app.routers.v1._utils import fetch_one_or_404, fetch_paginated
from apps.api.app.schemas.common import PaginatedResponse
from apps.api.app.schemas.responses import PoliticianResponse

router = APIRouter(prefix="/politicians", tags=["politicians"])


@router.get("", response_model=PaginatedResponse[PoliticianResponse])
async def list_politicians(
    full_name: str | None = Query(None, description="Filter by full name"),
    family_name: str | None = Query(None, description="Filter by family name"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[PoliticianResponse]:
    """List all politicians."""
    stmt = select(PoliticianRow).order_by(PoliticianRow.full_name, PoliticianRow.id)

    if full_name is not None:
        stmt = stmt.where(PoliticianRow.full_name.ilike(f"%{full_name}%"))
    if family_name is not None:
        stmt = stmt.where(PoliticianRow.family_name.ilike(f"%{family_name}%"))

    return await fetch_paginated(db, stmt, PoliticianResponse, limit=limit, offset=offset)


@router.get("/{politician_id}", response_model=PoliticianResponse)
async def get_politician(
    politician_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> PoliticianResponse:
    """Get a single politician by ID."""
    return await fetch_one_or_404(
        db,
        select(PoliticianRow).where(PoliticianRow.id == politician_id),
        PoliticianResponse,
        detail="Politician not found",
    )
