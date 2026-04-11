"""Institution endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from apps.api.app.dependencies import get_db
from apps.api.app.schemas.common import PaginatedResponse
from apps.api.app.schemas.responses import InstitutionResponse

router = APIRouter(prefix="/institutions", tags=["institutions"])


@router.get("", response_model=PaginatedResponse[InstitutionResponse])
async def list_institutions(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    db=Depends(get_db),
) -> PaginatedResponse[InstitutionResponse]:
    """List all institutions."""
    # TODO: implement real DB query
    return PaginatedResponse[InstitutionResponse].build(items=[], total=0, page=page, page_size=page_size)


@router.get("/{institution_id}", response_model=InstitutionResponse)
async def get_institution(
    institution_id: UUID,
    db=Depends(get_db),
) -> InstitutionResponse:
    """Get a single institution by ID."""
    # TODO: implement real DB query
    raise HTTPException(status_code=404, detail="Institution not found")
