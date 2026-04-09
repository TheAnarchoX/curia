"""Crawl job scheduling."""
from __future__ import annotations

import abc
import logging
import uuid
from collections import deque
from datetime import datetime, timezone

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class CrawlJob(BaseModel):
    """Represents a single crawl job in the queue."""
    job_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    source_type: str
    source_id: uuid.UUID
    url: str
    priority: int = 0
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    started_at: datetime | None = None
    completed_at: datetime | None = None


class CrawlScheduler(abc.ABC):
    """Abstract scheduler for crawl jobs."""

    @abc.abstractmethod
    async def schedule_crawl(self, job: CrawlJob) -> None:
        """Add a crawl job to the queue."""

    @abc.abstractmethod
    async def get_pending_jobs(self, limit: int = 10) -> list[CrawlJob]:
        """Retrieve up to *limit* pending jobs."""

    @abc.abstractmethod
    async def mark_completed(self, job_id: uuid.UUID) -> None:
        """Mark a job as completed."""


class SimpleCrawlScheduler(CrawlScheduler):
    """In-memory FIFO crawl scheduler for development and testing."""

    def __init__(self) -> None:
        self._pending: deque[CrawlJob] = deque()
        self._in_progress: dict[uuid.UUID, CrawlJob] = {}
        self._completed: dict[uuid.UUID, CrawlJob] = {}

    async def schedule_crawl(self, job: CrawlJob) -> None:
        """Append *job* to the pending queue."""
        self._pending.append(job)
        logger.debug("Scheduled job %s for url=%s", job.job_id, job.url)

    async def get_pending_jobs(self, limit: int = 10) -> list[CrawlJob]:
        """Pop up to *limit* jobs from the pending queue and move them to in-progress."""
        jobs: list[CrawlJob] = []
        while self._pending and len(jobs) < limit:
            job = self._pending.popleft()
            job.started_at = datetime.now(timezone.utc)
            self._in_progress[job.job_id] = job
            jobs.append(job)
        logger.debug("Returned %d pending jobs", len(jobs))
        return jobs

    async def mark_completed(self, job_id: uuid.UUID) -> None:
        """Move a job from in-progress to completed."""
        job = self._in_progress.pop(job_id, None)
        if job is None:
            logger.warning("Job %s not found in in-progress set", job_id)
            return
        job.completed_at = datetime.now(timezone.utc)
        self._completed[job.job_id] = job
        logger.debug("Marked job %s as completed", job_id)
