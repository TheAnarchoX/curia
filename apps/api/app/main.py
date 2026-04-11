"""FastAPI application entry-point."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

from apps.api.app.config import Settings
from apps.api.app.dependencies import get_settings
from apps.api.app.middleware.logging import RequestLoggingMiddleware
from apps.api.app.routers.health import router as health_router
from apps.api.app.routers.v1 import v1_router

logger = logging.getLogger("curia.api")


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Startup / shutdown lifecycle hook."""
    logger.info("Curia API starting up")
    yield
    logger.info("Curia API shutting down")


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build and return the configured FastAPI application."""
    settings = settings or get_settings()

    app = FastAPI(
        title="Curia API",
        description="REST API for the Curia Dutch political intelligence platform.",
        version="0.1.0",
        lifespan=lifespan,
        debug=settings.debug,
    )

    # -- middleware --
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(RequestLoggingMiddleware)

    # -- routers --
    app.include_router(health_router)
    app.include_router(v1_router)

    return app


app = create_app()
