"""Tweede Kamer OData v4 connector — implements the SourceConnector interface.

The Tweede Kamer provides a rich OData v4 API at:
    https://gegevensmagazijn.tweedekamer.nl/OData/v4/2.0/

Unlike scraping-based connectors (iBabs, Eerste Kamer), this connector
consumes a structured API and returns JSON directly.  No HTML parsing
is required.

Key entities:
    Persoon, Fractie, Commissie, Vergadering, Zaak, Document, Stemming,
    Activiteit, Kamerstukdossier, Besluit, Agendapunt
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
_BASE_URL = "https://gegevensmagazijn.tweedekamer.nl/OData/v4/2.0"

# OData entity sets we intend to synchronise
ENTITIES = (
    "Persoon",
    "Fractie",
    "FractieZetel",
    "Commissie",
    "CommissieLid",
    "Vergadering",
    "Zaak",
    "ZaakActor",
    "Document",
    "DocumentActor",
    "Stemming",
    "Besluit",
    "Agendapunt",
    "Activiteit",
    "Kamerstukdossier",
)


class TweedeKamerConnector(SourceConnector):
    """Connector that synchronises data from the Tweede Kamer OData API."""

    def __init__(self) -> None:
        """Initialise the Tweede Kamer connector."""
        self._checkpoint: dict[str, Any] = {}

    # ------------------------------------------------------------------
    # SourceConnector interface
    # ------------------------------------------------------------------

    def get_meta(self) -> SourceConnectorMeta:
        """Return connector metadata."""
        return SourceConnectorMeta(
            source_type="tweedekamer",
            name="Tweede Kamer der Staten-Generaal",
            version=_VERSION,
            description="Official OData v4 API for the Dutch House of Representatives",
            capabilities=[
                "members",
                "parties",
                "committees",
                "sessions",
                "bills",
                "documents",
                "votes",
                "motions",
                "amendments",
            ],
        )

    async def discover_pages(self, config: CrawlConfig) -> list[str]:
        """Build OData entity-set URLs to synchronise."""
        base = config.base_url or _BASE_URL
        return [f"{base.rstrip('/')}/{entity}" for entity in ENTITIES]

    async def crawl_page(self, url: str, config: CrawlConfig) -> CrawlResult:
        """Fetch a single OData entity-set page.

        .. note:: Stub — returns an empty result.  The real implementation
           will page through OData ``@odata.nextLink`` responses.
        """
        raise NotImplementedError(
            "TweedeKamerConnector.crawl_page is not yet implemented. "
            "See https://github.com/TheAnarchoX/Curia/issues for the tracking task."
        )

    async def get_checkpoint(self) -> dict[str, Any]:
        """Return the current sync checkpoint."""
        return dict(self._checkpoint)

    async def set_checkpoint(self, checkpoint: dict[str, Any]) -> None:
        """Persist a sync checkpoint."""
        self._checkpoint = dict(checkpoint)
