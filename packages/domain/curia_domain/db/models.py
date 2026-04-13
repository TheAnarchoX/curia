"""SQLAlchemy ORM models for the Curia political intelligence platform."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from curia_domain.db.base import Base, TimestampMixin, uuid_pk
from curia_domain.enums import (
    DecisionType,
    DocumentType,
    ExtractionStatus,
    IdentityReviewStatus,
    MandateRole,
    MeetingStatus,
    PropositionStatus,
)

# ---------------------------------------------------------------------------
# Organisational hierarchy
# ---------------------------------------------------------------------------


class JurisdictionRow(TimestampMixin, Base):
    """ORM model for jurisdictions."""

    __tablename__ = "jurisdictions"

    id: Mapped[uuid.UUID] = uuid_pk()
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    level: Mapped[str] = mapped_column(String(32), nullable=False)
    region: Mapped[str | None] = mapped_column(String(255), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    institutions: Mapped[list[InstitutionRow]] = relationship(back_populates="jurisdiction")

    __table_args__ = (
        Index("ix_jurisdictions_level", "level"),
        Index("ix_jurisdictions_code", "code"),
    )


class InstitutionRow(TimestampMixin, Base):
    """ORM model for institutions."""

    __tablename__ = "institutions"

    id: Mapped[uuid.UUID] = uuid_pk()
    jurisdiction_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("jurisdictions.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    institution_type: Mapped[str] = mapped_column(String(32), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    jurisdiction: Mapped[JurisdictionRow] = relationship(back_populates="institutions")
    governing_bodies: Mapped[list[GoverningBodyRow]] = relationship(back_populates="institution")

    __table_args__ = (
        Index("ix_institutions_jurisdiction_id", "jurisdiction_id"),
        Index("ix_institutions_slug", "slug"),
    )


class GoverningBodyRow(TimestampMixin, Base):
    """ORM model for governing bodies."""

    __tablename__ = "governing_bodies"

    id: Mapped[uuid.UUID] = uuid_pk()
    institution_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("institutions.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    body_type: Mapped[str] = mapped_column(String(32), nullable=False)
    valid_from: Mapped[date | None] = mapped_column(Date, nullable=True)
    valid_until: Mapped[date | None] = mapped_column(Date, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    institution: Mapped[InstitutionRow] = relationship(back_populates="governing_bodies")
    meetings: Mapped[list[MeetingRow]] = relationship(back_populates="governing_body")

    __table_args__ = (Index("ix_governing_bodies_institution_id", "institution_id"),)


# ---------------------------------------------------------------------------
# People & parties
# ---------------------------------------------------------------------------


class PartyRow(TimestampMixin, Base):
    """ORM model for political parties."""

    __tablename__ = "parties"

    id: Mapped[uuid.UUID] = uuid_pk()
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    abbreviation: Mapped[str | None] = mapped_column(String(32), nullable=True)
    aliases: Mapped[list[str] | None] = mapped_column(ARRAY(String), nullable=True)
    scope_level: Mapped[str | None] = mapped_column(String(32), nullable=True)
    active_from: Mapped[date | None] = mapped_column(Date, nullable=True)
    active_until: Mapped[date | None] = mapped_column(Date, nullable=True)

    __table_args__ = (
        Index("ix_parties_abbreviation", "abbreviation"),
        Index("ix_parties_name", "name", unique=True),
    )


class PoliticianRow(TimestampMixin, Base):
    """ORM model for politicians."""

    __tablename__ = "politicians"

    id: Mapped[uuid.UUID] = uuid_pk()
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    given_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    family_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    initials: Mapped[str | None] = mapped_column(String(32), nullable=True)
    aliases: Mapped[list[str] | None] = mapped_column(ARRAY(String), nullable=True)
    gender: Mapped[str | None] = mapped_column(String(16), nullable=True)
    date_of_birth: Mapped[date | None] = mapped_column(Date, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        Index("ix_politicians_full_name", "full_name"),
        Index("ix_politicians_family_name", "family_name"),
    )


class MandateRow(TimestampMixin, Base):
    """ORM model for mandates."""

    __tablename__ = "mandates"

    id: Mapped[uuid.UUID] = uuid_pk()
    politician_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("politicians.id"), nullable=False)
    party_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("parties.id"), nullable=True)
    institution_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("institutions.id"), nullable=True
    )
    governing_body_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("governing_bodies.id"), nullable=True
    )
    role: Mapped[str] = mapped_column(String(32), nullable=False, default=MandateRole.MEMBER)
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    source_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("sources.id"), nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)

    politician: Mapped[PoliticianRow] = relationship()
    party: Mapped[PartyRow | None] = relationship()

    __table_args__ = (
        Index("ix_mandates_politician_id", "politician_id"),
        Index("ix_mandates_party_id", "party_id"),
        Index("ix_mandates_governing_body_id", "governing_body_id"),
    )


# ---------------------------------------------------------------------------
# Meetings & agenda
# ---------------------------------------------------------------------------


class MeetingRow(TimestampMixin, Base):
    """ORM model for meetings."""

    __tablename__ = "meetings"

    id: Mapped[uuid.UUID] = uuid_pk()
    governing_body_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("governing_bodies.id"), nullable=False
    )
    title: Mapped[str | None] = mapped_column(String(512), nullable=True)
    meeting_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    scheduled_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    scheduled_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    actual_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    actual_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default=MeetingStatus.SCHEDULED)
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("sources.id"), nullable=True)

    governing_body: Mapped[GoverningBodyRow] = relationship(back_populates="meetings")
    agenda_items: Mapped[list[AgendaItemRow]] = relationship(back_populates="meeting")

    __table_args__ = (
        Index("ix_meetings_governing_body_id", "governing_body_id"),
        Index("ix_meetings_status", "status"),
        Index("ix_meetings_scheduled_start", "scheduled_start"),
        Index("ix_meetings_source_url", "source_url", unique=True, postgresql_where="source_url IS NOT NULL"),
    )


class AgendaItemRow(TimestampMixin, Base):
    """ORM model for agenda items."""

    __tablename__ = "agenda_items"

    id: Mapped[uuid.UUID] = uuid_pk()
    meeting_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("meetings.id"), nullable=False)
    ordering: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    parent_item_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agenda_items.id"), nullable=True
    )
    document_ids: Mapped[list[uuid.UUID] | None] = mapped_column(ARRAY(UUID(as_uuid=True)), nullable=True)

    meeting: Mapped[MeetingRow] = relationship(back_populates="agenda_items")

    __table_args__ = (
        Index("ix_agenda_items_meeting_id", "meeting_id"),
        Index("ix_agenda_items_parent_item_id", "parent_item_id"),
    )


class DebateSegmentRow(TimestampMixin, Base):
    """ORM model for debate segments."""

    __tablename__ = "debate_segments"

    id: Mapped[uuid.UUID] = uuid_pk()
    meeting_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("meetings.id"), nullable=False)
    agenda_item_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agenda_items.id"), nullable=True
    )
    politician_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("politicians.id"), nullable=True
    )
    start_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    end_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    transcript_snippet: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        Index("ix_debate_segments_meeting_id", "meeting_id"),
        Index("ix_debate_segments_politician_id", "politician_id"),
    )


# ---------------------------------------------------------------------------
# Documents & propositions
# ---------------------------------------------------------------------------


class DocumentRow(TimestampMixin, Base):
    """ORM model for documents."""

    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = uuid_pk()
    title: Mapped[str | None] = mapped_column(String(512), nullable=True)
    document_type: Mapped[str] = mapped_column(String(32), nullable=False, default=DocumentType.OTHER)
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    mime_type: Mapped[str | None] = mapped_column(String(128), nullable=True)
    content_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    text_extracted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    text_content: Mapped[str | None] = mapped_column(Text, nullable=True)
    page_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    meeting_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("meetings.id"), nullable=True)
    agenda_item_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agenda_items.id"), nullable=True
    )

    __table_args__ = (
        Index("ix_documents_document_type", "document_type"),
        Index("ix_documents_meeting_id", "meeting_id"),
        Index("ix_documents_content_hash", "content_hash"),
        Index("ix_documents_source_url", "source_url", unique=True, postgresql_where="source_url IS NOT NULL"),
    )


class MotionRow(TimestampMixin, Base):
    """ORM model for motions."""

    __tablename__ = "motions"

    id: Mapped[uuid.UUID] = uuid_pk()
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    body: Mapped[str | None] = mapped_column(Text, nullable=True)
    proposer_ids: Mapped[list[uuid.UUID] | None] = mapped_column(ARRAY(UUID(as_uuid=True)), nullable=True)
    meeting_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("meetings.id"), nullable=True)
    agenda_item_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agenda_items.id"), nullable=True
    )
    document_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("documents.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default=PropositionStatus.SUBMITTED)
    submitted_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    decided_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    topic_tags: Mapped[list[str] | None] = mapped_column(ARRAY(String), nullable=True)

    __table_args__ = (
        Index("ix_motions_meeting_id", "meeting_id"),
        Index("ix_motions_status", "status"),
    )


class AmendmentRow(TimestampMixin, Base):
    """ORM model for amendments."""

    __tablename__ = "amendments"

    id: Mapped[uuid.UUID] = uuid_pk()
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    body: Mapped[str | None] = mapped_column(Text, nullable=True)
    proposer_ids: Mapped[list[uuid.UUID] | None] = mapped_column(ARRAY(UUID(as_uuid=True)), nullable=True)
    target_document_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id"), nullable=True
    )
    meeting_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("meetings.id"), nullable=True)
    agenda_item_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agenda_items.id"), nullable=True
    )
    document_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("documents.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default=PropositionStatus.SUBMITTED)
    submitted_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    decided_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    topic_tags: Mapped[list[str] | None] = mapped_column(ARRAY(String), nullable=True)

    __table_args__ = (
        Index("ix_amendments_meeting_id", "meeting_id"),
        Index("ix_amendments_status", "status"),
        Index("ix_amendments_target_document_id", "target_document_id"),
    )


class WrittenQuestionRow(TimestampMixin, Base):
    """ORM model for written questions."""

    __tablename__ = "written_questions"

    id: Mapped[uuid.UUID] = uuid_pk()
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    body: Mapped[str | None] = mapped_column(Text, nullable=True)
    questioner_ids: Mapped[list[uuid.UUID] | None] = mapped_column(ARRAY(UUID(as_uuid=True)), nullable=True)
    addressee: Mapped[str | None] = mapped_column(String(255), nullable=True)
    meeting_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("meetings.id"), nullable=True)
    document_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("documents.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default=PropositionStatus.SUBMITTED)
    submitted_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    answered_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    answer_document_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id"), nullable=True
    )
    topic_tags: Mapped[list[str] | None] = mapped_column(ARRAY(String), nullable=True)

    __table_args__ = (
        Index("ix_written_questions_meeting_id", "meeting_id"),
        Index("ix_written_questions_status", "status"),
    )


class PromiseRow(TimestampMixin, Base):
    """ORM model for promises."""

    __tablename__ = "promises"

    id: Mapped[uuid.UUID] = uuid_pk()
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    body: Mapped[str | None] = mapped_column(Text, nullable=True)
    maker_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("politicians.id"), nullable=True)
    meeting_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("meetings.id"), nullable=True)
    agenda_item_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agenda_items.id"), nullable=True
    )
    document_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("documents.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default=PropositionStatus.PENDING)
    made_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    fulfilled_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    topic_tags: Mapped[list[str] | None] = mapped_column(ARRAY(String), nullable=True)

    __table_args__ = (
        Index("ix_promises_maker_id", "maker_id"),
        Index("ix_promises_status", "status"),
    )


# ---------------------------------------------------------------------------
# Decisions & votes
# ---------------------------------------------------------------------------


class DecisionRow(TimestampMixin, Base):
    """ORM model for decisions."""

    __tablename__ = "decisions"

    id: Mapped[uuid.UUID] = uuid_pk()
    meeting_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("meetings.id"), nullable=False)
    agenda_item_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agenda_items.id"), nullable=True
    )
    decision_type: Mapped[str] = mapped_column(String(32), nullable=False, default=DecisionType.VOTE)
    outcome: Mapped[str | None] = mapped_column(String(32), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (Index("ix_decisions_meeting_id", "meeting_id"),)


class VoteRow(TimestampMixin, Base):
    """ORM model for votes."""

    __tablename__ = "votes"

    id: Mapped[uuid.UUID] = uuid_pk()
    decision_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("decisions.id"), nullable=False)
    proposition_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    proposition_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    date: Mapped[date | None] = mapped_column(Date, nullable=True)
    outcome: Mapped[str | None] = mapped_column(String(32), nullable=True)
    votes_for: Mapped[int | None] = mapped_column(Integer, nullable=True)
    votes_against: Mapped[int | None] = mapped_column(Integer, nullable=True)
    votes_abstain: Mapped[int | None] = mapped_column(Integer, nullable=True)
    party_breakdown: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    politician_votes: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)

    __table_args__ = (
        Index("ix_votes_decision_id", "decision_id"),
        Index("ix_votes_date", "date"),
    )


# ---------------------------------------------------------------------------
# Taxonomy
# ---------------------------------------------------------------------------


class TopicRow(TimestampMixin, Base):
    """ORM model for topics."""

    __tablename__ = "topics"

    id: Mapped[uuid.UUID] = uuid_pk()
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    parent_topic_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("topics.id"), nullable=True
    )
    aliases: Mapped[list[str] | None] = mapped_column(ARRAY(String), nullable=True)

    __table_args__ = (Index("ix_topics_slug", "slug"),)


# ---------------------------------------------------------------------------
# Ingestion / extraction lineage
# ---------------------------------------------------------------------------


class SourceRow(TimestampMixin, Base):
    """ORM model for data sources."""

    __tablename__ = "sources"

    id: Mapped[uuid.UUID] = uuid_pk()
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    source_type: Mapped[str] = mapped_column(String(64), nullable=False)
    base_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    config: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)

    __table_args__ = (Index("ix_sources_source_type", "source_type"),)


class SourceRecordRow(TimestampMixin, Base):
    """ORM model for source records."""

    __tablename__ = "source_records"

    id: Mapped[uuid.UUID] = uuid_pk()
    source_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("sources.id"), nullable=False)
    external_id: Mapped[str | None] = mapped_column(String(512), nullable=True)
    url: Mapped[str | None] = mapped_column(Text, nullable=True)
    content_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    fetched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    raw_metadata: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)

    __table_args__ = (
        Index("ix_source_records_source_id", "source_id"),
        Index("ix_source_records_external_id", "external_id"),
        Index("ix_source_records_content_hash", "content_hash"),
    )


class ExtractionRunRow(TimestampMixin, Base):
    """ORM model for extraction runs."""

    __tablename__ = "extraction_runs"

    id: Mapped[uuid.UUID] = uuid_pk()
    source_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("sources.id"), nullable=False)
    extractor_name: Mapped[str] = mapped_column(String(128), nullable=False)
    extractor_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default=ExtractionStatus.PENDING)
    records_processed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    errors_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    warnings: Mapped[list[str] | None] = mapped_column(ARRAY(String), nullable=True)

    __table_args__ = (
        Index("ix_extraction_runs_source_id", "source_id"),
        Index("ix_extraction_runs_status", "status"),
    )


class AssertionRow(TimestampMixin, Base):
    """ORM model for assertions."""

    __tablename__ = "assertions"

    id: Mapped[uuid.UUID] = uuid_pk()
    source_record_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("source_records.id"), nullable=True
    )
    extraction_run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("extraction_runs.id"), nullable=True
    )
    entity_type: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    field_name: Mapped[str] = mapped_column(String(128), nullable=False)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    evidence_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("evidence.id"), nullable=True)

    __table_args__ = (
        Index("ix_assertions_source_record_id", "source_record_id"),
        Index("ix_assertions_entity_type_entity_id", "entity_type", "entity_id"),
    )


class EvidenceRow(TimestampMixin, Base):
    """ORM model for evidence."""

    __tablename__ = "evidence"

    id: Mapped[uuid.UUID] = uuid_pk()
    source_record_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("source_records.id"), nullable=True
    )
    extraction_run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("extraction_runs.id"), nullable=True
    )
    snippet: Mapped[str | None] = mapped_column(Text, nullable=True)
    locator: Mapped[str | None] = mapped_column(String(512), nullable=True)
    url: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (Index("ix_evidence_source_record_id", "source_record_id"),)


# ---------------------------------------------------------------------------
# Identity resolution
# ---------------------------------------------------------------------------


class IdentityCandidateRow(TimestampMixin, Base):
    """ORM model for identity resolution candidates."""

    __tablename__ = "identity_candidates"

    id: Mapped[uuid.UUID] = uuid_pk()
    entity_type: Mapped[str] = mapped_column(String(64), nullable=False)
    candidate_a_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    candidate_b_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    match_type: Mapped[str] = mapped_column(String(32), nullable=False)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    reasons: Mapped[list[str] | None] = mapped_column(ARRAY(String), nullable=True)
    context: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)

    __table_args__ = (
        Index("ix_identity_candidates_entity_type", "entity_type"),
        Index("ix_identity_candidates_match_type", "match_type"),
    )


class IdentityResolutionReviewRow(TimestampMixin, Base):
    """ORM model for identity resolution reviews."""

    __tablename__ = "identity_resolution_reviews"

    id: Mapped[uuid.UUID] = uuid_pk()
    candidate_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("identity_candidates.id"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False, default=IdentityReviewStatus.PENDING)
    reviewer_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    resolved_entity_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (Index("ix_identity_resolution_reviews_candidate_id", "candidate_id"),)


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------


class MetricDefinitionRow(TimestampMixin, Base):
    """ORM model for metric definitions."""

    __tablename__ = "metric_definitions"

    id: Mapped[uuid.UUID] = uuid_pk()
    code: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    entity_scope: Mapped[str | None] = mapped_column(String(64), nullable=True)
    value_type: Mapped[str] = mapped_column(String(32), nullable=False)
    time_grain: Mapped[str] = mapped_column(String(32), nullable=False)
    dependencies: Mapped[list[str] | None] = mapped_column(ARRAY(String), nullable=True)
    caveats: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (Index("ix_metric_definitions_code", "code"),)


class MetricResultRow(TimestampMixin, Base):
    """ORM model for metric results."""

    __tablename__ = "metric_results"

    id: Mapped[uuid.UUID] = uuid_pk()
    metric_code: Mapped[str] = mapped_column(String(128), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    time_grain: Mapped[str] = mapped_column(String(32), nullable=False)
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    value: Mapped[float] = mapped_column(Float, nullable=False)
    evidence_ids: Mapped[list[uuid.UUID] | None] = mapped_column(ARRAY(UUID(as_uuid=True)), nullable=True)
    computed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("ix_metric_results_metric_code", "metric_code"),
        Index("ix_metric_results_entity", "entity_type", "entity_id"),
        Index("ix_metric_results_period", "period_start", "period_end"),
    )
