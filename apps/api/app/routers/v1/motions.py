"""Motion endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from apps.api.app.dependencies import get_db
from apps.api.app.schemas.common import PaginatedResponse
from apps.api.app.schemas.responses import MotionResponse

router = APIRouter(prefix="/motions", tags=["motions"])


@router.get("", response_model=PaginatedResponse[MotionResponse])
async def list_motions(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    db=Depends(get_db),
) -> PaginatedResponse[MotionResponse]:
    """List all motions."""
    # TODO: implement real DB query
    return PaginatedResponse[MotionResponse].build(items=[], total=0, page=page, page_size=page_size)


@router.get("/{motion_id}", response_model=MotionResponse)
async def get_motion(
    motion_id: UUID,
    db=Depends(get_db),
) -> MotionResponse:
    """Get a single motion by ID."""
    # TODO: implement real DB query
    raise HTTPException(status_code=404, detail="Motion not found")
