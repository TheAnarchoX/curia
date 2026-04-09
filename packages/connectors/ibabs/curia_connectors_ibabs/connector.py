"""iBabs source connector — implements the SourceConnector interface."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urljoin

import httpx

from curia_ingestion.interfaces import (
    CrawlConfig,
    CrawlResult,
    SourceConnector,
    SourceConnectorMeta,
)

from curia_connectors_ibabs.config import IbabsSourceConfig

_VERSION = "0.1.0"


class IbabsConnector(SourceConnector):
    """Connector that discovers and crawls pages on an iBabs portal."""

    def __init__(self, source_config: IbabsSourceConfig) -> None:
        self._config = source_config
        self._checkpoint: dict[str, Any] = {}
        self._client: httpx.AsyncClient | None = None

    # ------------------------------------------------------------------
    # SourceConnector interface
    # ------------------------------------------------------------------

    def get_meta(self) -> SourceConnectorMeta:
        return SourceConnectorMeta(
            source_type="ibabs",
            name=f"iBabs – {self._config.municipality_slug}",
            version=_VERSION,
            description=(
                f"Scrapes the iBabs portal for {self._config.municipality_slug} "
                f"({self._config.portal_variant} variant)"
            ),
            capabilities=list(self._config.known_capabilities),
        )

    async def discover_pages(self, config: CrawlConfig) -> list[str]:
        """Build the initial seed URLs from the configured paths."""
        base = config.base_url or self._config.base_url
        urls: list[str] = []

        for section, path in self._config.custom_paths.items():
            if section in self._config.known_capabilities:
                seed_url = urljoin(base.rstrip("/") + "/", path.lstrip("/"))
                urls.append(seed_url)

        # If a checkpoint records the last-seen page for pagination, resume
        last_meetings_page = self._checkpoint.get("last_meetings_page_url")
        if last_meetings_page and last_meetings_page not in urls:
            urls.append(last_meetings_page)

        return urls

    async def crawl_page(self, url: str, config: CrawlConfig) -> CrawlResult:
        """Fetch a single page from the iBabs portal."""
        client = await self._get_client(config)
        errors: list[str] = []
        discovered: list[str] = []

        try:
            response = await client.get(
                url,
                timeout=config.timeout_seconds,
                follow_redirects=True,
            )
            raw = response.content
            content_type = response.headers.get("content-type", "text/html")
            status_code = response.status_code
        except httpx.HTTPError as exc:
            errors.append(f"HTTP error fetching {url}: {exc}")
            return CrawlResult(
                url=url,
                status_code=0,
                content_hash="",
                fetched_at=datetime.now(UTC),
                content_type="",
                errors=errors,
            )

        content_hash = hashlib.sha256(raw).hexdigest()

        # Lightweight link discovery — parsers do the real extraction
        if "text/html" in content_type:
            discovered = self._extract_same_origin_links(raw, url)

        return CrawlResult(
            url=url,
            status_code=status_code,
            content_hash=content_hash,
            fetched_at=datetime.now(UTC),
            content_type=content_type,
            raw_content=raw,
            metadata={"municipality": self._config.municipality_slug},
            discovered_urls=discovered,
            errors=errors,
        )

    async def get_checkpoint(self) -> dict[str, Any]:
        return dict(self._checkpoint)

    async def set_checkpoint(self, checkpoint: dict[str, Any]) -> None:
        self._checkpoint = dict(checkpoint)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _get_client(self, config: CrawlConfig) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                headers={
                    "User-Agent": f"CuriaBot/{_VERSION} (+https://github.com/curia)",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                },
                timeout=config.timeout_seconds,
            )
        return self._client

    @staticmethod
    def _extract_same_origin_links(raw: bytes, page_url: str) -> list[str]:
        """Quick regex-free link extraction for discovery purposes."""
        from urllib.parse import urlparse

        from bs4 import BeautifulSoup

        soup = BeautifulSoup(raw, "lxml")
        origin = urlparse(page_url)
        links: list[str] = []

        for anchor in soup.find_all("a", href=True):
            href = anchor["href"]
            absolute = urljoin(page_url, href)
            parsed = urlparse(absolute)
            if parsed.netloc == origin.netloc:
                links.append(absolute)

        return links
