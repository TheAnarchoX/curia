"""Parser for iBabs meeting list pages."""

from __future__ import annotations

import re
from datetime import UTC, date, datetime
from urllib.parse import urljoin

from curia_ingestion.interfaces import CrawlResult, ParsedEntity, ParseResult

from curia_connectors_ibabs.models.pages import IbabsMeetingListPage, IbabsMeetingSummary
from curia_connectors_ibabs.parsers.base import IbabsParser

_MEETING_LIST_PATTERNS = (
    re.compile(r"/meetings/?(\?|$)", re.IGNORECASE),
    re.compile(r"/vergaderingen/?(\?|$)", re.IGNORECASE),
    re.compile(r"/calendar/?(\?|$)", re.IGNORECASE),
)


class IbabsMeetingListParser(IbabsParser):
    """Extract meeting summaries from an iBabs meetings overview page."""

    PARSER_NAME = "ibabs-meeting-list"
    PARSER_VERSION = "0.1.0"

    def can_parse(self, url: str, content_type: str) -> bool:
        """Check whether this parser handles the given URL and content type."""
        if "text/html" not in content_type:
            return False
        return any(pat.search(url) for pat in _MEETING_LIST_PATTERNS)

    def parse(self, crawl_result: CrawlResult) -> ParseResult:
        """Parse crawl result into structured entities."""
        soup = self._make_soup(crawl_result.raw_content or b"")
        entities: list[ParsedEntity] = []
        warnings: list[str] = []

        # TODO: Replace selectors with real portal-specific CSS selectors after
        # analysing live iBabs HTML. The structure below mirrors the typical
        # iBabs DOM: a table or repeated <div> blocks per meeting.
        rows = soup.select("table.meetings tbody tr, div.meeting-item")

        if not rows:
            warnings.append("No meeting rows found — CSS selectors may need updating for this portal variant")

        meetings: list[IbabsMeetingSummary] = []
        for row in rows:
            title_el = row.select_one("td.title a, a.meeting-title")
            date_el = row.select_one("td.date, span.meeting-date")
            status_el = row.select_one("td.status, span.meeting-status")

            title = self._extract_text(title_el)
            href = title_el["href"] if title_el and title_el.has_attr("href") else ""
            abs_url = urljoin(crawl_result.url, href) if href else crawl_result.url

            raw_date = self._extract_text(date_el)
            try:
                meeting_date = datetime.strptime(raw_date, "%d-%m-%Y").date()
            except (ValueError, TypeError):
                meeting_date = date(1970, 1, 1)
                if raw_date:
                    warnings.append(f"Unparseable date '{raw_date}' for meeting '{title}'")

            meeting_id = href.rstrip("/").rsplit("/", 1)[-1] if href else title
            status = self._extract_text(status_el) or "unknown"

            summary = IbabsMeetingSummary(
                title=title or "(untitled)",
                date=meeting_date,
                url=abs_url,
                meeting_id=meeting_id,
                status=status,
            )
            meetings.append(summary)

            entities.append(
                ParsedEntity(
                    entity_type="meeting_summary",
                    source_url=crawl_result.url,
                    external_id=summary.meeting_id,
                    data=summary.model_dump(mode="json"),
                )
            )

        # Pagination
        next_link = soup.select_one("a.next-page, li.next a, a[rel='next']")
        next_page_url: str | None = None
        if next_link and next_link.has_attr("href"):
            next_page_url = urljoin(crawl_result.url, next_link["href"])

        _page = IbabsMeetingListPage(meetings=meetings, next_page_url=next_page_url)

        return ParseResult(
            source_url=crawl_result.url,
            parser_name=self.PARSER_NAME,
            parser_version=self.PARSER_VERSION,
            parsed_at=datetime.now(UTC),
            entities=entities,
            warnings=warnings,
        )
