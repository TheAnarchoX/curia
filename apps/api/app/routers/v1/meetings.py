"""Meeting endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from apps.api.app.dependencies import get_db
from apps.api.app.schemas.common import PaginatedResponse
from apps.api.app.schemas.responses import MeetingResponse

router = APIRouter(prefix="/meetings", tags=["meetings"])


@router.get("", response_model=PaginatedResponse[MeetingResponse])
async def list_meetings(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    db=Depends(get_db),
) -> PaginatedResponse[MeetingResponse]:
    """List all meetings."""
    # TODO: implement real DB query
    return PaginatedResponse[MeetingResponse].build(
        items=[], total=0, page=page, page_size=page_size
    )


@router.get("/{meeting_id}", response_model=MeetingResponse)
async def get_meeting(
    meeting_id: UUID,
    db=Depends(get_db),
) -> MeetingResponse:
    """Get a single meeting by ID."""
    # TODO: implement real DB query
    raise HTTPException(status_code=404, detail="Meeting not found")
