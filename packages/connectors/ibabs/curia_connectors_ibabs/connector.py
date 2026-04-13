"""iBabs source connector — implements the SourceConnector interface."""

from __future__ import annotations

from typing import Any
from urllib.parse import parse_qsl, urlencode, urljoin, urlparse, urlunparse

from curia_ingestion.client import CrawlerClient
from curia_ingestion.interfaces import (
    CrawlConfig,
    CrawlResult,
    SourceConnector,
    SourceConnectorMeta,
)
from curia_ingestion.rate_limiter import RateLimiter
from curia_ingestion.retry import RetryPolicy

from curia_connectors_ibabs.config import INCREMENTAL_SYNC_SECTIONS, IbabsSourceConfig

_VERSION = "0.1.0"


class IbabsConnector(SourceConnector):
    """Connector that discovers and crawls pages on an iBabs portal."""

    def __init__(self, source_config: IbabsSourceConfig) -> None:
        """Initialize the connector with an iBabs source configuration."""
        self._config = source_config
        self._checkpoint: dict[str, Any] = {}
        self._crawler: CrawlerClient | None = None

    # ------------------------------------------------------------------
    # SourceConnector interface
    # ------------------------------------------------------------------

    def get_meta(self) -> SourceConnectorMeta:
        """Return metadata describing this iBabs connector instance."""
        return SourceConnectorMeta(
            source_type="ibabs",
            name=f"iBabs – {self._config.municipality_slug}",
            version=_VERSION,
            description=(
                f"Scrapes the iBabs portal for {self._config.municipality_slug} ({self._config.portal_variant} variant)"
            ),
            capabilities=list(self._config.known_capabilities),
        )

    async def discover_pages(self, config: CrawlConfig) -> list[str]:
        """Build the initial seed URLs from the configured paths."""
        base = config.base_url or self._config.base_url
        urls_by_section: list[tuple[str, str]] = []

        for section, path in self._config.custom_paths.items():
            if section in self._config.known_capabilities:
                seed_url = urljoin(base.rstrip("/") + "/", path.lstrip("/"))
                urls_by_section.append((section, seed_url))

        urls = [url for _, url in urls_by_section]

        checkpoint_offsets = self._checkpoint.get("page_offsets")
        if self._checkpoint.get("last_synced_at") and isinstance(checkpoint_offsets, dict):
            incremental_sections = [section for section, _ in urls_by_section if section in INCREMENTAL_SYNC_SECTIONS]
            if incremental_sections:
                urls_by_section_lookup = dict(urls_by_section)
                incremental_urls_by_section = {
                    section: self._apply_page_offset(
                        urljoin(base.rstrip("/") + "/", self._config.custom_paths[section].lstrip("/")),
                        checkpoint_offsets.get(section),
                    )
                    for section in incremental_sections
                }
                urls = [
                    incremental_urls_by_section.get(section, urls_by_section_lookup[section])
                    for section in incremental_sections
                ]

        # If a checkpoint records the last-seen page for pagination, resume
        last_meetings_page = self._checkpoint.get("last_meetings_page_url")
        if last_meetings_page and last_meetings_page not in urls:
            urls.append(last_meetings_page)

        return urls

    async def crawl_page(self, url: str, config: CrawlConfig) -> CrawlResult:
        """Fetch a single page from the iBabs portal.

        Delegates to :class:`~curia_ingestion.client.CrawlerClient` which
        handles rate limiting (via ``config.rate_limit_rps``) and retries.
        The result is enriched with same-origin link discovery and
        municipality metadata before being returned.
        """
        crawler = self._get_crawler(config)
        result = await crawler.fetch(url, config)

        # Enrich result with connector-specific metadata and discovered links.
        discovered: list[str] = []
        if result.raw_content is not None and "text/html" in result.content_type:
            discovered = self._extract_same_origin_links(result.raw_content, url)

        return result.model_copy(
            update={
                "metadata": {"municipality": self._config.municipality_slug},
                "discovered_urls": discovered,
            }
        )

    async def get_checkpoint(self) -> dict[str, Any]:
        """Return the current checkpoint state for resumable crawling."""
        return dict(self._checkpoint)

    async def set_checkpoint(self, checkpoint: dict[str, Any]) -> None:
        """Restore checkpoint state from a previous crawl run."""
        self._checkpoint = dict(checkpoint)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_crawler(self, config: CrawlConfig) -> CrawlerClient:
        """Return (and lazily create) the shared :class:`CrawlerClient`.

        The client is configured with a :class:`~curia_ingestion.rate_limiter.RateLimiter`
        seeded from ``config.rate_limit_rps`` and a
        :class:`~curia_ingestion.retry.RetryPolicy` derived from
        ``config.retry_max``.

        .. note::
            The client is initialised once per connector instance using the
            *first* :class:`CrawlConfig` passed to :meth:`crawl_page`.
            Changing ``rate_limit_rps`` or ``retry_max`` in a subsequent
            config will have no effect; create a new :class:`IbabsConnector`
            instance if different settings are required.
        """
        if self._crawler is None:
            self._crawler = CrawlerClient(
                rate_limiter=RateLimiter(rate=config.rate_limit_rps),
                retry_policy=RetryPolicy(max_retries=config.retry_max),
                headers={
                    "User-Agent": f"CuriaBot/{_VERSION} (+https://github.com/curia-nl)",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                },
            )
        return self._crawler

    @staticmethod
    def _extract_same_origin_links(raw: bytes, page_url: str) -> list[str]:
        """Quick regex-free link extraction for discovery purposes."""
        from urllib.parse import urlparse

        from bs4 import BeautifulSoup

        soup = BeautifulSoup(raw, "lxml")
        origin = urlparse(page_url)
        links: list[str] = []

        for anchor in soup.find_all("a", href=True):
            href = anchor.get("href")
            if not isinstance(href, str):
                continue
            absolute = urljoin(page_url, href)
            parsed = urlparse(absolute)
            if parsed.netloc == origin.netloc:
                links.append(absolute)

        return links

    @staticmethod
    def _apply_page_offset(url: str, offset_data: Any) -> str:
        """Apply a stored checkpoint page offset to a section seed URL."""
        if not isinstance(offset_data, dict):
            return url

        param = offset_data.get("param")
        value = offset_data.get("value")
        if not isinstance(param, str) or param == "" or value in (None, ""):
            return url

        parsed = urlparse(url)
        query = dict(parse_qsl(parsed.query, keep_blank_values=True))
        query[param] = str(value)
        return urlunparse(parsed._replace(query=urlencode(query)))
