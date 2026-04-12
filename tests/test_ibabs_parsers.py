"""Fixture-based regression tests for iBabs HTML parsers."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
from bs4 import BeautifulSoup
from curia_connectors_ibabs.parsers.agenda_item import IbabsAgendaItemParser
from curia_connectors_ibabs.parsers.meeting_detail import IbabsMeetingDetailParser
from curia_connectors_ibabs.parsers.meeting_list import IbabsMeetingListParser
from curia_connectors_ibabs.parsers.member_roster import IbabsMemberRosterParser
from curia_ingestion.interfaces import CrawlResult

FIXTURES_ROOT = Path(__file__).resolve().parent / "fixtures" / "ibabs"


def _load_fixture(name: str, municipality: str) -> tuple[str, bytes]:
    metadata = json.loads((FIXTURES_ROOT / municipality / f"{name}.json").read_text(encoding="utf-8"))
    html = (FIXTURES_ROOT / municipality / f"{name}.html").read_bytes()
    return metadata["source_url"], html


def _crawl_result(url: str, html: bytes) -> CrawlResult:
    return CrawlResult(
        url=url,
        status_code=200,
        content_hash="fixture",
        fetched_at=datetime.now(UTC),
        content_type="text/html; charset=utf-8",
        raw_content=html,
    )


@pytest.mark.parametrize("municipality, expected_titles", [("almelo", 4), ("heerenveen", 3)])
def test_meeting_list_parser_extracts_fixture_meetings(municipality: str, expected_titles: int) -> None:
    """Meeting list parser should extract meetings from real calendar fixtures."""
    url, html = _load_fixture("meeting_list", municipality)
    parser = IbabsMeetingListParser()

    assert parser.can_parse(url, "text/html")

    result = parser.parse(_crawl_result(url, html))

    assert len(result.entities) >= expected_titles
    assert result.warnings == []
    assert result.entities[0].entity_type == "meeting_summary"
    assert result.entities[0].data["title"]
    assert result.entities[0].data["date"] == "2026-04-01"
    assert result.entities[0].data["url"].startswith(f"https://{municipality}.bestuurlijkeinformatie.nl/Agenda/Index/")


def test_meeting_list_parser_falls_back_to_legacy_table_markup() -> None:
    """Meeting list parser should keep working for non-calendar meeting table rows."""
    parser = IbabsMeetingListParser()
    html = b"""
    <table class="meetings">
      <tbody>
        <tr>
          <td class="date">01-04-2026</td>
          <td class="title"><a href="/Agenda/Index/legacy-1">Raadsvergadering</a></td>
          <td class="status">scheduled</td>
        </tr>
      </tbody>
    </table>
    """

    result = parser.parse(_crawl_result("https://example.test/meetings", html))

    assert result.warnings == []
    assert len(result.entities) == 1
    assert result.entities[0].data == {
        "title": "Raadsvergadering",
        "date": "2026-04-01",
        "url": "https://example.test/Agenda/Index/legacy-1",
        "meeting_id": "legacy-1",
        "status": "scheduled",
    }


@pytest.mark.parametrize(
    ("municipality", "expected_title", "expected_location", "expected_agenda_count", "expected_first_doc_title"),
    [
        ("almelo", "Raad", "Raadzaal", 7, "Aangepaste agenda buitengewone raadsvergadering 1 april 2026"),
        ("heerenveen", "Raadsvergadering", "Raadszaal", 11, None),
    ],
)
def test_meeting_detail_parser_extracts_fixture_content(
    municipality: str,
    expected_title: str,
    expected_location: str,
    expected_agenda_count: int,
    expected_first_doc_title: str | None,
) -> None:
    """Meeting detail parser should extract metadata, agenda items, and documents from fixtures."""
    url, html = _load_fixture("meeting_detail", municipality)
    parser = IbabsMeetingDetailParser()

    assert parser.can_parse(url, "text/html")

    result = parser.parse(_crawl_result(url, html))

    assert len(result.entities) == 1
    assert result.warnings == []

    detail = result.entities[0].data
    assert detail["title"] == expected_title
    assert detail["date"] == "2026-04-01"
    assert detail["location"] == expected_location
    assert len(detail["agenda_items"]) == expected_agenda_count
    assert detail["agenda_items"][0]["title"]
    assert detail["agenda_items"][0]["description"]
    if expected_first_doc_title is None:
        assert detail["documents"] == []
    else:
        assert detail["documents"][0]["title"] == expected_first_doc_title


@pytest.mark.parametrize(
    ("municipality", "expected_names"),
    [
        ("almelo", ["Gemeenteraad", "Raadsgriffie", "Wethouders"]),
        ("heerenveen", ["Gemeenteraad", "Algemene Zaken", "Commissieleden"]),
    ],
)
def test_member_roster_parser_extracts_people_directory_cards(
    municipality: str,
    expected_names: list[str],
) -> None:
    """Member roster parser should extract people-directory cards from fixtures."""
    url, html = _load_fixture("member_roster", municipality)
    parser = IbabsMemberRosterParser()

    assert parser.can_parse(url, "text/html")

    result = parser.parse(_crawl_result(url, html))

    names = [entity.data["name"] for entity in result.entities]
    assert result.warnings == []
    assert all(expected_name in names for expected_name in expected_names)
    assert all(entity.data["role"] for entity in result.entities)


@pytest.mark.parametrize(
    ("municipality", "expected_title", "expected_document_count"),
    [
        ("almelo", "Raadsbesluit toelating gemeenteraad 2026-2030", 2),
        ("heerenveen", "Vaststellen van de agenda", 1),
    ],
)
def test_agenda_item_parser_extracts_real_agenda_item_sections(
    municipality: str,
    expected_title: str,
    expected_document_count: int,
) -> None:
    """Agenda item parser should handle agenda item markup from real meeting-detail fixtures."""
    _, html = _load_fixture("meeting_detail", municipality)
    soup = BeautifulSoup(html, "lxml")
    agenda_rows = soup.select("div.panel.panel-default.agenda-item")
    target_row = agenda_rows[1] if municipality == "almelo" else agenda_rows[2]
    parser = IbabsAgendaItemParser()
    url = f"https://{municipality}.bestuurlijkeinformatie.nl/agendapunt/1"

    assert parser.can_parse(url, "text/html")

    result = parser.parse(_crawl_result(url, str(target_row).encode()))

    assert len(result.entities) == 1
    assert result.warnings == []

    agenda_item = result.entities[0].data
    assert agenda_item["title"] == expected_title
    assert agenda_item["ordering"] >= 1
    assert len(agenda_item["document_links"]) == expected_document_count
