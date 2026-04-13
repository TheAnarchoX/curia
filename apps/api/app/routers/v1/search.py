"""Full-text search endpoint."""

from __future__ import annotations

from datetime import date
from enum import StrEnum
from typing import Any
from uuid import UUID

from curia_domain.db.models import (
    AgendaItemRow,
    AmendmentRow,
    DocumentRow,
    GoverningBodyRow,
    InstitutionRow,
    MandateRow,
    MeetingRow,
    MotionRow,
    PartyRow,
    PoliticianRow,
    PromiseRow,
    WrittenQuestionRow,
)
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, field_validator
from sqlalchemy import Date, Float, String, case, cast, func, literal, literal_column, select, union_all
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import FromClause

from apps.api.app.dependencies import get_db
from apps.api.app.schemas.common import PaginatedResponse

router = APIRouter(prefix="/search", tags=["search"])

_DUTCH_CONFIG: Any = literal_column("'dutch'")
_SNIPPET_MAX_LENGTH = 280
_SCORE_EXACT_MATCH = 100.0
_SCORE_PREFIX_MATCH = 50.0
_SCORE_CONTAINS = 10.0


class SearchEntityType(StrEnum):
    """Supported search entity types."""

    institution = "institution"
    party = "party"
    politician = "politician"
    meeting = "meeting"
    agenda_item = "agenda_item"
    document = "document"
    motion = "motion"
    amendment = "amendment"
    written_question = "written_question"
    promise = "promise"


class SearchResultItem(BaseModel):
    """Single item in a search result set."""

    entity_type: str
    entity_id: str
    title: str
    snippet: str | None = None
    score: float | None = None

    @field_validator("entity_id")
    @classmethod
    def normalize_entity_id(cls, value: str) -> str:
        """Normalize UUID-like identifiers to canonical string form."""
        try:
            return str(UUID(value))
        except ValueError:
            return value


def _search_text(*expressions: Any) -> Any:
    """Build a normalized text expression for search."""
    value: Any = literal("")

    for expression in expressions:
        value = value + literal(" ") + func.coalesce(cast(expression, String), "")

    return func.trim(value)


def _search_snippet(expression: Any | None) -> Any:
    """Return a compact snippet value."""
    if expression is None:
        return cast(literal(None), String())

    return func.nullif(
        func.substr(func.trim(func.coalesce(cast(expression, String), "")), 1, _SNIPPET_MAX_LENGTH),
        "",
    )


def _build_search_select(
    *,
    dialect_name: str,
    query_text: str,
    entity_type: SearchEntityType,
    from_clause: FromClause | type[Any],
    id_expression: Any,
    title_expression: Any,
    search_expression: Any,
    snippet_expression: Any | None = None,
    entity_date_expression: Any | None = None,
    institution_id: UUID | None = None,
    institution_predicate: Any | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
) -> Any | None:
    """Build a filtered search select for a single entity type."""
    if (date_from is not None or date_to is not None) and entity_date_expression is None:
        return None
    if institution_id is not None and institution_predicate is None:
        return None

    stmt = (
        select(
            literal(entity_type.value).label("entity_type"),
            cast(id_expression, String).label("entity_id"),
            func.coalesce(cast(title_expression, String), "").label("title"),
            _search_snippet(snippet_expression).label("snippet"),
        )
        .select_from(from_clause)
        .where(search_expression != "")
    )

    if institution_predicate is not None:
        stmt = stmt.where(institution_predicate)

    if entity_date_expression is not None and date_from is not None:
        stmt = stmt.where(entity_date_expression >= date_from)
    if entity_date_expression is not None and date_to is not None:
        stmt = stmt.where(entity_date_expression <= date_to)

    if dialect_name == "postgresql":
        search_query = func.websearch_to_tsquery(_DUTCH_CONFIG, query_text)
        search_vector = func.to_tsvector(_DUTCH_CONFIG, search_expression)
        score: Any = cast(func.ts_rank_cd(search_vector, search_query), Float)
        stmt = stmt.add_columns(score.label("score")).where(search_vector.op("@@")(search_query))
    else:
        query_pattern = f"%{query_text.lower()}%"
        lowered_title = func.lower(func.coalesce(cast(title_expression, String), ""))
        lowered_search = func.lower(search_expression)
        score = case(
            (lowered_title == query_text.lower(), _SCORE_EXACT_MATCH),
            (lowered_title.like(f"{query_text.lower()}%"), _SCORE_PREFIX_MATCH),
            (lowered_search.like(query_pattern), _SCORE_CONTAINS),
            else_=0.0,
        )
        stmt = stmt.add_columns(cast(score, Float).label("score")).where(lowered_search.like(query_pattern))

    return stmt


@router.get("", response_model=PaginatedResponse[SearchResultItem])
async def search(
    q: str = Query(..., min_length=1, description="Search query"),
    entity_type: list[SearchEntityType] | None = Query(
        None,
        description="Filter by entity type; repeat the parameter for multiple values",
    ),
    date_from: date | None = Query(None, description="Filter by entity date lower bound"),
    date_to: date | None = Query(None, description="Filter by entity date upper bound"),
    institution_id: UUID | None = Query(None, description="Filter by institution"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[SearchResultItem]:
    """Search across supported entities."""
    query_text = q.strip()
    if not query_text:
        return PaginatedResponse[SearchResultItem].build(items=[], total=0, page=1, page_size=limit)

    dialect_name = db.bind.dialect.name if db.bind is not None else ""
    selected_types = set(entity_type or list(SearchEntityType))
    scoped_institution = GoverningBodyRow.institution_id == institution_id if institution_id is not None else None

    meeting_join = MeetingRow.__table__.join(
        GoverningBodyRow.__table__,
        MeetingRow.governing_body_id == GoverningBodyRow.id,
    )
    agenda_item_join = AgendaItemRow.__table__.join(
        MeetingRow.__table__, AgendaItemRow.meeting_id == MeetingRow.id
    ).join(
        GoverningBodyRow.__table__,
        MeetingRow.governing_body_id == GoverningBodyRow.id,
    )
    document_join = DocumentRow.__table__.outerjoin(
        MeetingRow.__table__, DocumentRow.meeting_id == MeetingRow.id
    ).outerjoin(
        GoverningBodyRow.__table__,
        MeetingRow.governing_body_id == GoverningBodyRow.id,
    )
    meeting_governing_body_join = MeetingRow.__table__.outerjoin(
        GoverningBodyRow.__table__,
        MeetingRow.governing_body_id == GoverningBodyRow.id,
    )

    search_selects = [
        _build_search_select(
            dialect_name=dialect_name,
            query_text=query_text,
            entity_type=SearchEntityType.institution,
            from_clause=InstitutionRow,
            id_expression=InstitutionRow.id,
            title_expression=InstitutionRow.name,
            search_expression=_search_text(
                InstitutionRow.name,
                InstitutionRow.slug,
                InstitutionRow.description,
            ),
            snippet_expression=InstitutionRow.description,
            institution_id=institution_id,
            institution_predicate=InstitutionRow.id == institution_id if institution_id is not None else None,
        )
        if SearchEntityType.institution in selected_types
        else None,
        _build_search_select(
            dialect_name=dialect_name,
            query_text=query_text,
            entity_type=SearchEntityType.party,
            from_clause=PartyRow,
            id_expression=PartyRow.id,
            title_expression=PartyRow.name,
            search_expression=_search_text(PartyRow.name, PartyRow.abbreviation),
            snippet_expression=PartyRow.abbreviation,
            institution_id=institution_id,
            institution_predicate=(
                select(1)
                .where(
                    MandateRow.party_id == PartyRow.id,
                    MandateRow.institution_id == institution_id,
                )
                .exists()
                if institution_id is not None
                else None
            ),
        )
        if SearchEntityType.party in selected_types
        else None,
        _build_search_select(
            dialect_name=dialect_name,
            query_text=query_text,
            entity_type=SearchEntityType.politician,
            from_clause=PoliticianRow,
            id_expression=PoliticianRow.id,
            title_expression=PoliticianRow.full_name,
            search_expression=_search_text(
                PoliticianRow.full_name,
                PoliticianRow.given_name,
                PoliticianRow.family_name,
                PoliticianRow.notes,
            ),
            snippet_expression=PoliticianRow.notes,
            institution_id=institution_id,
            institution_predicate=(
                select(1)
                .where(
                    MandateRow.politician_id == PoliticianRow.id,
                    MandateRow.institution_id == institution_id,
                )
                .exists()
                if institution_id is not None
                else None
            ),
        )
        if SearchEntityType.politician in selected_types
        else None,
        _build_search_select(
            dialect_name=dialect_name,
            query_text=query_text,
            entity_type=SearchEntityType.meeting,
            from_clause=meeting_join,
            id_expression=MeetingRow.id,
            title_expression=MeetingRow.title,
            search_expression=_search_text(
                MeetingRow.title,
                MeetingRow.meeting_type,
                MeetingRow.location,
            ),
            snippet_expression=MeetingRow.location,
            entity_date_expression=cast(MeetingRow.scheduled_start, Date),
            institution_id=institution_id,
            institution_predicate=scoped_institution,
            date_from=date_from,
            date_to=date_to,
        )
        if SearchEntityType.meeting in selected_types
        else None,
        _build_search_select(
            dialect_name=dialect_name,
            query_text=query_text,
            entity_type=SearchEntityType.agenda_item,
            from_clause=agenda_item_join,
            id_expression=AgendaItemRow.id,
            title_expression=AgendaItemRow.title,
            search_expression=_search_text(AgendaItemRow.title, AgendaItemRow.description),
            snippet_expression=AgendaItemRow.description,
            entity_date_expression=cast(MeetingRow.scheduled_start, Date),
            institution_id=institution_id,
            institution_predicate=scoped_institution,
            date_from=date_from,
            date_to=date_to,
        )
        if SearchEntityType.agenda_item in selected_types
        else None,
        _build_search_select(
            dialect_name=dialect_name,
            query_text=query_text,
            entity_type=SearchEntityType.document,
            from_clause=document_join,
            id_expression=DocumentRow.id,
            title_expression=DocumentRow.title,
            search_expression=_search_text(DocumentRow.title, DocumentRow.text_content),
            snippet_expression=DocumentRow.text_content,
            entity_date_expression=cast(MeetingRow.scheduled_start, Date),
            institution_id=institution_id,
            institution_predicate=scoped_institution,
            date_from=date_from,
            date_to=date_to,
        )
        if SearchEntityType.document in selected_types
        else None,
        _build_search_select(
            dialect_name=dialect_name,
            query_text=query_text,
            entity_type=SearchEntityType.motion,
            from_clause=MotionRow.__table__.outerjoin(
                meeting_governing_body_join,
                MotionRow.meeting_id == MeetingRow.id,
            ),
            id_expression=MotionRow.id,
            title_expression=MotionRow.title,
            search_expression=_search_text(MotionRow.title, MotionRow.body),
            snippet_expression=MotionRow.body,
            entity_date_expression=MotionRow.submitted_date,
            institution_id=institution_id,
            institution_predicate=scoped_institution,
            date_from=date_from,
            date_to=date_to,
        )
        if SearchEntityType.motion in selected_types
        else None,
        _build_search_select(
            dialect_name=dialect_name,
            query_text=query_text,
            entity_type=SearchEntityType.amendment,
            from_clause=AmendmentRow.__table__.outerjoin(
                meeting_governing_body_join,
                AmendmentRow.meeting_id == MeetingRow.id,
            ),
            id_expression=AmendmentRow.id,
            title_expression=AmendmentRow.title,
            search_expression=_search_text(AmendmentRow.title, AmendmentRow.body),
            snippet_expression=AmendmentRow.body,
            entity_date_expression=AmendmentRow.submitted_date,
            institution_id=institution_id,
            institution_predicate=scoped_institution,
            date_from=date_from,
            date_to=date_to,
        )
        if SearchEntityType.amendment in selected_types
        else None,
        _build_search_select(
            dialect_name=dialect_name,
            query_text=query_text,
            entity_type=SearchEntityType.written_question,
            from_clause=WrittenQuestionRow.__table__.outerjoin(
                meeting_governing_body_join,
                WrittenQuestionRow.meeting_id == MeetingRow.id,
            ),
            id_expression=WrittenQuestionRow.id,
            title_expression=WrittenQuestionRow.title,
            search_expression=_search_text(
                WrittenQuestionRow.title,
                WrittenQuestionRow.body,
                WrittenQuestionRow.addressee,
            ),
            snippet_expression=WrittenQuestionRow.body,
            entity_date_expression=WrittenQuestionRow.submitted_date,
            institution_id=institution_id,
            institution_predicate=scoped_institution,
            date_from=date_from,
            date_to=date_to,
        )
        if SearchEntityType.written_question in selected_types
        else None,
        _build_search_select(
            dialect_name=dialect_name,
            query_text=query_text,
            entity_type=SearchEntityType.promise,
            from_clause=PromiseRow.__table__.outerjoin(
                meeting_governing_body_join,
                PromiseRow.meeting_id == MeetingRow.id,
            ),
            id_expression=PromiseRow.id,
            title_expression=PromiseRow.title,
            search_expression=_search_text(PromiseRow.title, PromiseRow.body),
            snippet_expression=PromiseRow.body,
            entity_date_expression=PromiseRow.made_date,
            institution_id=institution_id,
            institution_predicate=scoped_institution,
            date_from=date_from,
            date_to=date_to,
        )
        if SearchEntityType.promise in selected_types
        else None,
    ]

    valid_selects = [stmt for stmt in search_selects if stmt is not None]
    if not valid_selects:
        page = (offset // limit) + 1
        return PaginatedResponse[SearchResultItem].build(items=[], total=0, page=page, page_size=limit)

    search_results = union_all(*valid_selects).subquery()
    total = (await db.execute(select(func.count()).select_from(search_results))).scalar_one()
    rows = (
        await db.execute(
            select(search_results)
            .order_by(
                search_results.c.score.desc(),
                search_results.c.title.asc(),
                search_results.c.entity_type.asc(),
                search_results.c.entity_id.asc(),
            )
            .limit(limit)
            .offset(offset)
        )
    ).mappings()

    items = [SearchResultItem.model_validate(row) for row in rows]
    page = (offset // limit) + 1
    return PaginatedResponse[SearchResultItem].build(items=items, total=total, page=page, page_size=limit)
