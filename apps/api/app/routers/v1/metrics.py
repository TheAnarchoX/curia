"""Metric endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query

from apps.api.app.dependencies import get_db
from apps.api.app.schemas.common import PaginatedResponse
from apps.api.app.schemas.responses import MetricDefinitionResponse, MetricResultResponse

router = APIRouter(prefix="/metrics", tags=["metrics"])


@router.get("/definitions", response_model=PaginatedResponse[MetricDefinitionResponse])
async def list_metric_definitions(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    db=Depends(get_db),
) -> PaginatedResponse[MetricDefinitionResponse]:
    """List all metric definitions."""
    # TODO: implement real DB query
    return PaginatedResponse[MetricDefinitionResponse].build(items=[], total=0, page=page, page_size=page_size)


@router.get("/results", response_model=PaginatedResponse[MetricResultResponse])
async def list_metric_results(
    entity_id: UUID | None = Query(None, description="Filter by entity"),
    metric_code: str | None = Query(None, description="Filter by metric code"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    db=Depends(get_db),
) -> PaginatedResponse[MetricResultResponse]:
    """List metric results, optionally filtered by entity or metric code."""
    # TODO: implement real DB query with filters
    return PaginatedResponse[MetricResultResponse].build(items=[], total=0, page=page, page_size=page_size)
