"""Data extraction tasks."""

import logging

from apps.worker.app.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="extraction.run_extraction")
def run_extraction(source_record_id: str) -> dict[str, str]:
    """Run the extraction pipeline on a source record.

    Parses a raw source record and produces structured assertions
    linked to evidence snippets.
    """
    logger.info("Running extraction for source record %s", source_record_id)
    # TODO: implement real extraction pipeline
    return {"status": "ok", "message": f"Extraction done for record {source_record_id}"}


@celery_app.task(name="extraction.extract_document_text")
def extract_document_text(document_id: str) -> dict[str, str]:
    """Extract plain text from a document (e.g. PDF).

    Downloads the document, runs text extraction, and persists
    the result on the document record.
    """
    logger.info("Extracting text from document %s", document_id)
    # TODO: implement real text extraction
    return {"status": "ok", "message": f"Text extracted for document {document_id}"}
