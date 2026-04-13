"""Helpers for database-backed v1 resource endpoints."""

from __future__ import annotations

from typing import Any, TypeVar

from fastapi import HTTPException
from pydantic import BaseModel
from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.app.schemas.common import PaginatedResponse

ResponseModelT = TypeVar("ResponseModelT", bound=BaseModel)


def serialize_row(row: Any, schema: type[ResponseModelT]) -> ResponseModelT:
    """Convert an ORM row into a response schema."""
    data: dict[str, Any] = {}

    for field_name, field_info in schema.model_fields.items():
        value = getattr(row, field_name)
        if value is None and isinstance(field_info.default, list):
            value = []
        data[field_name] = value

    return schema.model_validate(data)


async def fetch_paginated(
    db: AsyncSession,
    stmt: Select[Any],
    schema: type[ResponseModelT],
    *,
    limit: int,
    offset: int,
) -> PaginatedResponse[ResponseModelT]:
    """Execute a paginated query and serialize the result rows."""
    total_stmt = select(func.count()).select_from(stmt.order_by(None).subquery())
    total = (await db.execute(total_stmt)).scalar_one()
    rows = (await db.execute(stmt.limit(limit).offset(offset))).scalars().all()
    items = [serialize_row(row, schema) for row in rows]

    return PaginatedResponse.build(
        items=items,
        total=total,
        page=(offset // limit) + 1,
        page_size=limit,
    )


async def fetch_one_or_404(
    db: AsyncSession,
    stmt: Select[Any],
    schema: type[ResponseModelT],
    *,
    detail: str,
) -> ResponseModelT:
    """Execute a single-row query and raise a 404 when nothing matches."""
    row = (await db.execute(stmt.limit(1))).scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail=detail)
    return serialize_row(row, schema)
