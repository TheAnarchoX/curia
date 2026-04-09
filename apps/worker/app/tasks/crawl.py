"""Web crawling tasks."""

import logging

from apps.worker.app.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="crawl.run_crawl_job")
def run_crawl_job(source_id: str, job_config: dict) -> dict[str, str]:
    """Execute a crawl job for a given source.

    Iterates over configured pages for the source and enqueues
    individual page-crawl tasks.
    """
    logger.info("Running crawl job for source %s with config %s", source_id, job_config)
    # TODO: implement real crawl orchestration
    return {"status": "ok", "message": f"Crawl job started for source {source_id}"}


@celery_app.task(name="crawl.crawl_page")
def crawl_page(source_id: str, url: str) -> dict[str, str]:
    """Crawl a single page from a source.

    Downloads the page content, stores it as a source record, and
    computes a content hash for deduplication.
    """
    logger.info("Crawling page %s for source %s", url, source_id)
    # TODO: implement real page crawling
    return {"status": "ok", "message": f"Crawled {url}"}
