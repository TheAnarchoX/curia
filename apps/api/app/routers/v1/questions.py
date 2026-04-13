"""Written-question endpoints."""

from datetime import date
from uuid import UUID

from curia_domain.db.models import WrittenQuestionRow
from curia_domain.enums import PropositionStatus
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.app.dependencies import get_db
from apps.api.app.routers.v1._utils import fetch_one_or_404, fetch_paginated
from apps.api.app.schemas.common import PaginatedResponse
from apps.api.app.schemas.responses import WrittenQuestionResponse

router = APIRouter(prefix="/questions", tags=["questions"])


@router.get("", response_model=PaginatedResponse[WrittenQuestionResponse])
async def list_questions(
    meeting_id: UUID | None = Query(None, description="Filter by meeting"),
    addressee: str | None = Query(None, description="Filter by addressee"),
    status: PropositionStatus | None = Query(None, description="Filter by question status"),
    submitted_from: date | None = Query(None, description="Filter by submitted date lower bound"),
    submitted_to: date | None = Query(None, description="Filter by submitted date upper bound"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[WrittenQuestionResponse]:
    """List all written questions."""
    stmt = select(WrittenQuestionRow).order_by(WrittenQuestionRow.submitted_date, WrittenQuestionRow.id)

    if meeting_id is not None:
        stmt = stmt.where(WrittenQuestionRow.meeting_id == meeting_id)
    if addressee is not None:
        stmt = stmt.where(WrittenQuestionRow.addressee.ilike(f"%{addressee}%"))
    if status is not None:
        stmt = stmt.where(WrittenQuestionRow.status == status)
    if submitted_from is not None:
        stmt = stmt.where(WrittenQuestionRow.submitted_date >= submitted_from)
    if submitted_to is not None:
        stmt = stmt.where(WrittenQuestionRow.submitted_date <= submitted_to)

    return await fetch_paginated(db, stmt, WrittenQuestionResponse, limit=limit, offset=offset)


@router.get("/{question_id}", response_model=WrittenQuestionResponse)
async def get_question(
    question_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> WrittenQuestionResponse:
    """Get a single written question by ID."""
    return await fetch_one_or_404(
        db,
        select(WrittenQuestionRow).where(WrittenQuestionRow.id == question_id),
        WrittenQuestionResponse,
        detail="Written question not found",
    )
