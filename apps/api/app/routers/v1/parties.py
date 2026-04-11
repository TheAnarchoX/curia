"""Party endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from apps.api.app.dependencies import get_db
from apps.api.app.schemas.common import PaginatedResponse
from apps.api.app.schemas.responses import PartyResponse

router = APIRouter(prefix="/parties", tags=["parties"])


@router.get("", response_model=PaginatedResponse[PartyResponse])
async def list_parties(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    db=Depends(get_db),
) -> PaginatedResponse[PartyResponse]:
    """List all parties."""
    # TODO: implement real DB query
    return PaginatedResponse[PartyResponse].build(items=[], total=0, page=page, page_size=page_size)


@router.get("/{party_id}", response_model=PartyResponse)
async def get_party(
    party_id: UUID,
    db=Depends(get_db),
) -> PartyResponse:
    """Get a single party by ID."""
    # TODO: implement real DB query
    raise HTTPException(status_code=404, detail="Party not found")
