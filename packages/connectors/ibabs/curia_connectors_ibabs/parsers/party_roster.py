"""Parser for iBabs party roster pages."""

from __future__ import annotations

import re
from datetime import UTC, datetime

from curia_ingestion.interfaces import CrawlResult, ParsedEntity, ParseResult

from curia_connectors_ibabs.models.pages import IbabsPartyRosterEntry
from curia_connectors_ibabs.parsers.base import IbabsParser

_PARTY_PATTERNS = (
    re.compile(r"/part(y|ies)/?(\?|$)", re.IGNORECASE),
    re.compile(r"/partijen/?(\?|$)", re.IGNORECASE),
    re.compile(r"/fracties/?(\?|$)", re.IGNORECASE),
)


class IbabsPartyRosterParser(IbabsParser):
    """Parse a party roster / factions overview page."""

    PARSER_NAME = "ibabs-party-roster"
    PARSER_VERSION = "0.1.0"

    def can_parse(self, url: str, content_type: str) -> bool:
        """Check whether this parser handles the given URL and content type."""
        if "text/html" not in content_type:
            return False
        return any(pat.search(url) for pat in _PARTY_PATTERNS)

    def parse(self, crawl_result: CrawlResult) -> ParseResult:
        """Parse crawl result into structured entities."""
        soup = self._make_soup(crawl_result.raw_content or b"")
        entities: list[ParsedEntity] = []
        warnings: list[str] = []

        # TODO: Confirm selectors against live portal HTML
        rows = soup.select("table.parties tbody tr, div.party-item, li.party-entry, div.fractie")

        if not rows:
            warnings.append("No party rows found — CSS selectors may need updating")

        for row in rows:
            name_el = row.select_one("td.party-name, span.party-name, h3.party-name, a.party-name")
            abbr_el = row.select_one("td.abbreviation, span.abbreviation")

            party_name = self._extract_text(name_el)
            if not party_name:
                continue

            abbreviation = self._extract_text(abbr_el) or None

            # Members listed inline (e.g. in a nested <ul>)
            member_els = row.select("ul.members li, span.member-name")
            members = [self._extract_text(m) for m in member_els if self._extract_text(m)]

            entry = IbabsPartyRosterEntry(
                party_name=party_name,
                abbreviation=abbreviation,
                members=members,
            )

            entities.append(
                ParsedEntity(
                    entity_type="party_roster",
                    source_url=crawl_result.url,
                    external_id=party_name,
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
