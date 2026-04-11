"""Woogle / WOO connector — implements the SourceConnector interface.

Woogle indexes government documents published under the Wet open
overheid (WOO), the Dutch Freedom of Information Act.  The search
engine at woogle.wooverheid.nl currently holds 8M+ documents from
nearly 800 government bodies.

There is no standardised public REST API yet, but the data is
accessible via web scraping and emerging FAIR/linked-data APIs.
This connector will initially focus on document search and metadata
retrieval.
"""

from __future__ import annotations

from typing import Any

from curia_ingestion.interfaces import (
    CrawlConfig,
    CrawlResult,
    SourceConnector,
    SourceConnectorMeta,
)

_VERSION = "0.1.0"
_BASE_URL = "https://woogle.wooverheid.nl"


class WoogleConnector(SourceConnector):
    """Connector for Woogle government document search."""

    def __init__(self) -> None:
        """Initialise the Woogle connector."""
        self._checkpoint: dict[str, Any] = {}

    def get_meta(self) -> SourceConnectorMeta:
        """Return connector metadata."""
        return SourceConnectorMeta(
            source_type="woogle",
            name="Woogle (WOO Government Documents)",
            version=_VERSION,
            description=(
                "Government documents published under the Dutch Freedom of Information Act (Wet open overheid)"
            ),
            capabilities=[
                "documents",
                "decisions",
                "policy_documents",
                "search",
            ],
        )

    async def discover_pages(self, config: CrawlConfig) -> list[str]:
        """Discover document search result pages.

        .. note:: Stub — the real implementation will construct search
           queries based on tracked government bodies and topics.
        """
        return []

    async def crawl_page(self, url: str, config: CrawlConfig) -> CrawlResult:
        """Fetch a page of Woogle search results.

        .. note:: Stub — not yet implemented.
        """
        raise NotImplementedError("WoogleConnector.crawl_page is not yet implemented.")

    async def get_checkpoint(self) -> dict[str, Any]:
        """Return the current sync checkpoint."""
        return dict(self._checkpoint)

    async def set_checkpoint(self, checkpoint: dict[str, Any]) -> None:
        """Persist a sync checkpoint."""
        self._checkpoint = dict(checkpoint)
