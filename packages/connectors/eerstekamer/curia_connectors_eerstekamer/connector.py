"""Eerste Kamer connector — implements the SourceConnector interface.

The Eerste Kamer (Dutch Senate) does not provide an official API.
This connector scrapes data from eerstekamer.nl and supplements it
with structured data from OpenSanctions and official publications.

Website:       https://www.eerstekamer.nl
OpenSanctions: https://www.opensanctions.org/datasets/nl_senate/
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
_BASE_URL = "https://www.eerstekamer.nl"

# Sections of the Eerste Kamer website to scrape
SECTIONS = (
    "/leden",  # current members
    "/commissies",  # committees
    "/wetsvoorstellen",  # legislative proposals
    "/plenaire-vergaderingen",  # plenary sessions
)


class EersteKamerConnector(SourceConnector):
    """Connector that scrapes data from the Eerste Kamer website."""

    def __init__(self) -> None:
        """Initialise the Eerste Kamer connector."""
        self._checkpoint: dict[str, Any] = {}

    def get_meta(self) -> SourceConnectorMeta:
        """Return connector metadata."""
        return SourceConnectorMeta(
            source_type="eerstekamer",
            name="Eerste Kamer der Staten-Generaal",
            version=_VERSION,
            description="Dutch Senate — scraped from eerstekamer.nl",
            capabilities=[
                "members",
                "committees",
                "legislation",
                "sessions",
            ],
        )

    async def discover_pages(self, config: CrawlConfig) -> list[str]:
        """Build seed URLs from known Eerste Kamer website sections."""
        base = config.base_url or _BASE_URL
        return [f"{base.rstrip('/')}{section}" for section in SECTIONS]

    async def crawl_page(self, url: str, config: CrawlConfig) -> CrawlResult:
        """Fetch and parse a page from the Eerste Kamer website.

        .. note:: Stub — not yet implemented.
        """
        raise NotImplementedError("EersteKamerConnector.crawl_page is not yet implemented.")

    async def get_checkpoint(self) -> dict[str, Any]:
        """Return the current sync checkpoint."""
        return dict(self._checkpoint)

    async def set_checkpoint(self, checkpoint: dict[str, Any]) -> None:
        """Persist a sync checkpoint."""
        self._checkpoint = dict(checkpoint)
