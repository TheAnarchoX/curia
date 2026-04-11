"""Source synchronisation tasks."""

import logging

from apps.worker.app.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="source_sync.sync_source")
def sync_source(source_id: str) -> dict[str, str]:
    """Synchronise a single data source.

    Fetches the latest data from the external source and upserts
    source records into the database.
    """
    logger.info("Syncing source %s", source_id)
    # TODO: implement real synchronisation logic
    return {"status": "ok", "message": f"Synced source {source_id}"}


@celery_app.task(name="source_sync.discover_sources")
def discover_sources() -> dict[str, str]:
    """Discover new data sources to ingest.

    Scans configured source registries and registers any new sources
    found in the database.
    """
    logger.info("Discovering new sources")
    # TODO: implement real discovery logic
    return {"status": "ok", "message": "Source discovery complete"}
