"""Source synchronisation tasks."""

from __future__ import annotations

import asyncio
import logging
import uuid
from collections.abc import Sequence
from typing import Any

from celery import Signature, chain
from curia_connectors_ibabs.config import IbabsSourceConfig
from curia_connectors_ibabs.connector import IbabsConnector
from curia_domain.db.models import SourceRow
from curia_domain.db.session import async_session_factory
from curia_ingestion.interfaces import CrawlConfig
from sqlalchemy import select

from apps.worker.app.celery_app import celery_app
from apps.worker.app.config import WorkerSettings
from apps.worker.app.tasks.crawl import crawl_page, map_page, parse_page, persist_page

logger = logging.getLogger(__name__)


def _resolve_ibabs_sync_state(
    source_id: str,
    municipality_slug: str | None = None,
    base_url: str | None = None,
    governing_body_id: str | None = None,
    checkpoint: dict[str, Any] | None = None,
) -> dict[str, Any]:
    settings = WorkerSettings()
    resolved_base_url = base_url or settings.ibabs_base_url
    resolved_municipality = municipality_slug or settings.ibabs_municipality_slug
    resolved_governing_body_id = governing_body_id or (
        str(settings.ibabs_governing_body_id) if settings.ibabs_governing_body_id else None
    )

    if not resolved_base_url or not resolved_municipality or not resolved_governing_body_id:
        missing_fields = [
            field_name
            for field_name, value in (
                ("ibabs_base_url", resolved_base_url),
                ("ibabs_municipality_slug", resolved_municipality),
                ("ibabs_governing_body_id", resolved_governing_body_id),
            )
            if not value
        ]
        raise ValueError(f"Missing iBabs sync configuration: {', '.join(missing_fields)}")

    return {
        "source_id": source_id,
        "source_type": "ibabs",
        "connector": {
            "base_url": resolved_base_url,
            "municipality_slug": resolved_municipality,
        },
        "crawl_config": {
            "source_id": str(uuid.uuid5(uuid.NAMESPACE_URL, resolved_base_url.rstrip("/"))),
            "base_url": resolved_base_url,
            "max_pages": settings.ibabs_max_pages,
            "rate_limit_rps": settings.ibabs_rate_limit_rps,
            "timeout_seconds": settings.ibabs_timeout_seconds,
            "retry_max": settings.ibabs_retry_max,
            "checkpoint": dict(checkpoint or {}),
        },
        "governing_body_id": resolved_governing_body_id,
        "checkpoint": dict(checkpoint or {}),
        "sync_errors": [],
    }


async def _discover_ibabs_pages(sync_state: dict[str, Any]) -> list[str]:
    connector = IbabsConnector(IbabsSourceConfig.model_validate(sync_state["connector"]))
    await connector.set_checkpoint(dict(sync_state.get("checkpoint") or {}))
    return await connector.discover_pages(CrawlConfig.model_validate(sync_state["crawl_config"]))


async def _load_persisted_checkpoint(source_id: str) -> dict[str, Any]:
    try:
        source_uuid = uuid.UUID(source_id)
    except ValueError:
        return {}

    async with async_session_factory() as session:
        source_row = await session.scalar(select(SourceRow).where(SourceRow.id == source_uuid))
        if source_row is None or not isinstance(source_row.config, dict):
            return {}

        checkpoint = source_row.config.get("checkpoint")
        if not isinstance(checkpoint, dict):
            return {}

        return dict(checkpoint)


def build_ibabs_sync_signatures(sync_state: dict[str, Any], urls: Sequence[str]) -> list[Signature]:
    """Return the per-page crawl → parse → map → persist signature list."""
    signatures: list[Signature] = []
    for index, url in enumerate(urls):
        if index == 0:
            signatures.append(crawl_page.si(sync_state, url))
        else:
            signatures.append(crawl_page.s(url))
        signatures.extend([parse_page.s(), map_page.s(), persist_page.s()])
    return signatures


@celery_app.task(name="source_sync.sync_source")
def sync_source(
    source_id: str,
    municipality_slug: str | None = None,
    base_url: str | None = None,
    governing_body_id: str | None = None,
    checkpoint: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Synchronise a single data source.

    Triggers the iBabs crawl → parse → map → persist task chain
    for the configured municipality.
    """
    logger.info("Syncing source %s via iBabs pipeline", source_id)

    try:
        persisted_checkpoint = asyncio.run(_load_persisted_checkpoint(source_id))
        resolved_checkpoint = dict(persisted_checkpoint)
        resolved_checkpoint.update(dict(checkpoint or {}))
        sync_state = _resolve_ibabs_sync_state(
            source_id=source_id,
            municipality_slug=municipality_slug,
            base_url=base_url,
            governing_body_id=governing_body_id,
            checkpoint=resolved_checkpoint,
        )
        urls = asyncio.run(_discover_ibabs_pages(sync_state))
    except Exception as exc:  # noqa: BLE001
        logger.exception("Unable to start iBabs sync for source %s", source_id)
        return {"status": "error", "message": str(exc), "source_id": source_id}

    if not urls:
        return {
            "status": "noop",
            "message": f"No iBabs pages discovered for source {source_id}",
            "source_id": source_id,
            "municipality": sync_state["connector"]["municipality_slug"],
        }

    job = chain(*build_ibabs_sync_signatures(sync_state, urls)).apply_async()
    return {
        "status": "started",
        "message": f"Started iBabs sync for source {source_id}",
        "source_id": source_id,
        "municipality": sync_state["connector"]["municipality_slug"],
        "pages": len(urls),
        "task_id": job.id,
    }


@celery_app.task(name="source_sync.discover_sources")
def discover_sources() -> dict[str, str]:
    """Discover new data sources to ingest.

    Scans configured source registries and registers any new sources
    found in the database.
    """
    logger.info("Discovering new sources")
    # TODO: implement real discovery logic
    return {"status": "ok", "message": "Source discovery complete"}
