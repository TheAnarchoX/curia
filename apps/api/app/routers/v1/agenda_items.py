"""Agenda-item endpoints."""

from uuid import UUID

from curia_domain.db.models import AgendaItemRow
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.app.dependencies import get_db
from apps.api.app.routers.v1._utils import fetch_one_or_404, fetch_paginated
from apps.api.app.schemas.common import PaginatedResponse
from apps.api.app.schemas.responses import AgendaItemResponse

router = APIRouter(prefix="/agenda-items", tags=["agenda-items"])


@router.get("", response_model=PaginatedResponse[AgendaItemResponse])
async def list_agenda_items(
    meeting_id: UUID | None = Query(None, description="Filter by meeting"),
    parent_item_id: UUID | None = Query(None, description="Filter by parent item"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[AgendaItemResponse]:
    """List all agenda items."""
    stmt = select(AgendaItemRow).order_by(AgendaItemRow.meeting_id, AgendaItemRow.ordering, AgendaItemRow.id)

    if meeting_id is not None:
        stmt = stmt.where(AgendaItemRow.meeting_id == meeting_id)
    if parent_item_id is not None:
        stmt = stmt.where(AgendaItemRow.parent_item_id == parent_item_id)

    return await fetch_paginated(db, stmt, AgendaItemResponse, limit=limit, offset=offset)


@router.get("/{agenda_item_id}", response_model=AgendaItemResponse)
async def get_agenda_item(
    agenda_item_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> AgendaItemResponse:
    """Get a single agenda item by ID."""
    return await fetch_one_or_404(
        db,
        select(AgendaItemRow).where(AgendaItemRow.id == agenda_item_id),
        AgendaItemResponse,
        detail="Agenda item not found",
    )
