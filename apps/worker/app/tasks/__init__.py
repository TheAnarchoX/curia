"""Task package — import all task modules so Celery can discover them."""

from apps.worker.app.tasks import (  # noqa: F401
    analytics,
    crawl,
    document_processing,
    extraction,
    identity_resolution,
    normalization,
    source_sync,
)
