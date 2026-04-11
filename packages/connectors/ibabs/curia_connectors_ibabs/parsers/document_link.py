"""Parser for iBabs document-link sections."""

from __future__ import annotations

import re
from datetime import UTC, datetime
from urllib.parse import urljoin

from curia_ingestion.interfaces import CrawlResult, ParsedEntity, ParseResult

from curia_connectors_ibabs.models.pages import IbabsDocumentLink
from curia_connectors_ibabs.parsers.base import IbabsParser

_DOCUMENT_PATTERNS = (
    re.compile(r"/documents?/?(\?|$)", re.IGNORECASE),
    re.compile(r"/documenten/?(\?|$)", re.IGNORECASE),
    re.compile(r"/download/?(\?|$)", re.IGNORECASE),
)


class IbabsDocumentLinkParser(IbabsParser):
    """Parse a documents overview page into structured document-link entries."""

    PARSER_NAME = "ibabs-document-link"
    PARSER_VERSION = "0.1.0"

    def can_parse(self, url: str, content_type: str) -> bool:
        """Check whether this parser handles the given URL and content type."""
        if "text/html" not in content_type:
            return False
        return any(pat.search(url) for pat in _DOCUMENT_PATTERNS)

    def parse(self, crawl_result: CrawlResult) -> ParseResult:
        """Parse crawl result into structured entities."""
        soup = self._make_soup(crawl_result.raw_content or b"")
        entities: list[ParsedEntity] = []
        warnings: list[str] = []

        # TODO: Confirm selectors against live portal HTML
        rows = soup.select("table.documents tbody tr, div.document-item, li.document-entry, a.document-link")

        if not rows:
            warnings.append("No document rows found — CSS selectors may need updating")

        for row in rows:
            # If the matched element itself is an anchor, use it directly
            if row.name == "a" and row.has_attr("href"):
                anchor = row
            else:
                anchor = row.select_one("a[href]")

            if anchor is None or not anchor.has_attr("href"):
                continue

            title = self._extract_text(anchor)
            abs_url = urljoin(crawl_result.url, anchor["href"])

            # Try to extract MIME type from a sibling or data attribute
            mime_el = row.select_one("span.mime-type, td.type")
            mime_type = self._extract_text(mime_el) or self._guess_mime(abs_url)

            # Try to extract file size
            size_el = row.select_one("span.file-size, td.size")
            raw_size = self._extract_text(size_el)
            file_size = self._parse_size(raw_size)

            doc = IbabsDocumentLink(
                title=title or "(untitled document)",
                url=abs_url,
                mime_type=mime_type,
                file_size=file_size,
            )

            entities.append(
                ParsedEntity(
                    entity_type="document_link",
                    source_url=crawl_result.url,
                    external_id=abs_url,
                    data=doc.model_dump(mode="json"),
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

    @staticmethod
    def _guess_mime(url: str) -> str | None:
        """Guess MIME type from file extension."""
        ext_map = {
            ".pdf": "application/pdf",
            ".doc": "application/msword",
            ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            ".xls": "application/vnd.ms-excel",
            ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        }
        lower = url.lower()
        for ext, mime in ext_map.items():
            if lower.endswith(ext):
                return mime
        return None

    @staticmethod
    def _parse_size(raw: str) -> int | None:
        """Try to parse a human-readable file size like '1.2 MB' into bytes."""
        if not raw:
            return None
        match = re.search(r"([\d.,]+)\s*(KB|MB|GB|B)", raw, re.IGNORECASE)
        if not match:
            return None
        value = float(match.group(1).replace(",", "."))
        unit = match.group(2).upper()
        multipliers = {"B": 1, "KB": 1024, "MB": 1024**2, "GB": 1024**3}
        return int(value * multipliers.get(unit, 1))
