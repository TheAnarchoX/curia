"""Shared request/response schemas."""

from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Generic, TypeVar

from pydantic import BaseModel, Field, field_validator

T = TypeVar("T")


class PaginationParams(BaseModel):
    """Query parameters for paginated endpoints."""

    page: int = Field(default=1, ge=1, description="Page number (1-indexed)")
    page_size: int = Field(default=50, ge=1, le=100, description="Items per page")

    @field_validator("page_size")
    @classmethod
    def cap_page_size(cls, v: int) -> int:
        """Ensure page_size does not exceed 100."""
        return min(v, 100)


class PaginatedResponse(BaseModel, Generic[T]):
    """Wrapper for paginated list responses."""

    items: list[T]
    total: int
    page: int
    page_size: int
    pages: int

    @classmethod
    def build(  # noqa: D102
        cls, items: list[T], total: int, page: int, page_size: int
    ) -> "PaginatedResponse[T]":
        return cls(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            pages=max(1, math.ceil(total / page_size)),
        )


class ErrorResponse(BaseModel):
    """Standard error payload."""

    detail: str
    code: str | None = None
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


class SuccessResponse(BaseModel):
    """Generic success payload."""

    message: str
