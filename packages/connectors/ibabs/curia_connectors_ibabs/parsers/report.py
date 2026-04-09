"""Parser for iBabs report / minutes pages."""

from __future__ import annotations

import re
from datetime import UTC, date, datetime
from urllib.parse import urljoin

from curia_ingestion.interfaces import CrawlResult, ParseResult, ParsedEntity

from curia_connectors_ibabs.models.pages import IbabsDocumentLink, IbabsReportEntry
from curia_connectors_ibabs.parsers.base import IbabsParser

_REPORT_PATTERNS = (
    re.compile(r"/reports?/?(\?|$)", re.IGNORECASE),
    re.compile(r"/verslagen/?(\?|$)", re.IGNORECASE),
    re.compile(r"/minutes/?(\?|$)", re.IGNORECASE),
    re.compile(r"/besluitenlijst", re.IGNORECASE),
)


class IbabsReportParser(IbabsParser):
    """Parse report listing pages into structured report entries."""

    PARSER_NAME = "ibabs-report"
    PARSER_VERSION = "0.1.0"

    def can_parse(self, url: str, content_type: str) -> bool:
        if "text/html" not in content_type:
            return False
        return any(pat.search(url) for pat in _REPORT_PATTERNS)

    def parse(self, crawl_result: CrawlResult) -> ParseResult:
        soup = self._make_soup(crawl_result.raw_content or b"")
        entities: list[ParsedEntity] = []
        warnings: list[str] = []

        # TODO: Confirm selectors against live portal HTML
        rows = soup.select(
            "table.reports tbody tr, "
            "div.report-item, "
            "li.report-entry"
        )

        if not rows:
            warnings.append(
                "No report rows found — CSS selectors may need updating"
            )

        for row in rows:
            title_el = row.select_one("td.title a, a.report-title, span.title a")
            date_el = row.select_one("td.date, span.report-date")
            type_el = row.select_one("td.type, span.report-type")

            title = self._extract_text(title_el)
            href = title_el["href"] if title_el and title_el.has_attr("href") else ""
            abs_url = urljoin(crawl_result.url, href) if href else crawl_result.url

            raw_date = self._extract_text(date_el)
            try:
                report_date = datetime.strptime(raw_date, "%d-%m-%Y").date()
            except (ValueError, TypeError):
                report_date = date(1970, 1, 1)
                if raw_date:
                    warnings.append(f"Unparseable date '{raw_date}' for report '{title}'")

            report_type = self._extract_text(type_el) or "unknown"

            # Inline document links within the row
            doc_links: list[IbabsDocumentLink] = []
            for anchor in row.select("a[href$='.pdf'], a.document-link"):
                if anchor.has_attr("href"):
                    doc_links.append(
                        IbabsDocumentLink(
                            title=self._extract_text(anchor),
                            url=urljoin(crawl_result.url, anchor["href"]),
                        )
                    )

            entry = IbabsReportEntry(
                title=title or "(untitled report)",
                date=report_date,
                url=abs_url,
                report_type=report_type,
                document_links=doc_links,
            )

            entities.append(
                ParsedEntity(
                    entity_type="report",
                    source_url=crawl_result.url,
                    external_id=href.rstrip("/").rsplit("/", 1)[-1] if href else title,
                    data=entry.model_dump(mode="json"),
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
