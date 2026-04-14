"""Integration tests for Tweede Kamer bill and motion syncing."""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator, Generator

import curia_domain.db.models as _models  # noqa: F401
import httpx
import pytest
from curia_connectors_tweedekamer.connector import BillSyncResult, TweedeKamerConnector
from curia_connectors_tweedekamer.odata_client import ODataClient
from curia_domain.db.base import Base
from curia_domain.db.models import (
    AmendmentRow,
    BillRow,
    DocumentRow,
    GoverningBodyRow,
    InstitutionRow,
    JurisdictionRow,
    MotionRow,
    PoliticianRow,
)
from sqlalchemy import select
from sqlalchemy.dialects.sqlite.base import SQLiteTypeCompiler
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Deterministic UUIDs for test reproducibility
INSTITUTION_ID = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
GOVERNING_BODY_ID = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")

PERSON_1_ID = "97dd70f0-a4e0-42fa-98c4-7f44bbf5f46c"

ZAAK_BILL_ID = "11111111-1111-1111-1111-111111111111"
ZAAK_MOTIE_ID = "22222222-2222-2222-2222-222222222222"
ZAAK_AMEND_ID = "33333333-3333-3333-3333-333333333333"
ZAAK_OTHER_ID = "44444444-4444-4444-4444-444444444444"

DOC_1_ID = "55555555-5555-5555-5555-555555555555"
DOC_2_ID = "66666666-6666-6666-6666-666666666666"

DOSSIER_1_ID = "77777777-7777-7777-7777-777777777777"

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

        # Seed a politician for proposer resolution
        politician_1 = PoliticianRow(full_name="Myrthe Bikker")
        session.add(politician_1)
        await session.flush()

        session.info["politician_1"] = politician_1

        yield session

    await engine.dispose()


def _build_odata_handler(request: httpx.Request) -> httpx.Response:
    """Mock handler for OData requests returning Zaak, ZaakActor, Document, Kamerstukdossier."""
    path = request.url.path

    if path == "/OData/v4/2.0/Zaak":
        return httpx.Response(
            200,
            json={
                "value": [
                    {
                        "Id": ZAAK_BILL_ID,
                        "Soort": "Wetsvoorstel",
                        "Titel": "Wet duurzame energie",
                        "Onderwerp": "Bevordering duurzame energiebronnen",
                        "Status": "Aangenomen",
                        "GestartOp": "2025-03-01T00:00:00",
                        "Nummer": "36001",
                    },
                    {
                        "Id": ZAAK_MOTIE_ID,
                        "Soort": "Motie",
                        "Titel": "Motie-Bikker over duurzaam beleid",
                        "Onderwerp": "Verzoekt de regering duurzaam beleid te voeren",
                        "Status": "Aangenomen",
                    },
                    {
                        "Id": ZAAK_AMEND_ID,
                        "Soort": "Amendement",
                        "Titel": "Amendement-Bikker over windenergie",
                        "Onderwerp": "Wijziging artikel 5",
                        "Status": "Verworpen",
                    },
                    {
                        "Id": ZAAK_OTHER_ID,
                        "Soort": "Rondvraagpunt",
                        "Titel": "Overig punt",
                        "Status": "Aangemeld",
                    },
                ]
            },
            request=request,
        )

    if path == "/OData/v4/2.0/ZaakActor":
        return httpx.Response(
            200,
            json={
                "value": [
                    {
                        "Id": "aaaa0001-0001-0001-0001-000000000001",
                        "Zaak_Id": ZAAK_MOTIE_ID,
                        "ActorNaam": "Bikker",
                        "Relatie": "Indiener",
                        "Persoon_Id": PERSON_1_ID,
                    },
                ]
            },
            request=request,
        )

    if path == "/OData/v4/2.0/Document":
        return httpx.Response(
            200,
            json={
                "value": [
                    {
                        "Id": DOC_1_ID,
                        "Soort": "Wetsvoorstel",
                        "Titel": "Wet duurzame energie - tekst",
                        "ContentType": "application/pdf",
                    },
                    {
                        "Id": DOC_2_ID,
                        "Soort": "Motie",
                        "Titel": "Motie-Bikker over duurzaam beleid - tekst",
                        "ContentType": "application/pdf",
                    },
                ]
            },
            request=request,
        )

    if path == "/OData/v4/2.0/Kamerstukdossier":
        return httpx.Response(
            200,
            json={
                "value": [
                    {
                        "Id": DOSSIER_1_ID,
                        "Titel": "Duurzame energie",
                        "Nummer": 36001,
                    },
                ]
            },
            request=request,
        )

    raise AssertionError(f"Unexpected request: {request.method} {request.url}")


async def test_sync_bills_and_motions_creates_rows(
    async_session: AsyncSession,
) -> None:
    """The connector should create Bill, Motion, Amendment, and Document rows."""
    transport = httpx.MockTransport(_build_odata_handler)
    async with httpx.AsyncClient(transport=transport, base_url=TEST_BASE_URL) as http_client:
        client = ODataClient(base_url=TEST_BASE_URL, http_client=http_client)
        connector = TweedeKamerConnector()

        result = await connector.sync_bills_and_motions(
            async_session,
            governing_body_id=GOVERNING_BODY_ID,
            odata_client=client,
        )
        await async_session.commit()

    assert isinstance(result, BillSyncResult)
    assert result.fetched_zaken == 4
    assert result.fetched_documents == 2
    assert result.fetched_dossiers == 1
    assert result.bills_created == 1
    assert result.motions_created == 1
    assert result.amendments_created == 1
    assert result.documents_created == 2
    assert result.skipped == 1  # "Rondvraagpunt" is not a recognised type

    # Check Bill row
    bills = (await async_session.execute(select(BillRow))).scalars().all()
    assert len(bills) == 1
    assert bills[0].title == "Wet duurzame energie"
    assert bills[0].status == "adopted"
    assert bills[0].external_id == ZAAK_BILL_ID
    assert bills[0].governing_body_id == GOVERNING_BODY_ID

    # Check Motion row
    motions = (await async_session.execute(select(MotionRow))).scalars().all()
    assert len(motions) == 1
    assert motions[0].title == "Motie-Bikker over duurzaam beleid"
    assert motions[0].status == "adopted"

    # Check Amendment row
    amendments = (await async_session.execute(select(AmendmentRow))).scalars().all()
    assert len(amendments) == 1
    assert amendments[0].title == "Amendement-Bikker over windenergie"
    assert amendments[0].status == "rejected"

    # Check Document rows
    documents = (await async_session.execute(select(DocumentRow))).scalars().all()
    assert len(documents) == 2
    doc_titles = sorted(d.title for d in documents if d.title)
    assert "Motie-Bikker over duurzaam beleid - tekst" in doc_titles
    assert "Wet duurzame energie - tekst" in doc_titles


async def test_sync_bills_and_motions_is_idempotent(
    async_session: AsyncSession,
) -> None:
    """Running sync_bills_and_motions twice should not duplicate rows."""
    transport = httpx.MockTransport(_build_odata_handler)
    async with httpx.AsyncClient(transport=transport, base_url=TEST_BASE_URL) as http_client:
        client = ODataClient(base_url=TEST_BASE_URL, http_client=http_client)
        connector = TweedeKamerConnector()

        first = await connector.sync_bills_and_motions(
            async_session,
            governing_body_id=GOVERNING_BODY_ID,
            odata_client=client,
        )
        await async_session.commit()

        second = await connector.sync_bills_and_motions(
            async_session,
            governing_body_id=GOVERNING_BODY_ID,
            odata_client=client,
        )
        await async_session.commit()

    assert first.bills_created == 1
    assert first.motions_created == 1
    assert first.amendments_created == 1
    assert first.documents_created == 2

    # Second run: everything should already exist
    assert second.bills_created == 0
    assert second.bills_existing == 1
    assert second.motions_created == 0
    assert second.motions_existing == 1
    assert second.amendments_created == 0
    assert second.amendments_existing == 1
    assert second.documents_created == 0
    assert second.documents_existing == 2

    # Totals should not have doubled
    bills = (await async_session.execute(select(BillRow))).scalars().all()
    assert len(bills) == 1
    motions = (await async_session.execute(select(MotionRow))).scalars().all()
    assert len(motions) == 1
    amendments = (await async_session.execute(select(AmendmentRow))).scalars().all()
    assert len(amendments) == 1
    documents = (await async_session.execute(select(DocumentRow))).scalars().all()
    assert len(documents) == 2


async def test_sync_bills_skips_deleted_zaken(
    async_session: AsyncSession,
) -> None:
    """Deleted Zaak records (Verwijderd=true) should be skipped."""

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path == "/OData/v4/2.0/Zaak":
            return httpx.Response(
                200,
                json={
                    "value": [
                        {
                            "Id": ZAAK_BILL_ID,
                            "Soort": "Wetsvoorstel",
                            "Titel": "Deleted Bill",
                            "Verwijderd": True,
                        }
                    ]
                },
                request=request,
            )
        if path in (
            "/OData/v4/2.0/ZaakActor",
            "/OData/v4/2.0/Document",
            "/OData/v4/2.0/Kamerstukdossier",
        ):
            return httpx.Response(200, json={"value": []}, request=request)
        raise AssertionError(f"Unexpected request: {request.url}")

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport, base_url=TEST_BASE_URL) as http_client:
        client = ODataClient(base_url=TEST_BASE_URL, http_client=http_client)
        connector = TweedeKamerConnector()
        result = await connector.sync_bills_and_motions(
            async_session,
            governing_body_id=GOVERNING_BODY_ID,
            odata_client=client,
        )

    assert result.skipped == 1
    assert result.bills_created == 0


def test_map_zaak_status_converts_dutch_labels() -> None:
    """Dutch Zaak status labels should map to BillStatus values."""
    assert TweedeKamerConnector._map_zaak_status("Aangenomen") == "adopted"
    assert TweedeKamerConnector._map_zaak_status("Verworpen") == "rejected"
    assert TweedeKamerConnector._map_zaak_status("Ingetrokken") == "withdrawn"
    assert TweedeKamerConnector._map_zaak_status("In behandeling") == "committee"
    assert TweedeKamerConnector._map_zaak_status(None) == "other"
    assert TweedeKamerConnector._map_zaak_status("Onbekend") == "other"


def test_map_document_soort_converts_types() -> None:
    """Dutch Document.Soort values should map to DocumentType values."""
    assert TweedeKamerConnector._map_document_soort("Wetsvoorstel") == "bill"
    assert TweedeKamerConnector._map_document_soort("Motie") == "motion"
    assert TweedeKamerConnector._map_document_soort("Amendement") == "amendment"
    assert TweedeKamerConnector._map_document_soort("Verslag") == "report"
    assert TweedeKamerConnector._map_document_soort(None) == "other"
    assert TweedeKamerConnector._map_document_soort("Brief") == "other"


def test_resolve_proposer_ids_links_indiener_actors() -> None:
    """ZaakActor records with Relatie 'Indiener' should be resolved to politician IDs."""
    from curia_connectors_tweedekamer.odata_client import ZaakActor as ODataZaakActor

    pol_row = PoliticianRow(full_name="Test Politician")
    pol_row.id = uuid.UUID("eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee")
    persoon_id = uuid.UUID(PERSON_1_ID)

    actors = [
        ODataZaakActor.model_validate({"Relatie": "Indiener", "Persoon_Id": PERSON_1_ID}),
        ODataZaakActor.model_validate({"Relatie": "Rapporteur", "Persoon_Id": PERSON_1_ID}),
    ]
    politician_map = {persoon_id: pol_row}

    result = TweedeKamerConnector._resolve_proposer_ids(actors, politician_map=politician_map)
    assert result == [pol_row.id]
