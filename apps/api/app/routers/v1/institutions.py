"""Institution endpoints."""

from uuid import UUID

from curia_domain.db.models import InstitutionRow
from curia_domain.enums import InstitutionType
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.app.dependencies import get_db
from apps.api.app.routers.v1._utils import fetch_one_or_404, fetch_paginated
from apps.api.app.schemas.common import PaginatedResponse
from apps.api.app.schemas.responses import InstitutionResponse

router = APIRouter(prefix="/institutions", tags=["institutions"])


@router.get("", response_model=PaginatedResponse[InstitutionResponse])
async def list_institutions(
    jurisdiction_id: UUID | None = Query(None, description="Filter by jurisdiction"),
    institution_type: InstitutionType | None = Query(None, description="Filter by institution type"),
    slug: str | None = Query(None, description="Filter by slug"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[InstitutionResponse]:
    """List all institutions."""
    stmt = select(InstitutionRow).order_by(InstitutionRow.name, InstitutionRow.id)

    if jurisdiction_id is not None:
        stmt = stmt.where(InstitutionRow.jurisdiction_id == jurisdiction_id)
    if institution_type is not None:
        stmt = stmt.where(InstitutionRow.institution_type == institution_type)
    if slug is not None:
        stmt = stmt.where(InstitutionRow.slug == slug)

    return await fetch_paginated(db, stmt, InstitutionResponse, limit=limit, offset=offset)


@router.get("/{institution_id}", response_model=InstitutionResponse)
async def get_institution(
    institution_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> InstitutionResponse:
    """Get a single institution by ID."""
    return await fetch_one_or_404(
        db,
        select(InstitutionRow).where(InstitutionRow.id == institution_id),
        InstitutionResponse,
        detail="Institution not found",
    )
