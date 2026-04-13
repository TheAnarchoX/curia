"""Integration tests for IbabsEntityMapper using in-memory SQLite."""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from datetime import UTC, datetime

import curia_domain.db.models as _models  # noqa: F401
import pytest
from curia_connectors_ibabs.mapper import IbabsEntityMapper
from curia_domain.db.base import Base
from curia_domain.db.models import (
    DecisionRow,
    DocumentRow,
    GoverningBodyRow,
    InstitutionRow,
    JurisdictionRow,
    MeetingRow,
    MotionRow,
    PartyRow,
    PoliticianRow,
    VoteRow,
)
from curia_ingestion.interfaces import ParsedEntity, ParseResult
from sqlalchemy import select
from sqlalchemy.dialects.sqlite.base import SQLiteTypeCompiler
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

GOVERNING_BODY_ID = uuid.uuid4()


@pytest.fixture(autouse=True)
def _patch_sqlite_type_compiler() -> AsyncIterator[None]:
    """Temporarily patch SQLiteTypeCompiler to handle PostgreSQL-only types.

    This avoids leaking the patch into unrelated tests that may rely on the
    default compiler behaviour in the same pytest process.
    """
    orig_array = getattr(SQLiteTypeCompiler, "visit_ARRAY", None)
    orig_jsonb = getattr(SQLiteTypeCompiler, "visit_JSONB", None)

    SQLiteTypeCompiler.visit_ARRAY = lambda self, type_, **kw: "TEXT"  # type: ignore[assignment]
    SQLiteTypeCompiler.visit_JSONB = lambda self, type_, **kw: "TEXT"  # type: ignore[assignment]

    yield

    # Restore originals (or delete if they didn't exist).
    if orig_array is None:
        delattr(SQLiteTypeCompiler, "visit_ARRAY")
    else:
        SQLiteTypeCompiler.visit_ARRAY = orig_array  # type: ignore[assignment]
    if orig_jsonb is None:
        delattr(SQLiteTypeCompiler, "visit_JSONB")
    else:
        SQLiteTypeCompiler.visit_JSONB = orig_jsonb  # type: ignore[assignment]


@pytest.fixture
async def async_session() -> AsyncIterator[AsyncSession]:
    """Yield an async SQLAlchemy session backed by in-memory SQLite."""
    engine = create_async_engine("sqlite+aiosqlite://", echo=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with factory() as session:
        # Seed the minimal parent rows required by FK constraints.
        jurisdiction = JurisdictionRow(name="Test Municipality", level="municipality")
        session.add(jurisdiction)
        await session.flush()

        institution = InstitutionRow(
            name="Council",
            slug="test-municipality-council",
            institution_type="council",
            jurisdiction_id=jurisdiction.id,
        )
        session.add(institution)
        await session.flush()

        governing_body = GoverningBodyRow(
            id=GOVERNING_BODY_ID,
            name="Municipal Council",
            body_type="council",
            institution_id=institution.id,
        )
        session.add(governing_body)
        await session.flush()

        yield session

    await engine.dispose()


def _make_parse_result(
    entities: list[ParsedEntity],
    parser_name: str = "test-parser",
) -> ParseResult:
    """Build a minimal ParseResult for testing."""
    return ParseResult(
        source_url="https://test.ibabs.eu/test",
        parser_name=parser_name,
        parser_version="0.1.0",
        parsed_at=datetime.now(UTC),
        entities=entities,
    )


# ---------------------------------------------------------------------------
# Party
# ---------------------------------------------------------------------------


async def test_upsert_party_creates_new_row(async_session: AsyncSession) -> None:
    """A party_roster entity should create a new PartyRow."""
    mapper = IbabsEntityMapper(async_session, GOVERNING_BODY_ID)

    pr = _make_parse_result(
        [
            ParsedEntity(
                entity_type="party_roster",
                source_url="https://test.ibabs.eu",
                external_id="VVD",
                data={"party_name": "VVD", "abbreviation": "VVD", "members": []},
            ),
        ]
    )

    result = await mapper.map_and_persist(pr)
    assert result.created == 1
    assert result.updated == 0

    row = (await async_session.execute(select(PartyRow).where(PartyRow.name == "VVD"))).scalar_one()
    assert row.abbreviation == "VVD"


async def test_upsert_party_updates_existing_row(async_session: AsyncSession) -> None:
    """Re-crawling the same party should update rather than duplicate."""
    mapper = IbabsEntityMapper(async_session, GOVERNING_BODY_ID)

    entity = ParsedEntity(
        entity_type="party_roster",
        source_url="https://test.ibabs.eu",
        external_id="D66",
        data={"party_name": "D66", "abbreviation": None, "members": []},
    )

    # First insert
    r1 = await mapper.map_and_persist(_make_parse_result([entity]))
    assert r1.created == 1

    # Second pass with updated abbreviation — should update, not duplicate
    entity_v2 = ParsedEntity(
        entity_type="party_roster",
        source_url="https://test.ibabs.eu",
        external_id="D66",
        data={"party_name": "D66", "abbreviation": "D66", "members": []},
    )
    r2 = await mapper.map_and_persist(_make_parse_result([entity_v2]))
    assert r2.updated == 1

    rows = (await async_session.execute(select(PartyRow).where(PartyRow.name == "D66"))).scalars().all()
    assert len(rows) == 1
    assert rows[0].abbreviation == "D66"


# ---------------------------------------------------------------------------
# Politician
# ---------------------------------------------------------------------------


async def test_upsert_politician_creates_new_row(async_session: AsyncSession) -> None:
    """A member_roster entity should create a new PoliticianRow."""
    mapper = IbabsEntityMapper(async_session, GOVERNING_BODY_ID)

    pr = _make_parse_result(
        [
            ParsedEntity(
                entity_type="member_roster",
                source_url="https://test.ibabs.eu",
                external_id="Jan de Vries",
                data={
                    "name": "Jan de Vries",
                    "party_name": "VVD",
                    "role": "raadslid",
                },
            ),
        ]
    )

    result = await mapper.map_and_persist(pr)
    assert result.created == 1

    row = (
        await async_session.execute(select(PoliticianRow).where(PoliticianRow.full_name == "Jan de Vries"))
    ).scalar_one()
    assert row.notes == "raadslid"


async def test_upsert_politician_updates_on_recrawl(async_session: AsyncSession) -> None:
    """Re-crawling a politician should update notes, not duplicate the row."""
    mapper = IbabsEntityMapper(async_session, GOVERNING_BODY_ID)

    entity = ParsedEntity(
        entity_type="member_roster",
        source_url="https://test.ibabs.eu",
        external_id="Piet Jansen",
        data={"name": "Piet Jansen", "role": "raadslid"},
    )
    await mapper.map_and_persist(_make_parse_result([entity]))

    entity_v2 = ParsedEntity(
        entity_type="member_roster",
        source_url="https://test.ibabs.eu",
        external_id="Piet Jansen",
        data={"name": "Piet Jansen", "role": "wethouder"},
    )
    r2 = await mapper.map_and_persist(_make_parse_result([entity_v2]))
    assert r2.updated == 1

    rows = (
        (await async_session.execute(select(PoliticianRow).where(PoliticianRow.full_name == "Piet Jansen")))
        .scalars()
        .all()
    )
    assert len(rows) == 1
    assert rows[0].notes == "wethouder"


# ---------------------------------------------------------------------------
# Meeting
# ---------------------------------------------------------------------------


async def test_upsert_meeting_creates_new_row(async_session: AsyncSession) -> None:
    """A meeting_summary entity should create a new MeetingRow."""
    mapper = IbabsEntityMapper(async_session, GOVERNING_BODY_ID)

    pr = _make_parse_result(
        [
            ParsedEntity(
                entity_type="meeting_summary",
                source_url="https://test.ibabs.eu",
                external_id="mtg-1",
                data={
                    "title": "Council Meeting 2024-01-15",
                    "date": "2024-01-15",
                    "url": "https://test.ibabs.eu/meeting/1",
                    "status": "scheduled",
                },
            ),
        ]
    )

    result = await mapper.map_and_persist(pr)
    assert result.created == 1

    row = (
        await async_session.execute(
            select(MeetingRow).where(MeetingRow.source_url == "https://test.ibabs.eu/meeting/1")
        )
    ).scalar_one()
    assert row.title == "Council Meeting 2024-01-15"
    assert row.governing_body_id == GOVERNING_BODY_ID
    # _parse_datetime normalises date-only strings to tz-aware UTC, but
    # SQLite strips tzinfo on storage/retrieval so we cannot assert
    # tzinfo on the row itself — verify the helper directly instead.
    assert row.scheduled_start is not None
    parsed = IbabsEntityMapper._parse_datetime("2024-01-15")
    assert parsed is not None
    assert parsed.tzinfo is not None


async def test_upsert_meeting_does_not_duplicate(async_session: AsyncSession) -> None:
    """Re-crawling the same meeting should update, not create a duplicate."""
    mapper = IbabsEntityMapper(async_session, GOVERNING_BODY_ID)

    entity = ParsedEntity(
        entity_type="meeting_detail",
        source_url="https://test.ibabs.eu",
        external_id="mtg-2",
        data={
            "title": "Meeting A",
            "date": "2024-02-01",
            "url": "https://test.ibabs.eu/meeting/2",
            "location": "City Hall",
        },
    )

    await mapper.map_and_persist(_make_parse_result([entity]))

    entity_v2 = ParsedEntity(
        entity_type="meeting_detail",
        source_url="https://test.ibabs.eu",
        external_id="mtg-2",
        data={
            "title": "Meeting A (updated)",
            "date": "2024-02-01",
            "url": "https://test.ibabs.eu/meeting/2",
            "location": "Online",
        },
    )
    r2 = await mapper.map_and_persist(_make_parse_result([entity_v2]))
    assert r2.updated == 1

    rows = (
        (
            await async_session.execute(
                select(MeetingRow).where(MeetingRow.source_url == "https://test.ibabs.eu/meeting/2")
            )
        )
        .scalars()
        .all()
    )
    assert len(rows) == 1
    assert rows[0].title == "Meeting A (updated)"
    assert rows[0].location == "Online"


# ---------------------------------------------------------------------------
# Document (report + document_link)
# ---------------------------------------------------------------------------


async def test_upsert_report_creates_document_row(async_session: AsyncSession) -> None:
    """A report entity should be persisted as a DocumentRow with type 'report'."""
    mapper = IbabsEntityMapper(async_session, GOVERNING_BODY_ID)

    pr = _make_parse_result(
        [
            ParsedEntity(
                entity_type="report",
                source_url="https://test.ibabs.eu",
                external_id="rpt-1",
                data={
                    "title": "Minutes 2024-01-15",
                    "url": "https://test.ibabs.eu/report/1",
                    "report_type": "minutes",
                },
            ),
        ]
    )

    result = await mapper.map_and_persist(pr)
    assert result.created == 1

    row = (
        await async_session.execute(
            select(DocumentRow).where(DocumentRow.source_url == "https://test.ibabs.eu/report/1")
        )
    ).scalar_one()
    assert row.title == "Minutes 2024-01-15"
    assert row.document_type == "report"


async def test_upsert_document_link_creates_document_row(
    async_session: AsyncSession,
) -> None:
    """A document_link entity should be persisted as a DocumentRow with type 'other'."""
    mapper = IbabsEntityMapper(async_session, GOVERNING_BODY_ID)

    pr = _make_parse_result(
        [
            ParsedEntity(
                entity_type="document_link",
                source_url="https://test.ibabs.eu",
                external_id="doc-url",
                data={
                    "title": "Budget 2024",
                    "url": "https://test.ibabs.eu/doc/budget.pdf",
                    "mime_type": "application/pdf",
                },
            ),
        ]
    )

    result = await mapper.map_and_persist(pr)
    assert result.created == 1

    row = (
        await async_session.execute(
            select(DocumentRow).where(DocumentRow.source_url == "https://test.ibabs.eu/doc/budget.pdf")
        )
    ).scalar_one()
    assert row.title == "Budget 2024"
    assert row.document_type == "other"
    assert row.mime_type == "application/pdf"


# ---------------------------------------------------------------------------
# Motion
# ---------------------------------------------------------------------------


async def test_upsert_motion_creates_new_row(async_session: AsyncSession) -> None:
    """A motion entity should create a new MotionRow."""
    mapper = IbabsEntityMapper(async_session, GOVERNING_BODY_ID)

    pr = _make_parse_result(
        [
            ParsedEntity(
                entity_type="motion",
                source_url="https://test.ibabs.eu",
                external_id="mot-1",
                data={
                    "title": "Motion on housing policy",
                    "body": "The council decides ...",
                    "status": "submitted",
                },
            ),
        ]
    )

    result = await mapper.map_and_persist(pr)
    assert result.created == 1

    row = (
        await async_session.execute(select(MotionRow).where(MotionRow.title == "Motion on housing policy"))
    ).scalar_one()
    assert row.body == "The council decides ..."


async def test_upsert_motion_does_not_duplicate(async_session: AsyncSession) -> None:
    """Re-crawling a motion should update, not create a duplicate."""
    mapper = IbabsEntityMapper(async_session, GOVERNING_BODY_ID)

    entity = ParsedEntity(
        entity_type="motion",
        source_url="https://test.ibabs.eu",
        external_id="mot-2",
        data={"title": "Motion X", "status": "submitted"},
    )
    await mapper.map_and_persist(_make_parse_result([entity]))

    entity_v2 = ParsedEntity(
        entity_type="motion",
        source_url="https://test.ibabs.eu",
        external_id="mot-2",
        data={"title": "Motion X", "body": "updated text", "status": "adopted"},
    )
    r2 = await mapper.map_and_persist(_make_parse_result([entity_v2]))
    assert r2.updated == 1

    rows = (await async_session.execute(select(MotionRow).where(MotionRow.title == "Motion X"))).scalars().all()
    assert len(rows) == 1
    assert rows[0].body == "updated text"
    assert rows[0].status == "adopted"


# ---------------------------------------------------------------------------
# Vote
# ---------------------------------------------------------------------------


async def test_upsert_vote_creates_decision_and_vote(
    async_session: AsyncSession,
) -> None:
    """A vote entity should auto-create a DecisionRow and VoteRow."""
    mapper = IbabsEntityMapper(async_session, GOVERNING_BODY_ID)

    # Pre-create a meeting for the vote to reference.
    meeting_url = "https://test.ibabs.eu/meeting/for-vote"
    meeting_entity = ParsedEntity(
        entity_type="meeting_summary",
        source_url="https://test.ibabs.eu",
        external_id="mtg-vote",
        data={
            "title": "Vote Meeting",
            "date": "2024-03-01",
            "url": meeting_url,
            "status": "completed",
        },
    )
    await mapper.map_and_persist(_make_parse_result([meeting_entity]))

    # Now persist a vote referencing that meeting.
    vote_entity = ParsedEntity(
        entity_type="vote",
        source_url="https://test.ibabs.eu",
        external_id="vote-1",
        data={
            "meeting_source_url": meeting_url,
            "description": "Housing motion vote",
            "outcome": "adopted",
            "votes_for": 20,
            "votes_against": 10,
            "votes_abstain": 3,
        },
    )
    result = await mapper.map_and_persist(_make_parse_result([vote_entity]))
    assert result.created == 1

    decisions = (await async_session.execute(select(DecisionRow))).scalars().all()
    assert len(decisions) == 1
    assert decisions[0].description == "Housing motion vote"

    votes = (await async_session.execute(select(VoteRow))).scalars().all()
    assert len(votes) == 1
    assert votes[0].votes_for == 20
    assert votes[0].votes_against == 10
    assert votes[0].outcome == "adopted"


async def test_upsert_vote_partial_update_preserves_fields(
    async_session: AsyncSession,
) -> None:
    """A vote re-crawl with missing fields should not overwrite stored values."""
    mapper = IbabsEntityMapper(async_session, GOVERNING_BODY_ID)

    meeting_url = "https://test.ibabs.eu/meeting/partial-vote"
    await mapper.map_and_persist(
        _make_parse_result(
            [
                ParsedEntity(
                    entity_type="meeting_summary",
                    source_url="https://test.ibabs.eu",
                    external_id="mtg-partial",
                    data={"title": "Partial Vote Meeting", "date": "2024-04-01", "url": meeting_url},
                ),
            ]
        )
    )

    # First crawl — full payload.
    await mapper.map_and_persist(
        _make_parse_result(
            [
                ParsedEntity(
                    entity_type="vote",
                    source_url="https://test.ibabs.eu",
                    external_id="vote-partial",
                    data={
                        "meeting_source_url": meeting_url,
                        "description": "Partial test",
                        "outcome": "adopted",
                        "votes_for": 15,
                        "votes_against": 5,
                        "votes_abstain": 2,
                    },
                ),
            ]
        )
    )

    # Second crawl — only outcome present.
    r2 = await mapper.map_and_persist(
        _make_parse_result(
            [
                ParsedEntity(
                    entity_type="vote",
                    source_url="https://test.ibabs.eu",
                    external_id="vote-partial",
                    data={
                        "meeting_source_url": meeting_url,
                        "description": "Partial test",
                        "outcome": "rejected",
                    },
                ),
            ]
        )
    )
    assert r2.updated == 1

    votes = (await async_session.execute(select(VoteRow))).scalars().all()
    assert len(votes) == 1
    assert votes[0].outcome == "rejected"
    # votes_for/against/abstain should be preserved from the first crawl.
    assert votes[0].votes_for == 15
    assert votes[0].votes_against == 5
    assert votes[0].votes_abstain == 2


async def test_upsert_vote_without_meeting_records_error(
    async_session: AsyncSession,
) -> None:
    """A vote referencing a missing meeting should be recorded as an error."""
    mapper = IbabsEntityMapper(async_session, GOVERNING_BODY_ID)

    vote_entity = ParsedEntity(
        entity_type="vote",
        source_url="https://test.ibabs.eu",
        external_id="vote-bad",
        data={
            "meeting_source_url": "https://nonexistent/meeting",
            "outcome": "rejected",
        },
    )
    result = await mapper.map_and_persist(_make_parse_result([vote_entity]))
    assert result.errors
    assert "Cannot persist vote" in result.errors[0]


# ---------------------------------------------------------------------------
# Missing natural key validation
# ---------------------------------------------------------------------------


async def test_missing_natural_key_is_skipped_with_error(async_session: AsyncSession) -> None:
    """Entities with empty or missing natural keys should be skipped, not inserted."""
    mapper = IbabsEntityMapper(async_session, GOVERNING_BODY_ID)

    pr = _make_parse_result(
        [
            ParsedEntity(
                entity_type="party_roster",
                source_url="https://test.ibabs.eu",
                external_id="empty-party",
                data={"party_name": "", "abbreviation": "X"},
            ),
            ParsedEntity(
                entity_type="member_roster",
                source_url="https://test.ibabs.eu",
                external_id="no-name",
                data={"role": "raadslid"},
            ),
            ParsedEntity(
                entity_type="meeting_summary",
                source_url="https://test.ibabs.eu",
                external_id="no-url",
                data={"title": "Meeting without URL"},
            ),
        ]
    )

    result = await mapper.map_and_persist(pr)
    assert result.created == 0
    assert result.skipped == 3
    assert len(result.errors) == 3

    # No rows should have been created.
    parties = (await async_session.execute(select(PartyRow))).scalars().all()
    assert len(parties) == 0


# ---------------------------------------------------------------------------
# Skipped entity types
# ---------------------------------------------------------------------------


async def test_unknown_entity_type_is_skipped(async_session: AsyncSession) -> None:
    """Entities with unsupported types should be counted as skipped."""
    mapper = IbabsEntityMapper(async_session, GOVERNING_BODY_ID)

    pr = _make_parse_result(
        [
            ParsedEntity(
                entity_type="unknown_type",
                source_url="https://test.ibabs.eu",
                external_id="x",
                data={},
            ),
        ]
    )
    result = await mapper.map_and_persist(pr)
    assert result.skipped == 1
    assert result.created == 0


# ---------------------------------------------------------------------------
# Mixed batch
# ---------------------------------------------------------------------------


async def test_mixed_batch_persists_multiple_entity_types(
    async_session: AsyncSession,
) -> None:
    """A ParseResult with mixed entity types should persist all of them."""
    mapper = IbabsEntityMapper(async_session, GOVERNING_BODY_ID)

    entities = [
        ParsedEntity(
            entity_type="party_roster",
            source_url="https://test.ibabs.eu",
            external_id="CDA",
            data={"party_name": "CDA", "abbreviation": "CDA"},
        ),
        ParsedEntity(
            entity_type="member_roster",
            source_url="https://test.ibabs.eu",
            external_id="Marie",
            data={"name": "Marie Bakker", "role": "fractievoorzitter"},
        ),
        ParsedEntity(
            entity_type="meeting_summary",
            source_url="https://test.ibabs.eu",
            external_id="mtg-batch",
            data={
                "title": "Batch Meeting",
                "date": "2024-06-01",
                "url": "https://test.ibabs.eu/meeting/batch",
            },
        ),
    ]

    result = await mapper.map_and_persist(_make_parse_result(entities))
    assert result.created == 3
    assert result.errors == []
