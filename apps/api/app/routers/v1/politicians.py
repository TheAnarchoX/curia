"""Politician endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from apps.api.app.dependencies import get_db
from apps.api.app.schemas.common import PaginatedResponse
from apps.api.app.schemas.responses import PoliticianResponse

router = APIRouter(prefix="/politicians", tags=["politicians"])


@router.get("", response_model=PaginatedResponse[PoliticianResponse])
async def list_politicians(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    db=Depends(get_db),
) -> PaginatedResponse[PoliticianResponse]:
    """List all politicians."""
    # TODO: implement real DB query
    return PaginatedResponse[PoliticianResponse].build(
        items=[], total=0, page=page, page_size=page_size
    )


@router.get("/{politician_id}", response_model=PoliticianResponse)
async def get_politician(
    politician_id: UUID,
    db=Depends(get_db),
) -> PoliticianResponse:
    """Get a single politician by ID."""
    # TODO: implement real DB query
    raise HTTPException(status_code=404, detail="Politician not found")
