"""Regression tests for review-thread follow-up fixes."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest
from curia_ingestion.interfaces import CrawlConfig, CrawlResult, SourceConnector, SourceConnectorMeta
from curia_ingestion.rate_limiter import RateLimiter
from curia_ingestion.registry import SourceRegistry
from curia_ingestion.retry import RetryPolicy
from curia_ingestion.snapshot import FileSystemSnapshotStore

from apps.api.app.config import Settings
from apps.worker.app.config import WorkerSettings


class _ConfigurableConnector(SourceConnector):
    """Simple connector stub with instance-specific metadata."""

    def __init__(self, source_type: str) -> None:
        self._source_type = source_type

    def get_meta(self) -> SourceConnectorMeta:
        return SourceConnectorMeta(
            source_type=self._source_type,
            name="Stub connector",
            version="0.1.0",
            description="Test stub",
        )

    async def discover_pages(self, config: CrawlConfig) -> list[str]:
        return []

    async def crawl_page(self, url: str, config: CrawlConfig) -> CrawlResult:
        raise NotImplementedError

    async def get_checkpoint(self) -> dict[str, object]:
        return {}

    async def set_checkpoint(self, checkpoint: dict[str, object]) -> None:
        return None


def test_rate_limiter_rejects_non_positive_values() -> None:
    """Rate limiter should reject invalid rate/burst values."""
    with pytest.raises(ValueError, match="rate"):
        RateLimiter(rate=0)

    with pytest.raises(ValueError, match="burst"):
        RateLimiter(burst=0)


def test_retry_policy_requires_at_least_one_retry() -> None:
    """Retry policy should validate max_retries eagerly."""
    with pytest.raises(ValueError, match="max_retries"):
        RetryPolicy(max_retries=0)


def test_registry_supports_instance_registration() -> None:
    """Registry should be able to register connectors with instance state."""
    connector = _ConfigurableConnector("configured-source")
    registry = SourceRegistry()

    registry.register(connector)

    factory = registry.get("configured-source")
    assert factory() is connector


def test_settings_read_unprefixed_environment_and_parse_cors(monkeypatch: pytest.MonkeyPatch) -> None:
    """API/worker settings should align with the repo's unprefixed env vars."""
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://env:test@localhost:5432/curia")
    monkeypatch.setenv("CELERY_BROKER_URL", "redis://localhost:6379/9")
    monkeypatch.setenv("CORS_ORIGINS", "http://localhost:3000, https://example.com")

    settings = Settings()
    worker_settings = WorkerSettings()

    assert settings.database_url == "postgresql+asyncpg://env:test@localhost:5432/curia"
    assert settings.cors_origins == ["http://localhost:3000", "https://example.com"]
    assert worker_settings.celery_broker_url == "redis://localhost:6379/9"


@pytest.mark.asyncio
async def test_filesystem_snapshot_store_round_trip(tmp_path: Path) -> None:
    """Snapshot store should perform async-safe round-trips."""
    store = FileSystemSnapshotStore(tmp_path)
    crawl_result = CrawlResult(
        url="https://example.com/doc",
        status_code=200,
        content_hash="abc123",
        fetched_at=datetime.now(UTC),
        content_type="text/html",
        raw_content=b"<html></html>",
        metadata={"source_id": str(uuid4())},
        discovered_urls=["https://example.com/next"],
    )

    key = await store.store(crawl_result)

    assert await store.exists(key) is True
    restored = await store.retrieve(key)
    assert restored == crawl_result
