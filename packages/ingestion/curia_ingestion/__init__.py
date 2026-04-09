"""Curia ingestion layer – crawling, parsing, and snapshot storage."""

from curia_ingestion.interfaces import (
    CrawlConfig,
    CrawlResult,
    ParsedEntity,
    Parser,
    ParseResult,
    SourceConnector,
    SourceConnectorMeta,
)
from curia_ingestion.registry import SourceRegistry
from curia_ingestion.scheduler import CrawlScheduler, SimpleCrawlScheduler
from curia_ingestion.rate_limiter import RateLimiter
from curia_ingestion.retry import RetryPolicy, retry_with_policy
from curia_ingestion.client import CrawlerClient
from curia_ingestion.snapshot import FileSystemSnapshotStore, RawSnapshotStore

__all__ = [
    "CrawlConfig",
    "CrawlResult",
    "CrawlerClient",
    "CrawlScheduler",
    "FileSystemSnapshotStore",
    "ParsedEntity",
    "Parser",
    "ParseResult",
    "RateLimiter",
    "RawSnapshotStore",
    "RetryPolicy",
    "retry_with_policy",
    "SimpleCrawlScheduler",
    "SourceConnector",
    "SourceConnectorMeta",
    "SourceRegistry",
]
