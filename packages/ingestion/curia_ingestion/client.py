"""High-level async HTTP client for crawling."""

from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timezone

import httpx

from curia_ingestion.interfaces import CrawlConfig, CrawlResult
from curia_ingestion.rate_limiter import RateLimiter
from curia_ingestion.retry import RetryableError, RetryPolicy, retry_with_policy

logger = logging.getLogger(__name__)


class CrawlerClient:
    """Async HTTP client that wraps :class:`httpx.AsyncClient` with
    rate-limiting and retry logic.
    """

    def __init__(
        self,
        rate_limiter: RateLimiter | None = None,
        retry_policy: RetryPolicy | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        """Initialize the crawler client with optional rate limiter, retry policy, and headers."""
        self._rate_limiter = rate_limiter or RateLimiter()
        self._retry_policy = retry_policy or RetryPolicy()
        self._headers = headers or {
            "User-Agent": "CuriaCrawler/0.1 (+https://github.com/curia-nl)",
        }
        self._client: httpx.AsyncClient | None = None

    async def _ensure_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(headers=self._headers, follow_redirects=True)
        return self._client

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    async def fetch(self, url: str, config: CrawlConfig) -> CrawlResult:
        """Fetch *url* respecting rate limits and retry policy.

        Returns a :class:`CrawlResult` regardless of HTTP status.
        """
        await self._rate_limiter.acquire()

        async def _do_fetch() -> CrawlResult:
            client = await self._ensure_client()
            try:
                response = await client.get(url, timeout=config.timeout_seconds)
            except httpx.TransportError as exc:
                logger.error("Transport error fetching %s: %s", url, exc)
                return CrawlResult(
                    url=url,
                    status_code=0,
                    content_hash="",
                    fetched_at=datetime.now(timezone.utc),
                    content_type="",
                    errors=[str(exc)],
                )

            content = response.content
            content_hash = hashlib.sha256(content).hexdigest()
            content_type = response.headers.get("content-type", "")

            if response.status_code in self._retry_policy.retryable_status_codes:
                raise RetryableError(
                    f"HTTP {response.status_code} for {url}",
                    status_code=response.status_code,
                )

            return CrawlResult(
                url=url,
                status_code=response.status_code,
                content_hash=content_hash,
                fetched_at=datetime.now(timezone.utc),
                content_type=content_type,
                raw_content=content,
            )

        try:
            return await retry_with_policy(_do_fetch, self._retry_policy)
        except RetryableError as exc:
            logger.error("All retries exhausted for %s: %s", url, exc)
            return CrawlResult(
                url=url,
                status_code=exc.status_code or 0,
                content_hash="",
                fetched_at=datetime.now(timezone.utc),
                content_type="",
                errors=[str(exc)],
            )
