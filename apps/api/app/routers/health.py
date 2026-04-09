"""Health and readiness probes."""

import logging

from fastapi import APIRouter, Depends, Response
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.app.dependencies import get_db

logger = logging.getLogger("curia.api")

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict[str, str]:
    """Liveness check."""
    return {"status": "healthy", "version": "0.1.0"}


@router.get("/ready")
async def ready(
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """Readiness check — verifies database connectivity."""
    try:
        await db.execute(text("SELECT 1"))
        return {"status": "ready"}
    except Exception:
        logger.exception("Readiness check failed")
        response.status_code = 503
        return {"status": "unavailable"}
