"""FastAPI dependencies for injection."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from functools import lru_cache

from curia_domain.db.session import get_session
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.app.config import Settings


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached application settings."""
    return Settings()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Yield an async database session."""
    async for session in get_session():
        yield session
