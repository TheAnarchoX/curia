"""Async database session factory for use with FastAPI and SQLAlchemy 2.x."""

from __future__ import annotations

import os
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)


def get_database_url() -> str:
    """Read the database URL from the environment."""
    return os.getenv("DATABASE_URL", "postgresql+asyncpg://curia:curia@localhost:5432/curia")


engine = create_async_engine(
    get_database_url(),
    echo=False,
    pool_size=5,
    max_overflow=10,
)

async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Yield an async database session (FastAPI dependency)."""
    async with async_session_factory() as session:
        yield session
