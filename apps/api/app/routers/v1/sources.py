"""Source endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from apps.api.app.dependencies import get_db
from apps.api.app.schemas.common import PaginatedResponse
from apps.api.app.schemas.responses import SourceResponse

router = APIRouter(prefix="/sources", tags=["sources"])


@router.get("", response_model=PaginatedResponse[SourceResponse])
async def list_sources(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    db=Depends(get_db),
) -> PaginatedResponse[SourceResponse]:
    """List all data sources."""
    # TODO: implement real DB query
    return PaginatedResponse[SourceResponse].build(items=[], total=0, page=page, page_size=page_size)


@router.get("/{source_id}", response_model=SourceResponse)
async def get_source(
    source_id: UUID,
    db=Depends(get_db),
) -> SourceResponse:
    """Get a single source by ID."""
    # TODO: implement real DB query
    raise HTTPException(status_code=404, detail="Source not found")
