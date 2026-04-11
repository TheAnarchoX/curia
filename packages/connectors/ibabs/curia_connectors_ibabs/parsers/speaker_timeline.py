"""Parser for iBabs speaker-timeline data within meetings."""

from __future__ import annotations

import re
from datetime import UTC, datetime

from curia_ingestion.interfaces import CrawlResult, ParsedEntity, ParseResult

from curia_connectors_ibabs.models.pages import IbabsSpeakerEvent
from curia_connectors_ibabs.parsers.base import IbabsParser

_SPEAKER_PATTERNS = (
    re.compile(r"/speakers?[_-]?timeline", re.IGNORECASE),
    re.compile(r"/spreektijden", re.IGNORECASE),
    re.compile(r"/meetings/\d+/speakers", re.IGNORECASE),
)


class IbabsSpeakerTimelineParser(IbabsParser):
    """Parse a speaker-timeline page into structured speaker events."""

    PARSER_NAME = "ibabs-speaker-timeline"
    PARSER_VERSION = "0.1.0"

    def can_parse(self, url: str, content_type: str) -> bool:
        """Check whether this parser handles the given URL and content type."""
        if "text/html" not in content_type:
            return False
        return any(pat.search(url) for pat in _SPEAKER_PATTERNS)

    def parse(self, crawl_result: CrawlResult) -> ParseResult:
        """Parse crawl result into structured entities."""
        soup = self._make_soup(crawl_result.raw_content or b"")
        entities: list[ParsedEntity] = []
        warnings: list[str] = []

        # TODO: Confirm selectors against live portal HTML
        rows = soup.select("table.speaker-timeline tbody tr, div.speaker-event, li.speaker-entry")

        if not rows:
            warnings.append("No speaker-timeline rows found — CSS selectors may need updating")

        for row in rows:
            name_el = row.select_one("td.speaker-name, span.speaker-name")
            party_el = row.select_one("td.party-name, span.party-name")
            start_el = row.select_one("td.start-time, span.start-time")
            end_el = row.select_one("td.end-time, span.end-time")
            duration_el = row.select_one("td.duration, span.duration")
            role_el = row.select_one("td.role, span.role")

            speaker_name = self._extract_text(name_el)
            if not speaker_name:
                continue

            party_name = self._extract_text(party_el) or None

            start_time = self._try_parse_time(self._extract_text(start_el))
            end_time = self._try_parse_time(self._extract_text(end_el))

            raw_dur = self._extract_text(duration_el)
            duration_seconds: float | None = None
            if raw_dur:
                dur_match = re.search(r"(\d+)", raw_dur)
                if dur_match:
                    duration_seconds = float(dur_match.group(1))

            role = self._extract_text(role_el) or None

            event = IbabsSpeakerEvent(
                speaker_name=speaker_name,
                party_name=party_name,
                start_time=start_time,
                end_time=end_time,
                duration_seconds=duration_seconds,
                role=role,
            )

            entities.append(
                ParsedEntity(
                    entity_type="speaker_event",
                    source_url=crawl_result.url,
                    external_id=f"{speaker_name}@{start_time or 'unknown'}",
                    data=event.model_dump(mode="json"),
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
    def _try_parse_time(raw: str) -> datetime | None:
        """Best-effort parse of a time string from the portal."""
        for fmt in ("%H:%M:%S", "%H:%M", "%d-%m-%Y %H:%M:%S", "%d-%m-%Y %H:%M"):
            try:
                return datetime.strptime(raw, fmt).replace(tzinfo=UTC)
            except (ValueError, TypeError):
                continue
        return None
