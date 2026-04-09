"""Parser for individual iBabs agenda-item pages/sections."""

from __future__ import annotations

import re
from datetime import UTC, datetime
from urllib.parse import urljoin

from curia_ingestion.interfaces import CrawlResult, ParseResult, ParsedEntity

from curia_connectors_ibabs.models.pages import IbabsAgendaItem, IbabsDocumentLink
from curia_connectors_ibabs.parsers.base import IbabsParser

_AGENDA_ITEM_PATTERNS = (
    re.compile(r"/agenda[_-]?items?/\d+", re.IGNORECASE),
    re.compile(r"/agendapunt/\d+", re.IGNORECASE),
)


class IbabsAgendaItemParser(IbabsParser):
    """Parse a dedicated agenda-item page into structured data."""

    PARSER_NAME = "ibabs-agenda-item"
    PARSER_VERSION = "0.1.0"

    def can_parse(self, url: str, content_type: str) -> bool:
        if "text/html" not in content_type:
            return False
        return any(pat.search(url) for pat in _AGENDA_ITEM_PATTERNS)

    def parse(self, crawl_result: CrawlResult) -> ParseResult:
        soup = self._make_soup(crawl_result.raw_content or b"")
        entities: list[ParsedEntity] = []
        warnings: list[str] = []

        # --- Title & description -------------------------------------------------
        # TODO: Confirm selectors against live portal HTML
        title_el = soup.select_one("h1.agenda-title, h2.agenda-title, h1")
        desc_el = soup.select_one("div.agenda-description, div.item-body, div.content")

        title = self._extract_text(title_el)
        description = self._extract_text(desc_el)

        # --- Ordering (try to extract from breadcrumb / numbering) ---------------
        ordering_match = re.search(r"(\d+)", crawl_result.url.rstrip("/").rsplit("/", 1)[-1])
        ordering = int(ordering_match.group(1)) if ordering_match else 0

        # --- Documents -----------------------------------------------------------
        doc_links: list[IbabsDocumentLink] = []
        for anchor in soup.select("a.document-link, a[href*='document'], a[href$='.pdf']"):
            if anchor.has_attr("href"):
                doc_links.append(
                    IbabsDocumentLink(
                        title=self._extract_text(anchor),
                        url=urljoin(crawl_result.url, anchor["href"]),
                    )
                )

        # --- Sub-items -----------------------------------------------------------
        sub_items: list[IbabsAgendaItem] = []
        # TODO: Confirm sub-item selector against live portal
        sub_rows = soup.select("ul.sub-items li, div.sub-agenda-item")
        for sub_idx, sub_row in enumerate(sub_rows, start=1):
            sub_title_el = sub_row.select_one("a, span.title")
            sub_items.append(
                IbabsAgendaItem(
                    ordering=sub_idx,
                    title=self._extract_text(sub_title_el) or f"Sub-item {sub_idx}",
                )
            )

        item = IbabsAgendaItem(
            ordering=ordering,
            title=title or "(untitled agenda item)",
            description=description,
            sub_items=sub_items,
            document_links=doc_links,
        )

        entities.append(
            ParsedEntity(
                entity_type="agenda_item",
                source_url=crawl_result.url,
                external_id=str(ordering),
                data=item.model_dump(mode="json"),
            )
        )

        return ParseResult(
            source_url=crawl_result.url,
            parser_name=self.PARSER_NAME,
            parser_version=self.PARSER_VERSION,
            parsed_at=datetime.now(UTC),
            entities=entities,
            warnings=warnings,
        )
