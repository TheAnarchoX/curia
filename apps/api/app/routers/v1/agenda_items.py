"""Agenda-item endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from apps.api.app.dependencies import get_db
from apps.api.app.schemas.common import PaginatedResponse
from apps.api.app.schemas.responses import AgendaItemResponse

router = APIRouter(prefix="/agenda-items", tags=["agenda-items"])


@router.get("", response_model=PaginatedResponse[AgendaItemResponse])
async def list_agenda_items(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    db=Depends(get_db),
) -> PaginatedResponse[AgendaItemResponse]:
    """List all agenda items."""
    # TODO: implement real DB query
    return PaginatedResponse[AgendaItemResponse].build(
        items=[], total=0, page=page, page_size=page_size
    )


@router.get("/{agenda_item_id}", response_model=AgendaItemResponse)
async def get_agenda_item(
    agenda_item_id: UUID,
    db=Depends(get_db),
) -> AgendaItemResponse:
    """Get a single agenda item by ID."""
    # TODO: implement real DB query
    raise HTTPException(status_code=404, detail="Agenda item not found")
