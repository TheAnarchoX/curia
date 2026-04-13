"""Source endpoints."""

from uuid import UUID

from curia_domain.db.models import SourceRow
from curia_domain.enums import SourceType
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.app.dependencies import get_db
from apps.api.app.routers.v1._utils import fetch_one_or_404, fetch_paginated
from apps.api.app.schemas.common import PaginatedResponse
from apps.api.app.schemas.responses import SourceResponse

router = APIRouter(prefix="/sources", tags=["sources"])


@router.get("", response_model=PaginatedResponse[SourceResponse])
async def list_sources(
    source_type: SourceType | None = Query(None, description="Filter by source type"),
    active: bool | None = Query(None, description="Filter by active status"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[SourceResponse]:
    """List all data sources."""
    stmt = select(SourceRow).order_by(SourceRow.name, SourceRow.id)

    if source_type is not None:
        stmt = stmt.where(SourceRow.source_type == source_type)
    if active is not None:
        stmt = stmt.where(SourceRow.active == active)

    return await fetch_paginated(db, stmt, SourceResponse, limit=limit, offset=offset)


@router.get("/{source_id}", response_model=SourceResponse)
async def get_source(
    source_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> SourceResponse:
    """Get a single source by ID."""
    return await fetch_one_or_404(
        db,
        select(SourceRow).where(SourceRow.id == source_id),
        SourceResponse,
        detail="Source not found",
    )
