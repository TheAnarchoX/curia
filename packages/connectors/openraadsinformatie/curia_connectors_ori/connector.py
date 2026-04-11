"""OpenRaadsinformatie connector — implements the SourceConnector interface.

OpenRaadsinformatie (ORI) aggregates municipal, provincial, and water board
meeting data via an ElasticSearch API.  Unlike the scraping-based iBabs
connector, this one queries a structured JSON API.

API base: https://api.openraadsinformatie.nl/v1/
Docs:     https://github.com/openstate/open-raadsinformatie/blob/master/API-docs.md
Search:   https://zoek.openraadsinformatie.nl/
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
_BASE_URL = "https://api.openraadsinformatie.nl/v1"

# Index types available in the ORI API
INDEX_TYPES = (
    "events",  # meetings / vergaderingen
    "motions",  # moties
    "vote_events",  # stemmingen
    "organizations",  # councils, committees
    "persons",  # council members
)


class OpenRaadsinformatieConnector(SourceConnector):
    """Connector that queries the OpenRaadsinformatie ElasticSearch API."""

    def __init__(self) -> None:
        """Initialise the OpenRaadsinformatie connector."""
        self._checkpoint: dict[str, Any] = {}

    def get_meta(self) -> SourceConnectorMeta:
        """Return connector metadata."""
        return SourceConnectorMeta(
            source_type="openraadsinformatie",
            name="OpenRaadsinformatie",
            version=_VERSION,
            description=(
                "Open Council Data — aggregated meeting data from 300+ Dutch "
                "municipalities, provinces, and water boards"
            ),
            capabilities=[
                "meetings",
                "motions",
                "votes",
                "organisations",
                "persons",
                "documents",
            ],
        )

    async def discover_pages(self, config: CrawlConfig) -> list[str]:
        """Build API search URLs for each index type."""
        base = config.base_url or _BASE_URL
        return [f"{base.rstrip('/')}/{idx}/_search" for idx in INDEX_TYPES]

    async def crawl_page(self, url: str, config: CrawlConfig) -> CrawlResult:
        """Fetch a page of results from the ORI API.

        .. note:: Stub — not yet implemented.
        """
        raise NotImplementedError("OpenRaadsinformatieConnector.crawl_page is not yet implemented.")

    async def get_checkpoint(self) -> dict[str, Any]:
        """Return the current sync checkpoint."""
        return dict(self._checkpoint)

    async def set_checkpoint(self, checkpoint: dict[str, Any]) -> None:
        """Persist a sync checkpoint."""
        self._checkpoint = dict(checkpoint)
