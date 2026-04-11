"""Amendment endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from apps.api.app.dependencies import get_db
from apps.api.app.schemas.common import PaginatedResponse
from apps.api.app.schemas.responses import AmendmentResponse

router = APIRouter(prefix="/amendments", tags=["amendments"])


@router.get("", response_model=PaginatedResponse[AmendmentResponse])
async def list_amendments(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    db=Depends(get_db),
) -> PaginatedResponse[AmendmentResponse]:
    """List all amendments."""
    # TODO: implement real DB query
    return PaginatedResponse[AmendmentResponse].build(items=[], total=0, page=page, page_size=page_size)


@router.get("/{amendment_id}", response_model=AmendmentResponse)
async def get_amendment(
    amendment_id: UUID,
    db=Depends(get_db),
) -> AmendmentResponse:
    """Get a single amendment by ID."""
    # TODO: implement real DB query
    raise HTTPException(status_code=404, detail="Amendment not found")
