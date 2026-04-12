"""Unit tests for IbabsConnector.crawl_page() with mocked HTTP responses."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch
from uuid import uuid4

from curia_connectors_ibabs.config import IbabsSourceConfig
from curia_connectors_ibabs.connector import IbabsConnector
from curia_ingestion.interfaces import CrawlConfig, CrawlResult

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_config(
    rate_limit_rps: float = 2.0,
    retry_max: int = 3,
    timeout_seconds: float = 10.0,
) -> CrawlConfig:
    return CrawlConfig(
        source_id=uuid4(),
        base_url="https://test.bestuurlijkeinformatie.nl",
        rate_limit_rps=rate_limit_rps,
        retry_max=retry_max,
        timeout_seconds=timeout_seconds,
    )


def _make_connector(municipality: str = "testtown") -> IbabsConnector:
    return IbabsConnector(
        IbabsSourceConfig(
            base_url="https://testtown.bestuurlijkeinformatie.nl",
            municipality_slug=municipality,
        )
    )


def _make_crawl_result(
    url: str,
    status_code: int = 200,
    content: bytes = b"<html></html>",
    content_type: str = "text/html; charset=utf-8",
    errors: list[str] | None = None,
) -> CrawlResult:
    return CrawlResult(
        url=url,
        status_code=status_code,
        content_hash=hashlib.sha256(content).hexdigest(),
        fetched_at=datetime.now(UTC),
        content_type=content_type,
        raw_content=content if status_code == 200 else None,
        errors=errors or [],
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


async def test_crawl_page_returns_result_with_status_and_content_hash() -> None:
    """crawl_page() should return a CrawlResult with status code and content hash."""
    connector = _make_connector()
    config = _make_config()
    url = "https://testtown.bestuurlijkeinformatie.nl/Agenda/Index"
    raw = b"<html><body>Hello</body></html>"
    expected_hash = hashlib.sha256(raw).hexdigest()

    mock_result = _make_crawl_result(url, content=raw)

    with patch("curia_connectors_ibabs.connector.CrawlerClient") as MockClient:
        instance = MockClient.return_value
        instance.fetch = AsyncMock(return_value=mock_result)

        result = await connector.crawl_page(url, config)

    assert result.url == url
    assert result.status_code == 200
    assert result.content_hash == expected_hash
    assert result.raw_content == raw


async def test_crawl_page_adds_municipality_metadata() -> None:
    """crawl_page() should inject municipality slug into result metadata."""
    connector = _make_connector(municipality="amsterdam")
    config = _make_config()
    url = "https://amsterdam.bestuurlijkeinformatie.nl/Agenda/Index"
    raw = b"<html></html>"

    with patch("curia_connectors_ibabs.connector.CrawlerClient") as MockClient:
        instance = MockClient.return_value
        instance.fetch = AsyncMock(return_value=_make_crawl_result(url, content=raw))

        result = await connector.crawl_page(url, config)

    assert result.metadata == {"municipality": "amsterdam"}


async def test_crawl_page_discovers_same_origin_links_in_html() -> None:
    """crawl_page() should extract same-origin hrefs from HTML content."""
    connector = _make_connector(municipality="utrecht")
    config = _make_config()
    base = "https://utrecht.bestuurlijkeinformatie.nl"
    url = f"{base}/Agenda/Index"
    raw = (
        b"<html><body>"
        b'<a href="/Vergadering/1">Meeting 1</a>'
        b'<a href="https://extern.nl/other">External</a>'
        b'<a href="/Vergadering/2">Meeting 2</a>'
        b"</body></html>"
    )

    with patch("curia_connectors_ibabs.connector.CrawlerClient") as MockClient:
        instance = MockClient.return_value
        instance.fetch = AsyncMock(return_value=_make_crawl_result(url, content=raw, content_type="text/html"))

        result = await connector.crawl_page(url, config)

    assert f"{base}/Vergadering/1" in result.discovered_urls
    assert f"{base}/Vergadering/2" in result.discovered_urls
    assert "https://extern.nl/other" not in result.discovered_urls


async def test_crawl_page_skips_link_discovery_for_non_html() -> None:
    """crawl_page() should not attempt link extraction for non-HTML content types."""
    connector = _make_connector()
    config = _make_config()
    url = "https://testtown.bestuurlijkeinformatie.nl/doc/report.pdf"
    raw = b"%PDF-1.4 binary data here"

    with patch("curia_connectors_ibabs.connector.CrawlerClient") as MockClient:
        instance = MockClient.return_value
        instance.fetch = AsyncMock(return_value=_make_crawl_result(url, content=raw, content_type="application/pdf"))

        result = await connector.crawl_page(url, config)

    assert result.discovered_urls == []


async def test_crawl_page_propagates_http_errors_as_error_result() -> None:
    """crawl_page() should return a CrawlResult with errors on HTTP failure."""
    connector = _make_connector()
    config = _make_config()
    url = "https://testtown.bestuurlijkeinformatie.nl/missing"
    error_result = CrawlResult(
        url=url,
        status_code=0,
        content_hash="",
        fetched_at=datetime.now(UTC),
        content_type="",
        errors=["Transport error: connection refused"],
    )

    with patch("curia_connectors_ibabs.connector.CrawlerClient") as MockClient:
        instance = MockClient.return_value
        instance.fetch = AsyncMock(return_value=error_result)

        result = await connector.crawl_page(url, config)

    assert result.status_code == 0
    assert result.errors != []
    assert result.discovered_urls == []


async def test_crawl_page_configures_rate_limiter_from_config() -> None:
    """CrawlerClient should be created with rate_limit_rps from CrawlConfig."""
    connector = _make_connector()
    config = _make_config(rate_limit_rps=5.0)
    url = "https://testtown.bestuurlijkeinformatie.nl/Agenda/Index"

    with (
        patch("curia_connectors_ibabs.connector.CrawlerClient") as MockClient,
        patch("curia_connectors_ibabs.connector.RateLimiter") as MockRateLimiter,
    ):
        instance = MockClient.return_value
        instance.fetch = AsyncMock(return_value=_make_crawl_result(url))

        await connector.crawl_page(url, config)

    MockRateLimiter.assert_called_once_with(rate=5.0)


async def test_crawl_page_reuses_crawler_client_across_calls() -> None:
    """IbabsConnector should reuse the same CrawlerClient instance."""
    connector = _make_connector()
    config = _make_config()
    url = "https://testtown.bestuurlijkeinformatie.nl/Agenda/Index"

    with patch("curia_connectors_ibabs.connector.CrawlerClient") as MockClient:
        instance = MockClient.return_value
        instance.fetch = AsyncMock(return_value=_make_crawl_result(url))

        await connector.crawl_page(url, config)
        await connector.crawl_page(url, config)

    # CrawlerClient constructor should only have been called once
    assert MockClient.call_count == 1


async def test_crawl_page_configures_retry_policy_from_config() -> None:
    """CrawlerClient should be created with retry_max from CrawlConfig."""
    connector = _make_connector()
    config = _make_config(retry_max=5)
    url = "https://testtown.bestuurlijkeinformatie.nl/Agenda/Index"

    with (
        patch("curia_connectors_ibabs.connector.CrawlerClient") as MockClient,
        patch("curia_connectors_ibabs.connector.RetryPolicy") as MockRetryPolicy,
    ):
        instance = MockClient.return_value
        instance.fetch = AsyncMock(return_value=_make_crawl_result(url))

        await connector.crawl_page(url, config)

    MockRetryPolicy.assert_called_once_with(max_retries=5)


async def test_crawl_page_sets_ibabs_user_agent_header() -> None:
    """CrawlerClient should be created with a CuriaBot User-Agent header."""
    connector = _make_connector()
    config = _make_config()
    url = "https://testtown.bestuurlijkeinformatie.nl/Agenda/Index"

    with patch("curia_connectors_ibabs.connector.CrawlerClient") as MockClient:
        instance = MockClient.return_value
        instance.fetch = AsyncMock(return_value=_make_crawl_result(url))

        await connector.crawl_page(url, config)

    _, kwargs = MockClient.call_args
    headers = kwargs.get("headers", {})
    assert "CuriaBot" in headers.get("User-Agent", "")
