"""Integration tests for Tweede Kamer vote syncing."""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator, Generator

import curia_domain.db.models as _models  # noqa: F401
import httpx
import pytest
from curia_connectors_tweedekamer.connector import TweedeKamerConnector, VoteSyncResult
from curia_connectors_tweedekamer.odata_client import ODataClient, Stemming
from curia_domain.db.base import Base
from curia_domain.db.models import (
    DecisionRow,
    GoverningBodyRow,
    InstitutionRow,
    JurisdictionRow,
    MeetingRow,
    PartyRow,
    PoliticianRow,
    VoteRecordRow,
    VoteRow,
)
from sqlalchemy import select
from sqlalchemy.dialects.sqlite.base import SQLiteTypeCompiler
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Fixed UUIDs for test reproducibility
INSTITUTION_ID = uuid.uuid4()
GOVERNING_BODY_ID = uuid.uuid4()
MEETING_ID = uuid.uuid4()

PERSON_1_ID = "97dd70f0-a4e0-42fa-98c4-7f44bbf5f46c"
PERSON_2_ID = "8ef86d15-bbd2-4d50-8450-2669e0f50a20"
PARTY_CU_ID = "11fc67aa-7f75-4251-b974-c90d55793f43"
PARTY_VVD_ID = "eaac8e85-90c8-4fb4-a33f-1dd18f72b038"

BESLUIT_1_ID = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
STEMMING_1_ID = "11111111-1111-1111-1111-111111111111"
STEMMING_2_ID = "22222222-2222-2222-2222-222222222222"
STEMMING_3_ID = "33333333-3333-3333-3333-333333333333"

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

        meeting = MeetingRow(
            id=MEETING_ID,
            governing_body_id=governing_body.id,
        )
        session.add(meeting)
        await session.flush()

        # Seed parties and politicians that the vote sync will reference
        party_cu = PartyRow(name="ChristenUnie", abbreviation="CU")
        party_vvd = PartyRow(name="VVD", abbreviation="VVD")
        session.add_all([party_cu, party_vvd])
        await session.flush()

        politician_1 = PoliticianRow(full_name="Myrthe Bikker")
        politician_2 = PoliticianRow(full_name="Pieter van Vliet")
        session.add_all([politician_1, politician_2])
        await session.flush()

        # Store for use in tests (via stash)
        session.info["party_cu"] = party_cu
        session.info["party_vvd"] = party_vvd
        session.info["politician_1"] = politician_1
        session.info["politician_2"] = politician_2

        yield session

    await engine.dispose()


def _build_odata_handler(request: httpx.Request) -> httpx.Response:
    """Mock handler for OData requests returning Besluit and Stemming entities."""
    if request.url.path == "/OData/v4/2.0/Besluit":
        return httpx.Response(
            200,
            json={
                "value": [
                    {
                        "Id": BESLUIT_1_ID,
                        "StemmingsSoort": "Hoofdelijk",
                        "BesluitSoort": "Motie",
                        "BesluitTekst": "Motie-Bikker over duurzaam beleid",
                        "Status": "Aangenomen",
                    }
                ]
            },
            request=request,
        )

    if request.url.path == "/OData/v4/2.0/Stemming":
        assert request.url.params.get("$expand") == "StemmingsSoort", (
            "Stemming should be fetched with $expand=StemmingsSoort"
        )
        return httpx.Response(
            200,
            json={
                "value": [
                    {
                        "Id": STEMMING_1_ID,
                        "Besluit_Id": BESLUIT_1_ID,
                        "Soort": "Voor",
                        "ActorNaam": "Bikker",
                        "ActorFractie": "ChristenUnie",
                        "FractieGrootte": 5,
                        "Persoon_Id": PERSON_1_ID,
                        "Fractie_Id": PARTY_CU_ID,
                        "Vergissing": False,
                    },
                    {
                        "Id": STEMMING_2_ID,
                        "Besluit_Id": BESLUIT_1_ID,
                        "Soort": "Tegen",
                        "ActorNaam": "van Vliet",
                        "ActorFractie": "VVD",
                        "FractieGrootte": 24,
                        "Persoon_Id": PERSON_2_ID,
                        "Fractie_Id": PARTY_VVD_ID,
                        "Vergissing": False,
                    },
                    {
                        "Id": STEMMING_3_ID,
                        "Besluit_Id": BESLUIT_1_ID,
                        "Soort": "Niet deelgenomen",
                        "ActorNaam": None,
                        "ActorFractie": None,
                        "FractieGrootte": 2,
                        "Vergissing": False,
                    },
                ]
            },
            request=request,
        )

    raise AssertionError(f"Unexpected request: {request.method} {request.url}")


async def test_sync_votes_persists_decisions_votes_and_records(
    async_session: AsyncSession,
) -> None:
    """The connector should create Decision, Vote, and VoteRecord rows."""
    party_cu: PartyRow = async_session.info["party_cu"]
    party_vvd: PartyRow = async_session.info["party_vvd"]
    politician_1: PoliticianRow = async_session.info["politician_1"]
    politician_2: PoliticianRow = async_session.info["politician_2"]

    politician_map = {
        uuid.UUID(PERSON_1_ID): politician_1,
        uuid.UUID(PERSON_2_ID): politician_2,
    }
    party_map = {
        uuid.UUID(PARTY_CU_ID): party_cu,
        uuid.UUID(PARTY_VVD_ID): party_vvd,
    }

    transport = httpx.MockTransport(_build_odata_handler)
    async with httpx.AsyncClient(transport=transport, base_url=TEST_BASE_URL) as http_client:
        client = ODataClient(base_url=TEST_BASE_URL, http_client=http_client)
        connector = TweedeKamerConnector()

        result = await connector.sync_votes(
            async_session,
            meeting_id=MEETING_ID,
            politician_map=politician_map,
            party_map=party_map,
            odata_client=client,
        )
        await async_session.commit()

    assert isinstance(result, VoteSyncResult)
    assert result.fetched_besluiten == 1
    assert result.fetched_stemmingen == 3
    assert result.decisions_created == 1
    assert result.votes_created == 1
    assert result.records_created == 3
    assert result.skipped == 0

    # Check Decision row
    decisions = (await async_session.execute(select(DecisionRow))).scalars().all()
    assert len(decisions) == 1
    assert decisions[0].meeting_id == MEETING_ID
    assert decisions[0].decision_type == "vote"
    assert decisions[0].description == "Motie-Bikker over duurzaam beleid"

    # Check Vote row (aggregate)
    votes = (await async_session.execute(select(VoteRow))).scalars().all()
    assert len(votes) == 1
    assert votes[0].decision_id == decisions[0].id
    assert votes[0].proposition_type == "Hoofdelijk"
    assert votes[0].votes_for == 5
    assert votes[0].votes_against == 24
    assert votes[0].votes_abstain == 2
    assert votes[0].outcome == "rejected"

    # Check VoteRecord rows (individual)
    records = (await async_session.execute(select(VoteRecordRow).order_by(VoteRecordRow.value))).scalars().all()
    assert len(records) == 3

    values = sorted(r.value for r in records)
    assert values == ["against", "for", "not_participated"]

    # The "for" record should link to politician_1 and party_cu
    for_record = next(r for r in records if r.value == "for")
    assert for_record.politician_id == politician_1.id
    assert for_record.party_id == party_cu.id
    assert for_record.party_size == 5
    assert for_record.is_mistake is False

    # The "not_participated" record has no politician or party link
    abstain_record = next(r for r in records if r.value == "not_participated")
    assert abstain_record.politician_id is None
    assert abstain_record.party_id is None
    assert abstain_record.party_size == 2


async def test_sync_votes_is_idempotent(
    async_session: AsyncSession,
) -> None:
    """Running sync_votes twice should not duplicate rows."""
    party_cu: PartyRow = async_session.info["party_cu"]
    party_vvd: PartyRow = async_session.info["party_vvd"]
    politician_1: PoliticianRow = async_session.info["politician_1"]
    politician_2: PoliticianRow = async_session.info["politician_2"]

    politician_map = {
        uuid.UUID(PERSON_1_ID): politician_1,
        uuid.UUID(PERSON_2_ID): politician_2,
    }
    party_map = {
        uuid.UUID(PARTY_CU_ID): party_cu,
        uuid.UUID(PARTY_VVD_ID): party_vvd,
    }

    transport = httpx.MockTransport(_build_odata_handler)
    async with httpx.AsyncClient(transport=transport, base_url=TEST_BASE_URL) as http_client:
        client = ODataClient(base_url=TEST_BASE_URL, http_client=http_client)
        connector = TweedeKamerConnector()

        first = await connector.sync_votes(
            async_session,
            meeting_id=MEETING_ID,
            politician_map=politician_map,
            party_map=party_map,
            odata_client=client,
        )
        await async_session.commit()

        second = await connector.sync_votes(
            async_session,
            meeting_id=MEETING_ID,
            politician_map=politician_map,
            party_map=party_map,
            odata_client=client,
        )
        await async_session.commit()

    assert first.decisions_created == 1
    assert first.votes_created == 1
    assert first.records_created == 3

    # Second run: everything should already exist
    assert second.decisions_created == 0
    assert second.decisions_existing == 1
    assert second.votes_created == 0
    assert second.votes_existing == 1
    assert second.records_created == 0
    assert second.records_existing == 3

    # Totals should not have doubled
    decisions = (await async_session.execute(select(DecisionRow))).scalars().all()
    assert len(decisions) == 1
    votes = (await async_session.execute(select(VoteRow))).scalars().all()
    assert len(votes) == 1
    records = (await async_session.execute(select(VoteRecordRow))).scalars().all()
    assert len(records) == 3


async def test_sync_votes_skips_deleted_stemmingen(
    async_session: AsyncSession,
) -> None:
    """Deleted Stemming records (Verwijderd=true) should be skipped."""
    politician_map: dict[uuid.UUID, PoliticianRow] = {}
    party_map: dict[uuid.UUID, PartyRow] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/OData/v4/2.0/Besluit":
            return httpx.Response(200, json={"value": []}, request=request)
        if request.url.path == "/OData/v4/2.0/Stemming":
            return httpx.Response(
                200,
                json={
                    "value": [
                        {
                            "Id": STEMMING_1_ID,
                            "Besluit_Id": BESLUIT_1_ID,
                            "Soort": "Voor",
                            "Verwijderd": True,
                        }
                    ]
                },
                request=request,
            )
        raise AssertionError(f"Unexpected request: {request.url}")

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport, base_url=TEST_BASE_URL) as http_client:
        client = ODataClient(base_url=TEST_BASE_URL, http_client=http_client)
        connector = TweedeKamerConnector()
        result = await connector.sync_votes(
            async_session,
            meeting_id=MEETING_ID,
            politician_map=politician_map,
            party_map=party_map,
            odata_client=client,
        )

    assert result.skipped == 1
    assert result.records_created == 0


def test_map_stemming_soort_converts_dutch_labels() -> None:
    """Dutch vote labels should map to normalised English values."""
    assert TweedeKamerConnector._map_stemming_soort("Voor") == "for"
    assert TweedeKamerConnector._map_stemming_soort("Tegen") == "against"
    assert TweedeKamerConnector._map_stemming_soort("Niet deelgenomen") == "not_participated"
    assert TweedeKamerConnector._map_stemming_soort(None) == "unknown"
    assert TweedeKamerConnector._map_stemming_soort("Onbekend") == "unknown"


def test_aggregate_stemming_computes_totals() -> None:
    """Aggregate helper should sum faction sizes and determine outcome."""
    stemmingen = [
        Stemming.model_validate({"Soort": "Voor", "FractieGrootte": 80}),
        Stemming.model_validate({"Soort": "Tegen", "FractieGrootte": 60}),
        Stemming.model_validate({"Soort": "Niet deelgenomen", "FractieGrootte": 10}),
    ]
    result = TweedeKamerConnector._aggregate_stemming(stemmingen)
    assert result["votes_for"] == 80
    assert result["votes_against"] == 60
    assert result["votes_abstain"] == 10
    assert result["outcome"] == "adopted"


def test_aggregate_stemming_rejected_outcome() -> None:
    """Votes with more against than for should be rejected."""
    stemmingen = [
        Stemming.model_validate({"Soort": "Voor", "FractieGrootte": 30}),
        Stemming.model_validate({"Soort": "Tegen", "FractieGrootte": 120}),
    ]
    result = TweedeKamerConnector._aggregate_stemming(stemmingen)
    assert result["outcome"] == "rejected"


def test_aggregate_stemming_tied_outcome() -> None:
    """Equal for/against counts should produce a tied outcome."""
    stemmingen = [
        Stemming.model_validate({"Soort": "Voor", "FractieGrootte": 75}),
        Stemming.model_validate({"Soort": "Tegen", "FractieGrootte": 75}),
    ]
    result = TweedeKamerConnector._aggregate_stemming(stemmingen)
    assert result["outcome"] == "tied"
