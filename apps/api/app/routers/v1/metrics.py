"""Metric endpoints."""

import asyncio
from datetime import date
from uuid import UUID

from curia_domain.db.models import (
    AmendmentRow,
    DocumentRow,
    MeetingRow,
    MetricDefinitionRow,
    MetricResultRow,
    MotionRow,
    PartyRow,
    PoliticianRow,
    VoteRow,
    WrittenQuestionRow,
)
from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.app.dependencies import get_db
from apps.api.app.routers.v1._utils import fetch_paginated
from apps.api.app.schemas.common import PaginatedResponse
from apps.api.app.schemas.responses import (
    MetricDefinitionResponse,
    MetricResultResponse,
    OverviewResponse,
)

router = APIRouter(prefix="/metrics", tags=["metrics"])


async def _count(db: AsyncSession, model: type) -> int:
    result = await db.execute(select(func.count()).select_from(model))
    return result.scalar_one()


@router.get("/overview", response_model=OverviewResponse)
async def get_overview(
    db: AsyncSession = Depends(get_db),
) -> OverviewResponse:
    """Return high-level entity counts for the dashboard."""
    (
        meetings,
        politicians,
        parties,
        motions,
        votes,
        documents,
        amendments,
        written_questions,
    ) = await asyncio.gather(
        _count(db, MeetingRow),
        _count(db, PoliticianRow),
        _count(db, PartyRow),
        _count(db, MotionRow),
        _count(db, VoteRow),
        _count(db, DocumentRow),
        _count(db, AmendmentRow),
        _count(db, WrittenQuestionRow),
    )
    return OverviewResponse(
        meetings=meetings,
        politicians=politicians,
        parties=parties,
        motions=motions,
        votes=votes,
        documents=documents,
        amendments=amendments,
        written_questions=written_questions,
    )


@router.get("/definitions", response_model=PaginatedResponse[MetricDefinitionResponse])
async def list_metric_definitions(
    code: str | None = Query(None, description="Filter by metric code"),
    entity_scope: str | None = Query(None, description="Filter by entity scope"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[MetricDefinitionResponse]:
    """List all metric definitions."""
    stmt = select(MetricDefinitionRow).order_by(MetricDefinitionRow.code, MetricDefinitionRow.id)

    if code is not None:
        stmt = stmt.where(MetricDefinitionRow.code == code)
    if entity_scope is not None:
        stmt = stmt.where(MetricDefinitionRow.entity_scope == entity_scope)

    return await fetch_paginated(db, stmt, MetricDefinitionResponse, limit=limit, offset=offset)


@router.get("/results", response_model=PaginatedResponse[MetricResultResponse])
async def list_metric_results(
    entity_id: UUID | None = Query(None, description="Filter by entity"),
    metric_code: str | None = Query(None, description="Filter by metric code"),
    entity_type: str | None = Query(None, description="Filter by entity type"),
    period_start_from: date | None = Query(None, description="Filter by period start lower bound"),
    period_end_to: date | None = Query(None, description="Filter by period end upper bound"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[MetricResultResponse]:
    """List metric results, optionally filtered by entity or metric code."""
    stmt = select(MetricResultRow).order_by(MetricResultRow.period_start, MetricResultRow.id)

    if entity_id is not None:
        stmt = stmt.where(MetricResultRow.entity_id == entity_id)
    if metric_code is not None:
        stmt = stmt.where(MetricResultRow.metric_code == metric_code)
    if entity_type is not None:
        stmt = stmt.where(MetricResultRow.entity_type == entity_type)
    if period_start_from is not None:
        stmt = stmt.where(MetricResultRow.period_start >= period_start_from)
    if period_end_to is not None:
        stmt = stmt.where(MetricResultRow.period_end <= period_end_to)

    return await fetch_paginated(db, stmt, MetricResultResponse, limit=limit, offset=offset)
