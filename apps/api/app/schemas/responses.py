"""Response schemas for all main domain entities."""

from __future__ import annotations

import uuid
from datetime import date as Date, datetime

from curia_domain.enums import (
    DecisionType,
    DocumentType,
    GoverningBodyType,
    InstitutionType,
    JurisdictionLevel,
    MandateRole,
    MeetingStatus,
    MetricTimeGrain,
    MetricValueType,
    PropositionStatus,
    SourceType,
    VoteOutcome,
)
from pydantic import BaseModel


class _BaseResponse(BaseModel):
    """Fields shared by every response."""

    id: uuid.UUID
    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------------------------
# Organisational hierarchy
# ---------------------------------------------------------------------------


class JurisdictionResponse(_BaseResponse):
    """A geographic or administrative jurisdiction."""

    name: str
    code: str | None = None
    level: JurisdictionLevel
    region: str | None = None
    description: str | None = None


class InstitutionResponse(_BaseResponse):
    """A political institution."""

    jurisdiction_id: uuid.UUID
    name: str
    slug: str
    institution_type: InstitutionType
    description: str | None = None


class GoverningBodyResponse(_BaseResponse):
    """A governing body within an institution."""

    institution_id: uuid.UUID
    name: str
    body_type: GoverningBodyType
    valid_from: Date | None = None
    valid_until: Date | None = None
    description: str | None = None


# ---------------------------------------------------------------------------
# People & parties
# ---------------------------------------------------------------------------


class PartyResponse(_BaseResponse):
    """A political party."""

    name: str
    abbreviation: str | None = None
    aliases: list[str] = []
    scope_level: JurisdictionLevel | None = None
    active_from: Date | None = None
    active_until: Date | None = None


class PoliticianResponse(_BaseResponse):
    """An individual politician."""

    full_name: str
    given_name: str | None = None
    family_name: str | None = None
    initials: str | None = None
    aliases: list[str] = []
    gender: str | None = None
    date_of_birth: Date | None = None


class MandateResponse(_BaseResponse):
    """A mandate linking a politician to a role."""

    politician_id: uuid.UUID
    party_id: uuid.UUID | None = None
    institution_id: uuid.UUID | None = None
    governing_body_id: uuid.UUID | None = None
    role: MandateRole
    start_date: Date | None = None
    end_date: Date | None = None


# ---------------------------------------------------------------------------
# Meetings & agenda
# ---------------------------------------------------------------------------


class MeetingResponse(_BaseResponse):
    """A meeting of a governing body."""

    governing_body_id: uuid.UUID
    title: str | None = None
    meeting_type: str | None = None
    scheduled_start: datetime | None = None
    scheduled_end: datetime | None = None
    status: MeetingStatus
    location: str | None = None
    source_url: str | None = None


class AgendaItemResponse(_BaseResponse):
    """An item on a meeting agenda."""

    meeting_id: uuid.UUID
    ordering: int
    title: str
    description: str | None = None
    parent_item_id: uuid.UUID | None = None


class DebateSegmentResponse(_BaseResponse):
    """A segment of debate from a single speaker."""

    meeting_id: uuid.UUID
    agenda_item_id: uuid.UUID | None = None
    politician_id: uuid.UUID | None = None
    start_time: datetime | None = None
    end_time: datetime | None = None
    duration_seconds: float | None = None
    transcript_snippet: str | None = None


# ---------------------------------------------------------------------------
# Documents & propositions
# ---------------------------------------------------------------------------


class DocumentResponse(_BaseResponse):
    """A document associated with political proceedings."""

    title: str | None = None
    document_type: DocumentType
    source_url: str | None = None
    mime_type: str | None = None
    text_extracted: bool = False
    page_count: int | None = None
    meeting_id: uuid.UUID | None = None
    agenda_item_id: uuid.UUID | None = None


class MotionResponse(_BaseResponse):
    """A motion proposed during proceedings."""

    title: str
    body: str | None = None
    meeting_id: uuid.UUID | None = None
    agenda_item_id: uuid.UUID | None = None
    status: PropositionStatus
    submitted_date: Date | None = None
    decided_date: Date | None = None
    topic_tags: list[str] = []


class AmendmentResponse(_BaseResponse):
    """An amendment to a document or motion."""

    title: str
    body: str | None = None
    target_document_id: uuid.UUID | None = None
    meeting_id: uuid.UUID | None = None
    status: PropositionStatus
    submitted_date: Date | None = None
    decided_date: Date | None = None
    topic_tags: list[str] = []


class WrittenQuestionResponse(_BaseResponse):
    """A written question submitted by a politician."""

    title: str
    body: str | None = None
    addressee: str | None = None
    status: PropositionStatus
    submitted_date: Date | None = None
    answered_date: Date | None = None
    topic_tags: list[str] = []


class PromiseResponse(_BaseResponse):
    """A promise or commitment made by a politician."""

    title: str
    body: str | None = None
    maker_id: uuid.UUID | None = None
    status: PropositionStatus
    made_date: Date | None = None
    due_date: Date | None = None
    fulfilled_date: Date | None = None
    topic_tags: list[str] = []


# ---------------------------------------------------------------------------
# Decisions & votes
# ---------------------------------------------------------------------------


class VoteResponse(_BaseResponse):
    """A recorded vote on a proposition."""

    decision_id: uuid.UUID
    proposition_type: str | None = None
    proposition_id: uuid.UUID | None = None
    date: Date | None = None
    outcome: VoteOutcome | None = None
    votes_for: int | None = None
    votes_against: int | None = None
    votes_abstain: int | None = None


class DecisionResponse(_BaseResponse):
    """A decision taken during a meeting."""

    meeting_id: uuid.UUID
    agenda_item_id: uuid.UUID | None = None
    decision_type: DecisionType
    outcome: VoteOutcome | None = None
    description: str | None = None


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------


class OverviewResponse(BaseModel):
    """High-level entity counts for the dashboard."""

    meetings: int
    politicians: int
    parties: int
    motions: int
    votes: int
    documents: int
    amendments: int
    written_questions: int


class MetricDefinitionResponse(_BaseResponse):
    """Definition of a computed metric."""

    code: str
    name: str
    description: str | None = None
    entity_scope: str | None = None
    value_type: MetricValueType
    time_grain: MetricTimeGrain


class MetricResultResponse(_BaseResponse):
    """A computed metric result for a specific entity and period."""

    metric_code: str
    entity_type: str
    entity_id: uuid.UUID
    time_grain: MetricTimeGrain
    period_start: Date
    period_end: Date
    value: float
    computed_at: datetime | None = None


# ---------------------------------------------------------------------------
# Sources
# ---------------------------------------------------------------------------


class SourceResponse(_BaseResponse):
    """An external data source."""

    name: str
    source_type: SourceType
    base_url: str | None = None
    description: str | None = None
    active: bool = True
