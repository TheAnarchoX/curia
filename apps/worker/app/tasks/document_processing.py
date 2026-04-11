"""Document processing tasks."""

import logging

from apps.worker.app.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="document_processing.process_document")
def process_document(document_id: str) -> dict[str, str]:
    """Run the full processing pipeline on a document.

    Downloads, extracts text, classifies the document type, and
    links it to relevant meetings or agenda items.
    """
    logger.info("Processing document %s", document_id)
    # TODO: implement real document processing pipeline
    return {"status": "ok", "message": f"Processed document {document_id}"}


@celery_app.task(name="document_processing.extract_pdf_text")
def extract_pdf_text(document_id: str) -> dict[str, str]:
    """Extract text content from a PDF document.

    Downloads the PDF, runs OCR if needed, and stores the
    extracted text on the document record.
    """
    logger.info("Extracting PDF text from document %s", document_id)
    # TODO: implement real PDF text extraction
    return {"status": "ok", "message": f"PDF text extracted for document {document_id}"}
