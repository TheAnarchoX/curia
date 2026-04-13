"""Integration tests for database-backed v1 API endpoints."""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator, Callable, Generator
from dataclasses import dataclass
from datetime import UTC, date, datetime

import curia_domain.db.models as _models  # noqa: F401
import pytest
import pytest_asyncio
from curia_domain.db.base import Base
from curia_domain.db.models import (
    AgendaItemRow,
    AmendmentRow,
    DecisionRow,
    DocumentRow,
    GoverningBodyRow,
    InstitutionRow,
    JurisdictionRow,
    MeetingRow,
    MetricDefinitionRow,
    MetricResultRow,
    MotionRow,
    PartyRow,
    PoliticianRow,
    PromiseRow,
    SourceRow,
    VoteRow,
    WrittenQuestionRow,
)
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.dialects.sqlite.base import SQLiteTypeCompiler
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from apps.api.app.config import Settings
from apps.api.app.dependencies import get_db
from apps.api.app.main import create_app


@dataclass(frozen=True)
class SeededIds:
    """Identifiers for seeded test rows."""

    institution_1: uuid.UUID
    institution_2: uuid.UUID
    meeting_1: uuid.UUID
    meeting_3: uuid.UUID
    meeting_4: uuid.UUID
    agenda_item_1: uuid.UUID
    document_1: uuid.UUID
    motion_1: uuid.UUID
    amendment_1: uuid.UUID
    question_1: uuid.UUID
    promise_1: uuid.UUID
    decision_1: uuid.UUID
    vote_1: uuid.UUID
    party_1: uuid.UUID
    politician_1: uuid.UUID
    source_1: uuid.UUID
    metric_definition_1: uuid.UUID
    metric_result_1: uuid.UUID
    jurisdiction_1: uuid.UUID


@pytest.fixture(autouse=True)
def _patch_sqlite_type_compiler() -> Generator[None, None, None]:
    """Patch SQLite compilation for PostgreSQL-only column types."""
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


@pytest_asyncio.fixture
async def session_factory() -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    """Yield an async session factory backed by shared in-memory SQLite."""
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        echo=False,
        poolclass=StaticPool,
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    yield factory
    await engine.dispose()


@pytest_asyncio.fixture
async def seeded_ids(session_factory: async_sessionmaker[AsyncSession]) -> SeededIds:
    """Seed rows needed by the API integration tests."""
    async with session_factory() as session:
        jurisdiction_1 = JurisdictionRow(name="Amsterdam", level="municipality")
        jurisdiction_2 = JurisdictionRow(name="Rotterdam", level="municipality")
        source_1 = SourceRow(name="Alpha Source", source_type="ibabs", active=True)
        source_2 = SourceRow(name="Beta Source", source_type="other", active=False)

        session.add_all([jurisdiction_1, jurisdiction_2, source_1, source_2])
        await session.flush()

        institution_1 = InstitutionRow(
            jurisdiction_id=jurisdiction_1.id,
            name="Alpha Council",
            slug="alpha-council",
            institution_type="council",
        )
        institution_2 = InstitutionRow(
            jurisdiction_id=jurisdiction_2.id,
            name="Beta Senate",
            slug="beta-senate",
            institution_type="senate",
        )
        session.add_all([institution_1, institution_2])
        await session.flush()

        governing_body_1 = GoverningBodyRow(
            institution_id=institution_1.id,
            name="Alpha Governing Body",
            body_type="council",
        )
        governing_body_2 = GoverningBodyRow(
            institution_id=institution_2.id,
            name="Beta Governing Body",
            body_type="plenary",
        )
        party_1 = PartyRow(
            name="Alpha Party",
            abbreviation="ALP",
            scope_level="municipality",
            active_from=date(2020, 1, 1),
        )
        party_2 = PartyRow(
            name="Beta Party",
            abbreviation="BTP",
            scope_level="province",
            active_from=date(2022, 1, 1),
        )
        politician_1 = PoliticianRow(full_name="Jane Example", family_name="Example")
        politician_2 = PoliticianRow(full_name="John Other", family_name="Other")

        session.add_all(
            [
                governing_body_1,
                governing_body_2,
                party_1,
                party_2,
                politician_1,
                politician_2,
            ]
        )
        await session.flush()

        meeting_1 = MeetingRow(
            governing_body_id=governing_body_1.id,
            title="Alpha Meeting",
            scheduled_start=datetime(2024, 1, 15, 12, 0, tzinfo=UTC),
            status="completed",
            source_id=source_1.id,
        )
        meeting_2 = MeetingRow(
            governing_body_id=governing_body_2.id,
            title="Beta Meeting",
            scheduled_start=datetime(2024, 3, 20, 12, 0, tzinfo=UTC),
            status="cancelled",
            source_id=source_2.id,
        )
        meeting_3 = MeetingRow(
            governing_body_id=governing_body_1.id,
            title="Alpha End Of Month Meeting",
            scheduled_start=datetime(2024, 1, 31, 23, 59, tzinfo=UTC),
            status="completed",
            source_id=source_1.id,
        )
        meeting_4 = MeetingRow(
            governing_body_id=governing_body_1.id,
            title="Alpha Next Day Meeting",
            scheduled_start=datetime(2024, 2, 1, 0, 0, tzinfo=UTC),
            status="completed",
            source_id=source_1.id,
        )
        session.add_all([meeting_1, meeting_2, meeting_3, meeting_4])
        await session.flush()

        agenda_item_1 = AgendaItemRow(meeting_id=meeting_1.id, ordering=1, title="Alpha Agenda Item")
        agenda_item_2 = AgendaItemRow(meeting_id=meeting_2.id, ordering=2, title="Beta Agenda Item")
        session.add_all([agenda_item_1, agenda_item_2])
        await session.flush()

        document_1 = DocumentRow(
            title="Alpha Report",
            document_type="report",
            text_extracted=True,
            meeting_id=meeting_1.id,
            agenda_item_id=agenda_item_1.id,
            source_url="https://example.com/alpha-report",
        )
        document_2 = DocumentRow(
            title="Beta Minutes",
            document_type="minutes",
            text_extracted=False,
            meeting_id=meeting_2.id,
            agenda_item_id=agenda_item_2.id,
            source_url="https://example.com/beta-minutes",
        )
        session.add_all([document_1, document_2])
        await session.flush()

        motion_1 = MotionRow(
            title="Alpha Motion",
            meeting_id=meeting_1.id,
            agenda_item_id=agenda_item_1.id,
            status="adopted",
            submitted_date=date(2024, 1, 16),
        )
        motion_2 = MotionRow(
            title="Beta Motion",
            meeting_id=meeting_2.id,
            agenda_item_id=agenda_item_2.id,
            status="rejected",
            submitted_date=date(2024, 3, 21),
        )
        amendment_1 = AmendmentRow(
            title="Alpha Amendment",
            target_document_id=document_1.id,
            meeting_id=meeting_1.id,
            agenda_item_id=agenda_item_1.id,
            status="submitted",
            submitted_date=date(2024, 1, 17),
        )
        amendment_2 = AmendmentRow(
            title="Beta Amendment",
            target_document_id=document_2.id,
            meeting_id=meeting_2.id,
            agenda_item_id=agenda_item_2.id,
            status="rejected",
            submitted_date=date(2024, 3, 22),
        )
        question_1 = WrittenQuestionRow(
            title="Alpha Question",
            addressee="Mayor",
            meeting_id=meeting_1.id,
            status="submitted",
            submitted_date=date(2024, 1, 18),
        )
        question_2 = WrittenQuestionRow(
            title="Beta Question",
            addressee="Minister",
            meeting_id=meeting_2.id,
            status="rejected",
            submitted_date=date(2024, 3, 23),
        )
        promise_1 = PromiseRow(
            title="Alpha Promise",
            maker_id=politician_1.id,
            meeting_id=meeting_1.id,
            status="pending",
            made_date=date(2024, 1, 19),
        )
        promise_2 = PromiseRow(
            title="Beta Promise",
            maker_id=politician_2.id,
            meeting_id=meeting_2.id,
            status="adopted",
            made_date=date(2024, 3, 24),
        )

        session.add_all(
            [
                motion_1,
                motion_2,
                amendment_1,
                amendment_2,
                question_1,
                question_2,
                promise_1,
                promise_2,
            ]
        )
        await session.flush()

        decision_1 = DecisionRow(
            meeting_id=meeting_1.id,
            agenda_item_id=agenda_item_1.id,
            decision_type="vote",
            outcome="adopted",
        )
        decision_2 = DecisionRow(
            meeting_id=meeting_2.id,
            agenda_item_id=agenda_item_2.id,
            decision_type="procedural",
            outcome="rejected",
        )
        session.add_all([decision_1, decision_2])
        await session.flush()

        vote_1 = VoteRow(
            decision_id=decision_1.id,
            proposition_type="motion",
            proposition_id=motion_1.id,
            date=date(2024, 1, 20),
            outcome="adopted",
        )
        vote_2 = VoteRow(
            decision_id=decision_2.id,
            proposition_type="amendment",
            proposition_id=amendment_2.id,
            date=date(2024, 3, 25),
            outcome="rejected",
        )
        metric_definition_1 = MetricDefinitionRow(
            code="attendance",
            name="Attendance",
            entity_scope="institution",
            value_type="count",
            time_grain="month",
        )
        metric_definition_2 = MetricDefinitionRow(
            code="absences",
            name="Absences",
            entity_scope="politician",
            value_type="count",
            time_grain="month",
        )
        metric_result_1 = MetricResultRow(
            metric_code="attendance",
            entity_type="institution",
            entity_id=institution_1.id,
            time_grain="month",
            period_start=date(2024, 1, 1),
            period_end=date(2024, 1, 31),
            value=42.0,
        )
        metric_result_2 = MetricResultRow(
            metric_code="absences",
            entity_type="politician",
            entity_id=politician_2.id,
            time_grain="month",
            period_start=date(2024, 3, 1),
            period_end=date(2024, 3, 31),
            value=4.0,
        )

        session.add_all(
            [
                vote_1,
                vote_2,
                metric_definition_1,
                metric_definition_2,
                metric_result_1,
                metric_result_2,
            ]
        )
        await session.commit()

        return SeededIds(
            institution_1=institution_1.id,
            institution_2=institution_2.id,
            meeting_1=meeting_1.id,
            meeting_3=meeting_3.id,
            meeting_4=meeting_4.id,
            agenda_item_1=agenda_item_1.id,
            document_1=document_1.id,
            motion_1=motion_1.id,
            amendment_1=amendment_1.id,
            question_1=question_1.id,
            promise_1=promise_1.id,
            decision_1=decision_1.id,
            vote_1=vote_1.id,
            party_1=party_1.id,
            politician_1=politician_1.id,
            source_1=source_1.id,
            metric_definition_1=metric_definition_1.id,
            metric_result_1=metric_result_1.id,
            jurisdiction_1=jurisdiction_1.id,
        )


@pytest_asyncio.fixture
async def api_client(
    session_factory: async_sessionmaker[AsyncSession],
    seeded_ids: SeededIds,
) -> AsyncIterator[AsyncClient]:
    """Yield an HTTP client for the FastAPI app with an overridden DB dependency."""
    app: FastAPI = create_app(
        Settings.model_validate(
            {
                "debug": True,
                "cors_origins": [],
            }
        )
    )

    async def override_get_db() -> AsyncIterator[AsyncSession]:
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        yield client

    app.dependency_overrides.clear()


ListQueryBuilder = Callable[[SeededIds], dict[str, str]]


@pytest.mark.parametrize(
    ("path", "build_query", "expected_id_attr"),
    [
        (
            "/api/v1/institutions",
            lambda ids: {"jurisdiction_id": str(ids.jurisdiction_1)},
            "institution_1",
        ),
        (
            "/api/v1/meetings",
            lambda ids: {
                "institution_id": str(ids.institution_1),
                "status": "completed",
                "start_date_from": "2024-01-01",
                "start_date_to": "2024-01-30",
            },
            "meeting_1",
        ),
        (
            "/api/v1/agenda-items",
            lambda ids: {"meeting_id": str(ids.meeting_1)},
            "agenda_item_1",
        ),
        (
            "/api/v1/documents",
            lambda ids: {
                "meeting_id": str(ids.meeting_1),
                "document_type": "report",
                "text_extracted": "true",
            },
            "document_1",
        ),
        (
            "/api/v1/motions",
            lambda ids: {
                "meeting_id": str(ids.meeting_1),
                "status": "adopted",
                "submitted_from": "2024-01-01",
                "submitted_to": "2024-01-31",
            },
            "motion_1",
        ),
        (
            "/api/v1/amendments",
            lambda ids: {
                "target_document_id": str(ids.document_1),
                "status": "submitted",
                "submitted_from": "2024-01-01",
                "submitted_to": "2024-01-31",
            },
            "amendment_1",
        ),
        (
            "/api/v1/questions",
            lambda ids: {
                "meeting_id": str(ids.meeting_1),
                "addressee": "mayor",
                "status": "submitted",
                "submitted_from": "2024-01-01",
                "submitted_to": "2024-01-31",
            },
            "question_1",
        ),
        (
            "/api/v1/promises",
            lambda ids: {
                "maker_id": str(ids.politician_1),
                "meeting_id": str(ids.meeting_1),
                "status": "pending",
                "made_from": "2024-01-01",
                "made_to": "2024-01-31",
            },
            "promise_1",
        ),
        (
            "/api/v1/votes",
            lambda ids: {
                "decision_id": str(ids.decision_1),
                "proposition_type": "motion",
                "outcome": "adopted",
                "date_from": "2024-01-01",
                "date_to": "2024-01-31",
            },
            "vote_1",
        ),
        (
            "/api/v1/parties",
            lambda _ids: {
                "name": "alpha",
                "abbreviation": "ALP",
                "scope_level": "municipality",
                "active_on": "2024-01-15",
            },
            "party_1",
        ),
        (
            "/api/v1/politicians",
            lambda _ids: {
                "full_name": "jane",
                "family_name": "example",
            },
            "politician_1",
        ),
        (
            "/api/v1/sources",
            lambda _ids: {
                "source_type": "ibabs",
                "active": "true",
            },
            "source_1",
        ),
        (
            "/api/v1/metrics/definitions",
            lambda _ids: {
                "code": "attendance",
                "entity_scope": "institution",
            },
            "metric_definition_1",
        ),
        (
            "/api/v1/metrics/results",
            lambda ids: {
                "entity_id": str(ids.institution_1),
                "entity_type": "institution",
                "metric_code": "attendance",
                "period_start_from": "2024-01-01",
                "period_end_to": "2024-01-31",
            },
            "metric_result_1",
        ),
    ],
)
@pytest.mark.asyncio
async def test_v1_list_endpoints_query_database(
    api_client: AsyncClient,
    seeded_ids: SeededIds,
    path: str,
    build_query: ListQueryBuilder,
    expected_id_attr: str,
) -> None:
    """Each list endpoint should apply filters and return paginated DB results."""
    response = await api_client.get(path, params={**build_query(seeded_ids), "limit": "1", "offset": "0"})

    assert response.status_code == 200
    payload = response.json()

    assert payload["total"] == 1
    assert payload["page"] == 1
    assert payload["page_size"] == 1
    assert payload["pages"] == 1
    assert [item["id"] for item in payload["items"]] == [str(getattr(seeded_ids, expected_id_attr))]


@pytest.mark.asyncio
async def test_limit_offset_pagination_metadata(api_client: AsyncClient, seeded_ids: SeededIds) -> None:
    """List endpoints should support limit and offset pagination."""
    response = await api_client.get("/api/v1/institutions", params={"limit": "1", "offset": "1"})

    assert response.status_code == 200
    payload = response.json()

    assert payload["total"] == 2
    assert payload["page"] == 2
    assert payload["page_size"] == 1
    assert payload["pages"] == 2
    assert [item["id"] for item in payload["items"]] == [str(seeded_ids.institution_2)]


@pytest.mark.asyncio
async def test_meetings_date_filters_use_utc_datetime_boundaries(
    api_client: AsyncClient,
    seeded_ids: SeededIds,
) -> None:
    """Meeting date filters should use explicit UTC datetime boundaries."""
    response = await api_client.get(
        "/api/v1/meetings",
        params={
            "institution_id": str(seeded_ids.institution_1),
            "status": "completed",
            "start_date_from": "2024-01-31",
            "start_date_to": "2024-01-31",
            "limit": "10",
            "offset": "0",
        },
    )

    assert response.status_code == 200
    payload = response.json()

    assert [item["id"] for item in payload["items"]] == [str(seeded_ids.meeting_3)]
    assert str(seeded_ids.meeting_4) not in {item["id"] for item in payload["items"]}


@pytest.mark.parametrize(
    ("path_template", "seed_attr", "detail"),
    [
        ("/api/v1/institutions/{id}", "institution_1", "Institution not found"),
        ("/api/v1/meetings/{id}", "meeting_1", "Meeting not found"),
        ("/api/v1/agenda-items/{id}", "agenda_item_1", "Agenda item not found"),
        ("/api/v1/documents/{id}", "document_1", "Document not found"),
        ("/api/v1/motions/{id}", "motion_1", "Motion not found"),
        ("/api/v1/amendments/{id}", "amendment_1", "Amendment not found"),
        ("/api/v1/questions/{id}", "question_1", "Written question not found"),
        ("/api/v1/promises/{id}", "promise_1", "Promise not found"),
        ("/api/v1/votes/{id}", "vote_1", "Vote not found"),
        ("/api/v1/parties/{id}", "party_1", "Party not found"),
        ("/api/v1/politicians/{id}", "politician_1", "Politician not found"),
        ("/api/v1/sources/{id}", "source_1", "Source not found"),
    ],
)
@pytest.mark.asyncio
async def test_v1_detail_endpoints_return_rows_or_404(
    api_client: AsyncClient,
    seeded_ids: SeededIds,
    path_template: str,
    seed_attr: str,
    detail: str,
) -> None:
    """Each detail endpoint should load a row and return a 404 when missing."""
    entity_id = getattr(seeded_ids, seed_attr)

    success_response = await api_client.get(path_template.format(id=entity_id))
    assert success_response.status_code == 200
    assert success_response.json()["id"] == str(entity_id)

    missing_response = await api_client.get(path_template.format(id=uuid.uuid4()))
    assert missing_response.status_code == 404
    assert missing_response.json() == {"detail": detail}
