"""Kiesraad connector — implements the SourceConnector interface.

The Kiesraad publishes official Dutch election results in EML
(Election Markup Language) format.  This connector downloads and
parses the EML files into structured election result data.

Data portal: https://data.overheid.nl (search "kiesraad")
Results DB:  https://www.kiesraad.nl/verkiezingen/verkiezingsuitslagen
GitHub tool: https://github.com/DIRKMJK/kiesraad (Python EML parser)
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
_BASE_URL = "https://data.overheid.nl/api/v3/datasets"

# Election types the Kiesraad publishes results for
ELECTION_TYPES = (
    "Tweede Kamer",
    "Eerste Kamer",
    "Provinciale Staten",
    "Gemeenteraad",
    "Waterschap",
    "Europees Parlement",
)


class KiesraadConnector(SourceConnector):
    """Connector that fetches official Dutch election results."""

    def __init__(self) -> None:
        """Initialise the Kiesraad connector."""
        self._checkpoint: dict[str, Any] = {}

    def get_meta(self) -> SourceConnectorMeta:
        """Return connector metadata."""
        return SourceConnectorMeta(
            source_type="kiesraad",
            name="Kiesraad (Dutch Electoral Council)",
            version=_VERSION,
            description=("Official election results for all Dutch elections since 2010"),
            capabilities=[
                "elections",
                "candidates",
                "parties",
                "results_per_municipality",
                "seat_allocations",
            ],
        )

    async def discover_pages(self, config: CrawlConfig) -> list[str]:
        """Discover election result dataset URLs from data.overheid.nl."""
        # Real implementation will query the CKAN API for Kiesraad datasets
        base = config.base_url or _BASE_URL
        return [f"{base}?q=kiesraad+verkiezingsuitslagen"]

    async def crawl_page(self, url: str, config: CrawlConfig) -> CrawlResult:
        """Fetch and parse an election result dataset.

        .. note:: Stub — not yet implemented.
        """
        raise NotImplementedError("KiesraadConnector.crawl_page is not yet implemented.")

    async def get_checkpoint(self) -> dict[str, Any]:
        """Return the current sync checkpoint."""
        return dict(self._checkpoint)

    async def set_checkpoint(self, checkpoint: dict[str, Any]) -> None:
        """Persist a sync checkpoint."""
        self._checkpoint = dict(checkpoint)
