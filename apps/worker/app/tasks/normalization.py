"""Data normalisation tasks."""

import logging

from apps.worker.app.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="normalization.normalize_records")
def normalize_records(extraction_run_id: str) -> dict[str, str]:
    """Normalise extracted records from an extraction run.

    Applies cleaning, deduplication, and schema-mapping rules to
    assertions produced by the given extraction run.
    """
    logger.info("Normalising records for extraction run %s", extraction_run_id)
    # TODO: implement real normalisation pipeline
    return {"status": "ok", "message": f"Normalised records for run {extraction_run_id}"}


@celery_app.task(name="normalization.canonicalize_entities")
def canonicalize_entities(source_id: str) -> dict[str, str]:
    """Canonicalise entities extracted from a source.

    Resolves variant names and merges duplicates to produce a
    single canonical record per real-world entity.
    """
    logger.info("Canonicalising entities for source %s", source_id)
    # TODO: implement real canonicalisation
    return {"status": "ok", "message": f"Entities canonicalised for source {source_id}"}
