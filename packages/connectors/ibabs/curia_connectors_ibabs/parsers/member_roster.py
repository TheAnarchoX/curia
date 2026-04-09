"""Parser for iBabs member roster pages."""

from __future__ import annotations

import re
from datetime import UTC, date, datetime

from curia_ingestion.interfaces import CrawlResult, ParseResult, ParsedEntity

from curia_connectors_ibabs.models.pages import IbabsMemberRosterEntry
from curia_connectors_ibabs.parsers.base import IbabsParser

_MEMBER_PATTERNS = (
    re.compile(r"/members?/?(\?|$)", re.IGNORECASE),
    re.compile(r"/leden/?(\?|$)", re.IGNORECASE),
    re.compile(r"/raadsleden/?(\?|$)", re.IGNORECASE),
    re.compile(r"/commissieleden/?(\?|$)", re.IGNORECASE),
)


class IbabsMemberRosterParser(IbabsParser):
    """Parse a member roster page into structured member entries."""

    PARSER_NAME = "ibabs-member-roster"
    PARSER_VERSION = "0.1.0"

    def can_parse(self, url: str, content_type: str) -> bool:
        if "text/html" not in content_type:
            return False
        return any(pat.search(url) for pat in _MEMBER_PATTERNS)

    def parse(self, crawl_result: CrawlResult) -> ParseResult:
        soup = self._make_soup(crawl_result.raw_content or b"")
        entities: list[ParsedEntity] = []
        warnings: list[str] = []

        # TODO: Confirm selectors against live portal HTML
        rows = soup.select(
            "table.members tbody tr, "
            "div.member-item, "
            "li.member-entry, "
            "div.raadslid"
        )

        if not rows:
            warnings.append(
                "No member rows found — CSS selectors may need updating"
            )

        for row in rows:
            name_el = row.select_one(
                "td.member-name, span.member-name, h3.member-name, a.member-name"
            )
            party_el = row.select_one("td.party, span.party-name")
            role_el = row.select_one("td.role, span.role")
            from_el = row.select_one("td.active-from, span.active-from")
            until_el = row.select_one("td.active-until, span.active-until")
            photo_el = row.select_one("img.photo, img.member-photo")

            name = self._extract_text(name_el)
            if not name:
                continue

            party_name = self._extract_text(party_el) or None
            role = self._extract_text(role_el) or None

            active_from = self._try_parse_date(self._extract_text(from_el))
            active_until = self._try_parse_date(self._extract_text(until_el))

            photo_url: str | None = None
            if photo_el and photo_el.has_attr("src"):
                from urllib.parse import urljoin

                photo_url = urljoin(crawl_result.url, photo_el["src"])

            entry = IbabsMemberRosterEntry(
                name=name,
                party_name=party_name,
                role=role,
                active_from=active_from,
                active_until=active_until,
                photo_url=photo_url,
            )

            entities.append(
                ParsedEntity(
                    entity_type="member_roster",
                    source_url=crawl_result.url,
                    external_id=name,
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

    @staticmethod
    def _try_parse_date(raw: str) -> date | None:
        """Best-effort date parsing."""
        for fmt in ("%d-%m-%Y", "%Y-%m-%d", "%d/%m/%Y"):
            try:
                return datetime.strptime(raw, fmt).date()
            except (ValueError, TypeError):
                continue
        return None
