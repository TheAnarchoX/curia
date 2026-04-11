"""Vote endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from apps.api.app.dependencies import get_db
from apps.api.app.schemas.common import PaginatedResponse
from apps.api.app.schemas.responses import VoteResponse

router = APIRouter(prefix="/votes", tags=["votes"])


@router.get("", response_model=PaginatedResponse[VoteResponse])
async def list_votes(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    db=Depends(get_db),
) -> PaginatedResponse[VoteResponse]:
    """List all votes."""
    # TODO: implement real DB query
    return PaginatedResponse[VoteResponse].build(items=[], total=0, page=page, page_size=page_size)


@router.get("/{vote_id}", response_model=VoteResponse)
async def get_vote(
    vote_id: UUID,
    db=Depends(get_db),
) -> VoteResponse:
    """Get a single vote by ID."""
    # TODO: implement real DB query
    raise HTTPException(status_code=404, detail="Vote not found")
