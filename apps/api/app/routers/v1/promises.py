"""Promise endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from apps.api.app.dependencies import get_db
from apps.api.app.schemas.common import PaginatedResponse
from apps.api.app.schemas.responses import PromiseResponse

router = APIRouter(prefix="/promises", tags=["promises"])


@router.get("", response_model=PaginatedResponse[PromiseResponse])
async def list_promises(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    db=Depends(get_db),
) -> PaginatedResponse[PromiseResponse]:
    """List all promises."""
    # TODO: implement real DB query
    return PaginatedResponse[PromiseResponse].build(items=[], total=0, page=page, page_size=page_size)


@router.get("/{promise_id}", response_model=PromiseResponse)
async def get_promise(
    promise_id: UUID,
    db=Depends(get_db),
) -> PromiseResponse:
    """Get a single promise by ID."""
    # TODO: implement real DB query
    raise HTTPException(status_code=404, detail="Promise not found")
