"""Pydantic domain models for the Curia political intelligence platform."""

from __future__ import annotations

import uuid
from datetime import date as Date
from datetime import datetime, timezone

from pydantic import BaseModel, Field

from curia_domain.enums import (
    DecisionType,
    DocumentType,
    ExtractionStatus,
    GoverningBodyType,
    IdentityMatchType,
    IdentityReviewStatus,
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


# ---------------------------------------------------------------------------
# Base
# ---------------------------------------------------------------------------


class BaseEntity(BaseModel):
    """Base for all domain entities."""

    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ---------------------------------------------------------------------------
# Organisational hierarchy
# ---------------------------------------------------------------------------


class Jurisdiction(BaseEntity):
    """A geographic or administrative jurisdiction (e.g. a municipality)."""

    name: str
    code: str | None = None
    level: JurisdictionLevel
    region: str | None = None
    description: str | None = None


class Institution(BaseEntity):
    """A political institution within a jurisdiction."""

    jurisdiction_id: uuid.UUID
    name: str
    slug: str
    institution_type: InstitutionType
    description: str | None = None


class GoverningBody(BaseEntity):
    """A governing body within an institution (e.g. a council or committee)."""

    institution_id: uuid.UUID
    name: str
    body_type: GoverningBodyType
    valid_from: Date | None = None
    valid_until: Date | None = None
    description: str | None = None


# ---------------------------------------------------------------------------
# People & parties
# ---------------------------------------------------------------------------


class Party(BaseEntity):
    """A political party."""

    name: str
    abbreviation: str | None = None
    aliases: list[str] = Field(default_factory=list)
    scope_level: JurisdictionLevel | None = None
    active_from: Date | None = None
    active_until: Date | None = None


class Politician(BaseEntity):
    """An individual politician."""

    full_name: str
    given_name: str | None = None
    family_name: str | None = None
    initials: str | None = None
    aliases: list[str] = Field(default_factory=list)
    gender: str | None = None
    date_of_birth: Date | None = None
    notes: str | None = None


class Mandate(BaseEntity):
    """A mandate linking a politician to a role within a governing body."""

    politician_id: uuid.UUID
    party_id: uuid.UUID | None = None
    institution_id: uuid.UUID | None = None
    governing_body_id: uuid.UUID | None = None
    role: MandateRole = MandateRole.MEMBER
    start_date: Date | None = None
    end_date: Date | None = None
    source_id: uuid.UUID | None = None
    confidence: float | None = None


# ---------------------------------------------------------------------------
# Meetings & agenda
# ---------------------------------------------------------------------------


class Meeting(BaseEntity):
    """A scheduled or completed meeting of a governing body."""

    governing_body_id: uuid.UUID
    title: str | None = None
    meeting_type: str | None = None
    scheduled_start: datetime | None = None
    scheduled_end: datetime | None = None
    actual_start: datetime | None = None
    actual_end: datetime | None = None
    location: str | None = None
    status: MeetingStatus = MeetingStatus.SCHEDULED
    source_url: str | None = None
    source_id: uuid.UUID | None = None


class AgendaItem(BaseEntity):
    """An item on a meeting agenda."""

    meeting_id: uuid.UUID
    ordering: int = 0
    title: str
    description: str | None = None
    parent_item_id: uuid.UUID | None = None
    document_ids: list[uuid.UUID] = Field(default_factory=list)


class DebateSegment(BaseEntity):
    """A segment of debate, typically one speaker's contribution."""

    meeting_id: uuid.UUID
    agenda_item_id: uuid.UUID | None = None
    politician_id: uuid.UUID | None = None
    start_time: datetime | None = None
    end_time: datetime | None = None
    duration_seconds: float | None = None
    transcript_snippet: str | None = None
    source_url: str | None = None


# ---------------------------------------------------------------------------
# Documents & propositions
# ---------------------------------------------------------------------------


class Document(BaseEntity):
    """A document associated with political proceedings."""

    title: str | None = None
    document_type: DocumentType = DocumentType.OTHER
    source_url: str | None = None
    mime_type: str | None = None
    content_hash: str | None = None
    text_extracted: bool = False
    text_content: str | None = None
    page_count: int | None = None
    meeting_id: uuid.UUID | None = None
    agenda_item_id: uuid.UUID | None = None


class Motion(BaseEntity):
    """A motion proposed during political proceedings."""

    title: str
    body: str | None = None
    proposer_ids: list[uuid.UUID] = Field(default_factory=list)
    meeting_id: uuid.UUID | None = None
    agenda_item_id: uuid.UUID | None = None
    document_id: uuid.UUID | None = None
    status: PropositionStatus = PropositionStatus.SUBMITTED
    submitted_date: Date | None = None
    decided_date: Date | None = None
    topic_tags: list[str] = Field(default_factory=list)


class Amendment(BaseEntity):
    """An amendment to an existing document or motion."""

    title: str
    body: str | None = None
    proposer_ids: list[uuid.UUID] = Field(default_factory=list)
    target_document_id: uuid.UUID | None = None
    meeting_id: uuid.UUID | None = None
    agenda_item_id: uuid.UUID | None = None
    document_id: uuid.UUID | None = None
    status: PropositionStatus = PropositionStatus.SUBMITTED
    submitted_date: Date | None = None
    decided_date: Date | None = None
    topic_tags: list[str] = Field(default_factory=list)


class WrittenQuestion(BaseEntity):
    """A written question submitted by a politician."""

    title: str
    body: str | None = None
    questioner_ids: list[uuid.UUID] = Field(default_factory=list)
    addressee: str | None = None
    meeting_id: uuid.UUID | None = None
    document_id: uuid.UUID | None = None
    status: PropositionStatus = PropositionStatus.SUBMITTED
    submitted_date: Date | None = None
    answered_date: Date | None = None
    answer_document_id: uuid.UUID | None = None
    topic_tags: list[str] = Field(default_factory=list)


class Promise(BaseEntity):
    """A promise or commitment made by a politician."""

    title: str
    body: str | None = None
    maker_id: uuid.UUID | None = None
    meeting_id: uuid.UUID | None = None
    agenda_item_id: uuid.UUID | None = None
    document_id: uuid.UUID | None = None
    status: PropositionStatus = PropositionStatus.PENDING
    made_date: Date | None = None
    due_date: Date | None = None
    fulfilled_date: Date | None = None
    topic_tags: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Decisions & votes
# ---------------------------------------------------------------------------


class Decision(BaseEntity):
    """A decision taken during a meeting."""

    meeting_id: uuid.UUID
    agenda_item_id: uuid.UUID | None = None
    decision_type: DecisionType = DecisionType.VOTE
    outcome: VoteOutcome | None = None
    description: str | None = None


class Vote(BaseEntity):
    """A recorded vote on a proposition."""

    decision_id: uuid.UUID
    proposition_type: str | None = None
    proposition_id: uuid.UUID | None = None
    date: Date | None = None
    outcome: VoteOutcome | None = None
    votes_for: int | None = None
    votes_against: int | None = None
    votes_abstain: int | None = None
    party_breakdown: dict[str, dict[str, int]] = Field(default_factory=dict)
    politician_votes: dict[str, str] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Taxonomy
# ---------------------------------------------------------------------------


class Topic(BaseEntity):
    """A topic or theme used for classification."""

    name: str
    slug: str
    description: str | None = None
    parent_topic_id: uuid.UUID | None = None
    aliases: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Ingestion / extraction lineage
# ---------------------------------------------------------------------------


class Source(BaseEntity):
    """An external data source."""

    name: str
    source_type: SourceType
    base_url: str | None = None
    description: str | None = None
    active: bool = True
    config: dict[str, object] = Field(default_factory=dict)


class SourceRecord(BaseEntity):
    """A single record fetched from a source."""

    source_id: uuid.UUID
    external_id: str | None = None
    url: str | None = None
    content_hash: str | None = None
    fetched_at: datetime | None = None
    raw_metadata: dict[str, object] = Field(default_factory=dict)


class ExtractionRun(BaseEntity):
    """A run of an extraction process against a source."""

    source_id: uuid.UUID
    extractor_name: str
    extractor_version: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    status: ExtractionStatus = ExtractionStatus.PENDING
    records_processed: int = 0
    errors_count: int = 0
    warnings: list[str] = Field(default_factory=list)


class Assertion(BaseEntity):
    """A single extracted fact tied to lineage evidence."""

    source_record_id: uuid.UUID | None = None
    extraction_run_id: uuid.UUID | None = None
    entity_type: str
    entity_id: uuid.UUID | None = None
    field_name: str
    value: str
    confidence: float | None = None
    evidence_id: uuid.UUID | None = None


class Evidence(BaseEntity):
    """Supporting evidence for an extracted assertion."""

    source_record_id: uuid.UUID | None = None
    extraction_run_id: uuid.UUID | None = None
    snippet: str | None = None
    locator: str | None = None
    url: str | None = None


# ---------------------------------------------------------------------------
# Identity resolution
# ---------------------------------------------------------------------------


class IdentityCandidate(BaseEntity):
    """A candidate pair for identity resolution (potential duplicate)."""

    entity_type: str
    candidate_a_id: uuid.UUID
    candidate_b_id: uuid.UUID
    match_type: IdentityMatchType
    confidence: float | None = None
    reasons: list[str] = Field(default_factory=list)
    context: dict[str, object] = Field(default_factory=dict)


class IdentityResolutionReview(BaseEntity):
    """A human review of an identity candidate pair."""

    candidate_id: uuid.UUID
    status: IdentityReviewStatus = IdentityReviewStatus.PENDING
    reviewer_notes: str | None = None
    resolved_entity_id: uuid.UUID | None = None
    reviewed_at: datetime | None = None


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------


class MetricDefinition(BaseEntity):
    """Definition of a computed metric."""

    code: str
    name: str
    description: str | None = None
    entity_scope: str | None = None
    value_type: MetricValueType
    time_grain: MetricTimeGrain
    dependencies: list[str] = Field(default_factory=list)
    caveats: str | None = None


class MetricResult(BaseEntity):
    """A computed metric result for a specific entity and time period."""

    metric_code: str
    entity_type: str
    entity_id: uuid.UUID
    time_grain: MetricTimeGrain
    period_start: Date
    period_end: Date
    value: float
    evidence_ids: list[uuid.UUID] = Field(default_factory=list)
    computed_at: datetime | None = None
