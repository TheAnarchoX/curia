"""Integration tests for Tweede Kamer member and party syncing."""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator, Generator
from datetime import date

import curia_domain.db.models as _models  # noqa: F401
import httpx
import pytest
from curia_connectors_tweedekamer.connector import TweedeKamerConnector
from curia_connectors_tweedekamer.odata_client import ODataClient
from curia_domain.db.base import Base
from curia_domain.db.models import (
    GoverningBodyRow,
    InstitutionRow,
    JurisdictionRow,
    MandateRow,
    PartyRow,
    PoliticianRow,
)
from sqlalchemy import select
from sqlalchemy.dialects.sqlite.base import SQLiteTypeCompiler
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

INSTITUTION_ID = uuid.uuid4()
GOVERNING_BODY_ID = uuid.uuid4()
PERSON_1_ID = "97dd70f0-a4e0-42fa-98c4-7f44bbf5f46c"
PERSON_2_ID = "8ef86d15-bbd2-4d50-8450-2669e0f50a20"
PARTY_1_ID = "11fc67aa-7f75-4251-b974-c90d55793f43"
PARTY_2_ID = "eaac8e85-90c8-4fb4-a33f-1dd18f72b038"


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
    """Yield an async session backed by in-memory SQLite."""
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


async def test_sync_members_and_parties_persists_people_parties_and_memberships(
    async_session: AsyncSession,
) -> None:
    """The connector should persist Persoon, Fractie, and FractieZetel memberships."""

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/OData/v4/2.0/Persoon":
            return httpx.Response(
                200,
                json={
                    "value": [
                        {
                            "Id": PERSON_1_ID,
                            "Initialen": "M.",
                            "Roepnaam": "Myrthe",
                            "Achternaam": "Bikker",
                            "Geslacht": "vrouw",
                            "Geboortedatum": "1982-06-15",
                            "Functie": "Kamerlid",
                        },
                        {
                            "Id": PERSON_2_ID,
                            "Voornamen": "Pieter",
                            "Tussenvoegsel": "van",
                            "Achternaam": "Vliet",
                            "Geslacht": "man",
                            "Geboortedatum": "1979-01-02",
                            "Functie": "Voormalig Kamerlid",
                        },
                    ]
                },
                request=request,
            )

        if request.url.path == "/OData/v4/2.0/Fractie":
            return httpx.Response(
                200,
                json={
                    "value": [
                        {
                            "Id": PARTY_1_ID,
                            "Afkorting": "CU",
                            "NaamNL": "ChristenUnie",
                            "DatumActief": "2001-01-01T00:00:00Z",
                        },
                        {
                            "Id": PARTY_2_ID,
                            "Afkorting": "VVD",
                            "NaamNL": "Volkspartij voor Vrijheid en Democratie",
                            "DatumActief": "1948-01-24T00:00:00Z",
                            "DatumInactief": "2024-12-31T00:00:00Z",
                        },
                    ]
                },
                request=request,
            )

        if request.url.path == "/OData/v4/2.0/FractieZetel":
            assert request.url.params["$expand"] == "FractieZetelPersoon"
            return httpx.Response(
                200,
                json={
                    "value": [
                        {
                            "Id": "c61160d6-9e11-4ba3-ac84-3a0fcf761a8f",
                            "Fractie_Id": PARTY_1_ID,
                            "FractieZetelPersoon": [
                                {
                                    "Id": "b0c1d2d4-9408-4630-b2d6-bbda07d96514",
                                    "Persoon_Id": PERSON_1_ID,
                                    "Functie": "Voorzitter",
                                    "Van": "2023-12-06T00:00:00Z",
                                }
                            ],
                        },
                        {
                            "Id": "42dfd93d-bf10-40dd-a36f-b4e1e8982cb3",
                            "Fractie_Id": PARTY_2_ID,
                            "FractieZetelPersoon": [
                                {
                                    "Id": "cd07850e-a0b1-49d0-814f-763302fa302e",
                                    "Persoon_Id": PERSON_2_ID,
                                    "Functie": "Lid",
                                    "Van": "2021-03-31T00:00:00Z",
                                    "TotEnMet": "2023-12-05T00:00:00Z",
                                }
                            ],
                        },
                    ]
                },
                request=request,
            )

        raise AssertionError(f"Unexpected request: {request.method} {request.url}")

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport, base_url="https://example.test/OData/v4/2.0/") as http_client:
        client = ODataClient(base_url="https://example.test/OData/v4/2.0/", http_client=http_client)
        connector = TweedeKamerConnector()

        first = await connector.sync_members_and_parties(
            async_session,
            institution_id=INSTITUTION_ID,
            governing_body_id=GOVERNING_BODY_ID,
            odata_client=client,
        )
        await async_session.commit()

        second = await connector.sync_members_and_parties(
            async_session,
            institution_id=INSTITUTION_ID,
            governing_body_id=GOVERNING_BODY_ID,
            odata_client=client,
        )
        await async_session.commit()

    assert first.created == 6
    assert first.updated == 0
    assert first.skipped == 0
    assert first.fetched_people == 2
    assert first.fetched_parties == 2
    assert first.fetched_memberships == 2

    assert second.created == 0
    assert second.updated == 6
    assert second.skipped == 0

    parties = (await async_session.execute(select(PartyRow).order_by(PartyRow.name))).scalars().all()
    assert [party.name for party in parties] == [
        "ChristenUnie",
        "Volkspartij voor Vrijheid en Democratie",
    ]
    assert parties[0].abbreviation == "CU"
    assert parties[0].active_from == date(2001, 1, 1)
    assert parties[1].active_until == date(2024, 12, 31)

    politicians = (
        await async_session.execute(select(PoliticianRow).order_by(PoliticianRow.full_name))
    ).scalars().all()
    assert [politician.full_name for politician in politicians] == ["Myrthe Bikker", "Pieter van Vliet"]
    assert politicians[0].gender == "vrouw"
    assert politicians[1].notes == "Voormalig Kamerlid"

    mandates = (await async_session.execute(select(MandateRow).order_by(MandateRow.start_date))).scalars().all()
    assert len(mandates) == 2
    assert mandates[0].role == "member"
    assert mandates[0].start_date == date(2021, 3, 31)
    assert mandates[0].end_date == date(2023, 12, 5)
    assert mandates[1].role == "chair"
    assert mandates[1].start_date == date(2023, 12, 6)
    assert all(mandate.institution_id == INSTITUTION_ID for mandate in mandates)
    assert all(mandate.governing_body_id == GOVERNING_BODY_ID for mandate in mandates)
