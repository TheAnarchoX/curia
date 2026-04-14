"""Integration tests for Tweede Kamer committee and session syncing."""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator, Generator

import curia_domain.db.models as _models  # noqa: F401
import httpx
import pytest
from curia_connectors_tweedekamer.connector import CommitteeSessionSyncResult, TweedeKamerConnector
from curia_connectors_tweedekamer.odata_client import ODataClient
from curia_domain.db.base import Base
from curia_domain.db.models import (
    AgendaItemRow,
    GoverningBodyRow,
    InstitutionRow,
    JurisdictionRow,
    MeetingRow,
)
from sqlalchemy import select
from sqlalchemy.dialects.sqlite.base import SQLiteTypeCompiler
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Deterministic UUIDs for test reproducibility
INSTITUTION_ID = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
GOVERNING_BODY_ID = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")

COMMISSIE_1_ID = "11111111-1111-1111-1111-111111111111"
COMMISSIE_2_ID = "22222222-2222-2222-2222-222222222222"
COMMISSIE_ZETEL_1_ID = "33333333-3333-3333-3333-333333333333"

VERGADERING_1_ID = "44444444-4444-4444-4444-444444444444"
VERGADERING_2_ID = "55555555-5555-5555-5555-555555555555"

ACTIVITEIT_1_ID = "66666666-6666-6666-6666-666666666666"
ACTIVITEIT_2_ID = "77777777-7777-7777-7777-777777777777"

AGENDAPUNT_1_ID = "88888888-8888-8888-8888-888888888888"
AGENDAPUNT_2_ID = "99999999-9999-9999-9999-999999999999"

TEST_BASE_URL = "https://example.test/OData/v4/2.0/"


@pytest.fixture(autouse=True)
def _patch_sqlite_type_compiler() -> Generator[None, None, None]:
    """Teach SQLite how to compile PostgreSQL-only column types for tests."""
    orig_array = getattr(SQLiteTypeCompiler, "visit_ARRAY", None)
    orig_jsonb = getattr(SQLiteTypeCompiler, "visit_JSONB", None)

    setattr(SQLiteTypeCompiler, "visit_ARRAY", lambda self, type_, **kw: "TEXT")
    setattr(SQLiteTypeCompiler, "visit_JSONB", lambda self, type_, **kw: "TEXT")

    yield

    if orig_array is None:
        delattr(SQLiteTypeCompiler, "visit_ARRAY")
    else:
        setattr(SQLiteTypeCompiler, "visit_ARRAY", orig_array)
    if orig_jsonb is None:
        delattr(SQLiteTypeCompiler, "visit_JSONB")
    else:
        setattr(SQLiteTypeCompiler, "visit_JSONB", orig_jsonb)


@pytest.fixture
async def async_session() -> AsyncIterator[AsyncSession]:
    """Yield an async session backed by in-memory SQLite with seed data."""
    engine = create_async_engine("sqlite+aiosqlite://", echo=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with factory() as session:
        jurisdiction = JurisdictionRow(name="Nederland", level="national")
        session.add(jurisdiction)
        await session.flush()

        institution = InstitutionRow(
            id=INSTITUTION_ID,
            jurisdiction_id=jurisdiction.id,
            name="Tweede Kamer der Staten-Generaal",
            slug="tweede-kamer",
            institution_type="chamber",
        )
        session.add(institution)
        await session.flush()

        governing_body = GoverningBodyRow(
            id=GOVERNING_BODY_ID,
            institution_id=institution.id,
            name="Plenaire zaal",
            body_type="plenary",
        )
        session.add(governing_body)
        await session.flush()

        yield session

    await engine.dispose()


def _build_odata_handler(request: httpx.Request) -> httpx.Response:
    """Mock handler for OData requests returning committees, sessions, and agenda items."""
    path = request.url.path

    if path == "/OData/v4/2.0/Commissie":
        return httpx.Response(
            200,
            json={
                "value": [
                    {
                        "Id": COMMISSIE_1_ID,
                        "Nummer": 1,
                        "Soort": "Vast",
                        "Afkorting": "BuZa",
                        "NaamNL": "Vaste commissie voor Buitenlandse Zaken",
                        "DatumActief": "2023-01-01T00:00:00",
                    },
                    {
                        "Id": COMMISSIE_2_ID,
                        "Nummer": 2,
                        "Soort": "Algemeen",
                        "NaamNL": "Algemene commissie voor Financiën",
                        "DatumActief": "2023-06-15T00:00:00",
                        "DatumInactief": "2025-12-31T00:00:00",
                    },
                ]
            },
            request=request,
        )

    if path == "/OData/v4/2.0/CommissieZetel":
        return httpx.Response(
            200,
            json={
                "value": [
                    {
                        "Id": COMMISSIE_ZETEL_1_ID,
                        "Gewicht": 10000,
                        "Commissie_Id": COMMISSIE_1_ID,
                    },
                ]
            },
            request=request,
        )

    if path == "/OData/v4/2.0/Vergadering":
        return httpx.Response(
            200,
            json={
                "value": [
                    {
                        "Id": VERGADERING_1_ID,
                        "Soort": "Plenair",
                        "Titel": "Plenaire vergadering nr. 42",
                        "Zaal": "Plenaire zaal",
                        "VergaderingNummer": 42,
                        "Datum": "2025-03-10T00:00:00",
                        "Aanvangstijd": "2025-03-10T10:00:00",
                        "Sluiting": "2025-03-10T18:00:00",
                    },
                    {
                        "Id": VERGADERING_2_ID,
                        "Soort": "Plenair",
                        "Titel": "Plenaire vergadering nr. 43",
                        "Zaal": "Plenaire zaal",
                        "VergaderingNummer": 43,
                        "Datum": "2025-03-17T00:00:00",
                        "Aanvangstijd": "2025-03-17T10:00:00",
                    },
                ]
            },
            request=request,
        )

    if path == "/OData/v4/2.0/Activiteit":
        return httpx.Response(
            200,
            json={
                "value": [
                    {
                        "Id": ACTIVITEIT_1_ID,
                        "Soort": "Commissiedebat",
                        "Onderwerp": "Debat over klimaatbeleid",
                        "Datum": "2025-03-11T00:00:00",
                        "Aanvangstijd": "2025-03-11T14:00:00",
                        "Eindtijd": "2025-03-11T17:00:00",
                        "Locatie": "Thorbeckezaal",
                        "Status": "Gereed",
                        "Voortouwcommissie_Id": COMMISSIE_1_ID,
                    },
                    {
                        "Id": ACTIVITEIT_2_ID,
                        "Soort": "Hoorzitting",
                        "Onderwerp": "Hoorzitting begrotingsbeleid",
                        "Datum": "2025-03-12T00:00:00",
                        "Aanvangstijd": "2025-03-12T09:00:00",
                        "Status": "Gepland",
                    },
                ]
            },
            request=request,
        )

    if path == "/OData/v4/2.0/Agendapunt":
        return httpx.Response(
            200,
            json={
                "value": [
                    {
                        "Id": AGENDAPUNT_1_ID,
                        "Nummer": "1",
                        "Onderwerp": "Opening en mededelingen",
                        "Volgorde": 1,
                        "Noot": "Procedureel",
                        "Activiteit_Id": ACTIVITEIT_1_ID,
                    },
                    {
                        "Id": AGENDAPUNT_2_ID,
                        "Nummer": "2",
                        "Onderwerp": "Klimaatnota bespreking",
                        "Volgorde": 2,
                        "Activiteit_Id": ACTIVITEIT_1_ID,
                    },
                ]
            },
            request=request,
        )

    raise AssertionError(f"Unexpected request: {request.method} {request.url}")


async def test_sync_committees_and_sessions_creates_rows(
    async_session: AsyncSession,
) -> None:
    """The connector should create committee, meeting, and agenda item rows."""
    transport = httpx.MockTransport(_build_odata_handler)
    async with httpx.AsyncClient(transport=transport, base_url=TEST_BASE_URL) as http_client:
        client = ODataClient(base_url=TEST_BASE_URL, http_client=http_client)
        connector = TweedeKamerConnector()

        result = await connector.sync_committees_and_sessions(
            async_session,
            institution_id=INSTITUTION_ID,
            governing_body_id=GOVERNING_BODY_ID,
            odata_client=client,
        )
        await async_session.commit()

    assert isinstance(result, CommitteeSessionSyncResult)
    assert result.fetched_commissies == 2
    assert result.fetched_commissiezetels == 1
    assert result.fetched_vergaderingen == 2
    assert result.fetched_activiteiten == 2
    assert result.fetched_agendapunten == 2
    assert result.committees_created == 2
    assert result.meetings_created == 4  # 2 vergaderingen + 2 activiteiten
    assert result.agenda_items_created == 2

    # Check committee GoverningBody rows
    committees = (
        (
            await async_session.execute(
                select(GoverningBodyRow).where(
                    GoverningBodyRow.institution_id == INSTITUTION_ID,
                    GoverningBodyRow.body_type.in_(["committee", "other"]),
                )
            )
        )
        .scalars()
        .all()
    )
    assert len(committees) == 2
    committee_names = sorted(c.name for c in committees)
    assert "Algemene commissie voor Financiën" in committee_names
    assert "Vaste commissie voor Buitenlandse Zaken" in committee_names

    # Check Meeting rows
    meetings = (await async_session.execute(select(MeetingRow))).scalars().all()
    assert len(meetings) == 4
    meeting_titles = sorted(m.title for m in meetings if m.title)
    assert "Debat over klimaatbeleid" in meeting_titles
    assert "Hoorzitting begrotingsbeleid" in meeting_titles
    assert "Plenaire vergadering nr. 42" in meeting_titles
    assert "Plenaire vergadering nr. 43" in meeting_titles

    # Vergadering 1 should be completed (has Sluiting)
    verg1 = next(m for m in meetings if m.title == "Plenaire vergadering nr. 42")
    assert verg1.status == "completed"
    assert verg1.location == "Plenaire zaal"
    assert verg1.governing_body_id == GOVERNING_BODY_ID

    # Vergadering 2 should be scheduled (no Sluiting)
    verg2 = next(m for m in meetings if m.title == "Plenaire vergadering nr. 43")
    assert verg2.status == "scheduled"

    # Activiteit 1 should be linked to the BuZa committee
    act1 = next(m for m in meetings if m.title == "Debat over klimaatbeleid")
    buza = next(c for c in committees if "Buitenlandse Zaken" in c.name)
    assert act1.governing_body_id == buza.id
    assert act1.status == "completed"

    # Activiteit 2 has no committee link, should use plenary body
    act2 = next(m for m in meetings if m.title == "Hoorzitting begrotingsbeleid")
    assert act2.governing_body_id == GOVERNING_BODY_ID
    assert act2.status == "scheduled"

    # Check AgendaItem rows
    agenda_items = (await async_session.execute(select(AgendaItemRow))).scalars().all()
    assert len(agenda_items) == 2
    item_titles = sorted(ai.title for ai in agenda_items)
    assert "Klimaatnota bespreking" in item_titles
    assert "Opening en mededelingen" in item_titles

    # Agenda items should be linked to the committee activity meeting
    for ai in agenda_items:
        assert ai.meeting_id == act1.id


async def test_sync_committees_and_sessions_is_idempotent(
    async_session: AsyncSession,
) -> None:
    """Running sync_committees_and_sessions twice should not duplicate rows."""
    transport = httpx.MockTransport(_build_odata_handler)
    async with httpx.AsyncClient(transport=transport, base_url=TEST_BASE_URL) as http_client:
        client = ODataClient(base_url=TEST_BASE_URL, http_client=http_client)
        connector = TweedeKamerConnector()

        first = await connector.sync_committees_and_sessions(
            async_session,
            institution_id=INSTITUTION_ID,
            governing_body_id=GOVERNING_BODY_ID,
            odata_client=client,
        )
        await async_session.commit()

        second = await connector.sync_committees_and_sessions(
            async_session,
            institution_id=INSTITUTION_ID,
            governing_body_id=GOVERNING_BODY_ID,
            odata_client=client,
        )
        await async_session.commit()

    assert first.committees_created == 2
    assert first.meetings_created == 4
    assert first.agenda_items_created == 2

    # Second run: everything should already exist
    assert second.committees_created == 0
    assert second.committees_existing == 2
    assert second.meetings_created == 0
    assert second.meetings_existing == 4
    assert second.agenda_items_created == 0
    assert second.agenda_items_existing == 2

    # Totals should not have doubled
    committees = (
        (
            await async_session.execute(
                select(GoverningBodyRow).where(
                    GoverningBodyRow.institution_id == INSTITUTION_ID,
                    GoverningBodyRow.body_type.in_(["committee", "other"]),
                )
            )
        )
        .scalars()
        .all()
    )
    assert len(committees) == 2

    meetings = (await async_session.execute(select(MeetingRow))).scalars().all()
    assert len(meetings) == 4

    agenda_items = (await async_session.execute(select(AgendaItemRow))).scalars().all()
    assert len(agenda_items) == 2


async def test_sync_committees_skips_deleted(
    async_session: AsyncSession,
) -> None:
    """Deleted records (Verwijderd=true) should be skipped."""

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path == "/OData/v4/2.0/Commissie":
            return httpx.Response(
                200,
                json={
                    "value": [
                        {
                            "Id": COMMISSIE_1_ID,
                            "NaamNL": "Deleted Committee",
                            "Verwijderd": True,
                        }
                    ]
                },
                request=request,
            )
        if path in (
            "/OData/v4/2.0/CommissieZetel",
            "/OData/v4/2.0/Vergadering",
            "/OData/v4/2.0/Activiteit",
            "/OData/v4/2.0/Agendapunt",
        ):
            return httpx.Response(200, json={"value": []}, request=request)
        raise AssertionError(f"Unexpected request: {request.url}")

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport, base_url=TEST_BASE_URL) as http_client:
        client = ODataClient(base_url=TEST_BASE_URL, http_client=http_client)
        connector = TweedeKamerConnector()
        result = await connector.sync_committees_and_sessions(
            async_session,
            institution_id=INSTITUTION_ID,
            governing_body_id=GOVERNING_BODY_ID,
            odata_client=client,
        )

    assert result.skipped == 1
    assert result.committees_created == 0


def test_map_commissie_soort_converts_types() -> None:
    """Dutch Commissie.Soort values should map to GoverningBodyType values."""
    assert TweedeKamerConnector._map_commissie_soort("Vast") == "committee"
    assert TweedeKamerConnector._map_commissie_soort("Algemeen") == "committee"
    assert TweedeKamerConnector._map_commissie_soort("Bijzonder") == "committee"
    assert TweedeKamerConnector._map_commissie_soort("Overig") == "other"
    assert TweedeKamerConnector._map_commissie_soort(None) == "committee"


def test_map_activiteit_status_converts_statuses() -> None:
    """Dutch Activiteit.Status values should map to MeetingStatus values."""
    assert TweedeKamerConnector._map_activiteit_status("Gepland") == "scheduled"
    assert TweedeKamerConnector._map_activiteit_status("Gereed") == "completed"
    assert TweedeKamerConnector._map_activiteit_status("Afgelast") == "cancelled"
    assert TweedeKamerConnector._map_activiteit_status("Uitgesteld") == "postponed"
    assert TweedeKamerConnector._map_activiteit_status(None) == "scheduled"
    assert TweedeKamerConnector._map_activiteit_status("Onbekend") == "scheduled"
