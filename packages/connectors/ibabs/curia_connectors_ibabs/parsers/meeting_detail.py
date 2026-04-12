"""Parser for iBabs meeting detail pages."""

from __future__ import annotations

import re
from datetime import UTC, date, datetime
from urllib.parse import urljoin

from curia_ingestion.interfaces import CrawlResult, ParsedEntity, ParseResult

from curia_connectors_ibabs.models.pages import (
    IbabsAgendaItem,
    IbabsDocumentLink,
    IbabsMeetingDetail,
)
from curia_connectors_ibabs.parsers.base import IbabsParser

_MEETING_DETAIL_PATTERNS = (
    re.compile(r"/meetings/\d+", re.IGNORECASE),
    re.compile(r"/vergaderingen/\d+", re.IGNORECASE),
    re.compile(r"/meeting/detail/", re.IGNORECASE),
    re.compile(r"/agenda/index/[0-9a-f-]+/?(\?.*)?$", re.IGNORECASE),
)


class IbabsMeetingDetailParser(IbabsParser):
    """Extract full meeting details including agenda items and documents."""

    PARSER_NAME = "ibabs-meeting-detail"
    PARSER_VERSION = "0.1.0"

    def can_parse(self, url: str, content_type: str) -> bool:
        """Check whether this parser handles the given URL and content type."""
        if "text/html" not in content_type:
            return False
        return any(pat.search(url) for pat in _MEETING_DETAIL_PATTERNS)

    def parse(self, crawl_result: CrawlResult) -> ParseResult:
        """Parse crawl result into structured entities."""
        soup = self._make_soup(crawl_result.raw_content or b"")
        entities: list[ParsedEntity] = []
        warnings: list[str] = []

        # --- Title & metadata ---------------------------------------------------
        # TODO: Confirm selectors against live portal HTML
        title_el = soup.select_one("div.box-header h1, h1.meeting-title, h1, div.meeting-header h1")
        title = self._extract_text(title_el)

        date_el = soup.select_one("div.box-header h2, span.meeting-date, div.meeting-date, time")
        raw_date = self._extract_text(date_el)
        meeting_date = self._try_parse_date(raw_date)
        if meeting_date is None:
            meeting_date = date(1970, 1, 1)
            if raw_date:
                warnings.append(f"Unparseable date '{raw_date}'")

        location = ""
        for term in soup.select("dl dt"):
            if self._extract_text(term).lower() == "locatie":
                location = self._extract_text(term.find_next_sibling("dd"))
                break

        meeting_id = crawl_result.url.rstrip("/").rsplit("/", 1)[-1]

        # --- Agenda items --------------------------------------------------------
        agenda_items: list[IbabsAgendaItem] = []
        # TODO: Confirm agenda row selector against live portal
        agenda_rows = soup.select("div.agenda-item, tr.agenda-item, li.agenda-item")
        for idx, row in enumerate(agenda_rows, start=1):
            item_title_el = row.select_one("span.panel-title-label, span.item-title, a.item-title, td.title")
            item_desc_el = row.select_one("div.panel-body > div.row .col-12.text, div.item-description, td.description")
            doc_anchors = row.select("ul.list-attachments a[href], a.document-link, a[href*='document']")

            item_title = self._extract_text(item_title_el, exclude_selectors=(".text-thin",)).rstrip(" -")

            doc_links = [
                IbabsDocumentLink(
                    title=self._extract_text(a, exclude_selectors=(".badge", ".icon", ".sr-only")),
                    url=urljoin(crawl_result.url, a["href"]),
                )
                for a in doc_anchors
                if a.has_attr("href")
            ]

            agenda_items.append(
                IbabsAgendaItem(
                    ordering=idx,
                    title=item_title or f"Item {idx}",
                    description=self._extract_text(item_desc_el),
                    document_links=doc_links,
                )
            )

        # --- Top-level documents -------------------------------------------------
        documents: list[IbabsDocumentLink] = []
        for term in soup.select("dl dt"):
            if self._extract_text(term).lower() != "agenda documenten":
                continue
            doc_section = term.find_next_sibling("dd")
            if doc_section is None:
                continue
            for a in doc_section.select("a[href]"):
                documents.append(
                    IbabsDocumentLink(
                        title=self._extract_text(
                            a,
                            exclude_selectors=(".badge", ".icon", ".sr-only"),
                        ),
                        url=urljoin(crawl_result.url, a["href"]),
                    )
                )
            break

        detail = IbabsMeetingDetail(
            title=title or "(untitled meeting)",
            date=meeting_date,
            location=location,
            url=crawl_result.url,
            meeting_id=meeting_id,
            agenda_items=agenda_items,
            documents=documents,
        )

        entities.append(
            ParsedEntity(
                entity_type="meeting_detail",
                source_url=crawl_result.url,
                external_id=meeting_id,
                data=detail.model_dump(mode="json"),
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
