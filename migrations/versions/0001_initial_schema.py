"""Initial schema — all core Curia domain tables.

Revision ID: 0001
Revises:
Create Date: 2025-01-01 00:00:00.000000+00:00
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create all core domain tables."""
    # --- Jurisdictions ---
    op.create_table(
        "jurisdictions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("code", sa.String(64), nullable=True),
        sa.Column("level", sa.String(32), nullable=False),
        sa.Column("region", sa.String(255), nullable=True),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_jurisdictions_level", "jurisdictions", ["level"])
    op.create_index("ix_jurisdictions_code", "jurisdictions", ["code"])

    # --- Institutions ---
    op.create_table(
        "institutions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("jurisdiction_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("jurisdictions.id"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(255), nullable=False, unique=True),
        sa.Column("institution_type", sa.String(32), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_institutions_jurisdiction_id", "institutions", ["jurisdiction_id"])
    op.create_index("ix_institutions_slug", "institutions", ["slug"])

    # --- Governing bodies ---
    op.create_table(
        "governing_bodies",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("institution_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("institutions.id"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("body_type", sa.String(32), nullable=False),
        sa.Column("valid_from", sa.Date, nullable=True),
        sa.Column("valid_until", sa.Date, nullable=True),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_governing_bodies_institution_id", "governing_bodies", ["institution_id"])

    # --- Parties ---
    op.create_table(
        "parties",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("abbreviation", sa.String(32), nullable=True),
        sa.Column("aliases", postgresql.ARRAY(sa.String), nullable=True),
        sa.Column("scope_level", sa.String(32), nullable=True),
        sa.Column("active_from", sa.Date, nullable=True),
        sa.Column("active_until", sa.Date, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_parties_abbreviation", "parties", ["abbreviation"])

    # --- Politicians ---
    op.create_table(
        "politicians",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("given_name", sa.String(128), nullable=True),
        sa.Column("family_name", sa.String(128), nullable=True),
        sa.Column("initials", sa.String(32), nullable=True),
        sa.Column("aliases", postgresql.ARRAY(sa.String), nullable=True),
        sa.Column("gender", sa.String(16), nullable=True),
        sa.Column("date_of_birth", sa.Date, nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_politicians_full_name", "politicians", ["full_name"])
    op.create_index("ix_politicians_family_name", "politicians", ["family_name"])

    # --- Sources (before mandates/meetings that reference it) ---
    op.create_table(
        "sources",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("source_type", sa.String(64), nullable=False),
        sa.Column("base_url", sa.Text, nullable=True),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("active", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("config", postgresql.JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_sources_source_type", "sources", ["source_type"])

    # --- Mandates ---
    op.create_table(
        "mandates",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("politician_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("politicians.id"), nullable=False),
        sa.Column("party_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("parties.id"), nullable=True),
        sa.Column("institution_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("institutions.id"), nullable=True),
        sa.Column(
            "governing_body_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("governing_bodies.id"),
            nullable=True,
        ),
        sa.Column("role", sa.String(32), nullable=False, server_default="member"),
        sa.Column("start_date", sa.Date, nullable=True),
        sa.Column("end_date", sa.Date, nullable=True),
        sa.Column("source_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("sources.id"), nullable=True),
        sa.Column("confidence", sa.Float, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_mandates_politician_id", "mandates", ["politician_id"])
    op.create_index("ix_mandates_party_id", "mandates", ["party_id"])
    op.create_index("ix_mandates_governing_body_id", "mandates", ["governing_body_id"])

    # --- Meetings ---
    op.create_table(
        "meetings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "governing_body_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("governing_bodies.id"),
            nullable=False,
        ),
        sa.Column("title", sa.String(512), nullable=True),
        sa.Column("meeting_type", sa.String(64), nullable=True),
        sa.Column("scheduled_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("scheduled_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("actual_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("actual_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("location", sa.String(255), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="scheduled"),
        sa.Column("source_url", sa.Text, nullable=True),
        sa.Column("source_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("sources.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_meetings_governing_body_id", "meetings", ["governing_body_id"])
    op.create_index("ix_meetings_status", "meetings", ["status"])
    op.create_index("ix_meetings_scheduled_start", "meetings", ["scheduled_start"])

    # --- Agenda items ---
    op.create_table(
        "agenda_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("meeting_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("meetings.id"), nullable=False),
        sa.Column("ordering", sa.Integer, nullable=False, server_default="0"),
        sa.Column("title", sa.String(512), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column(
            "parent_item_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("agenda_items.id"), nullable=True
        ),
        sa.Column("document_ids", postgresql.ARRAY(postgresql.UUID(as_uuid=True)), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_agenda_items_meeting_id", "agenda_items", ["meeting_id"])
    op.create_index("ix_agenda_items_parent_item_id", "agenda_items", ["parent_item_id"])

    # --- Debate segments ---
    op.create_table(
        "debate_segments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("meeting_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("meetings.id"), nullable=False),
        sa.Column(
            "agenda_item_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("agenda_items.id"), nullable=True
        ),
        sa.Column(
            "politician_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("politicians.id"), nullable=True
        ),
        sa.Column("start_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("end_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_seconds", sa.Float, nullable=True),
        sa.Column("transcript_snippet", sa.Text, nullable=True),
        sa.Column("source_url", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_debate_segments_meeting_id", "debate_segments", ["meeting_id"])
    op.create_index("ix_debate_segments_politician_id", "debate_segments", ["politician_id"])

    # --- Documents ---
    op.create_table(
        "documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("title", sa.String(512), nullable=True),
        sa.Column("document_type", sa.String(32), nullable=False, server_default="other"),
        sa.Column("source_url", sa.Text, nullable=True),
        sa.Column("mime_type", sa.String(128), nullable=True),
        sa.Column("content_hash", sa.String(128), nullable=True),
        sa.Column("text_extracted", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("text_content", sa.Text, nullable=True),
        sa.Column("page_count", sa.Integer, nullable=True),
        sa.Column("meeting_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("meetings.id"), nullable=True),
        sa.Column(
            "agenda_item_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("agenda_items.id"), nullable=True
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_documents_document_type", "documents", ["document_type"])
    op.create_index("ix_documents_meeting_id", "documents", ["meeting_id"])
    op.create_index("ix_documents_content_hash", "documents", ["content_hash"])

    # --- Motions ---
    op.create_table(
        "motions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("title", sa.String(512), nullable=False),
        sa.Column("body", sa.Text, nullable=True),
        sa.Column("proposer_ids", postgresql.ARRAY(postgresql.UUID(as_uuid=True)), nullable=True),
        sa.Column("meeting_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("meetings.id"), nullable=True),
        sa.Column(
            "agenda_item_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("agenda_items.id"), nullable=True
        ),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("documents.id"), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="submitted"),
        sa.Column("submitted_date", sa.Date, nullable=True),
        sa.Column("decided_date", sa.Date, nullable=True),
        sa.Column("topic_tags", postgresql.ARRAY(sa.String), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_motions_meeting_id", "motions", ["meeting_id"])
    op.create_index("ix_motions_status", "motions", ["status"])

    # --- Amendments ---
    op.create_table(
        "amendments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("title", sa.String(512), nullable=False),
        sa.Column("body", sa.Text, nullable=True),
        sa.Column("proposer_ids", postgresql.ARRAY(postgresql.UUID(as_uuid=True)), nullable=True),
        sa.Column(
            "target_document_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("documents.id"), nullable=True
        ),
        sa.Column("meeting_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("meetings.id"), nullable=True),
        sa.Column(
            "agenda_item_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("agenda_items.id"), nullable=True
        ),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("documents.id"), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="submitted"),
        sa.Column("submitted_date", sa.Date, nullable=True),
        sa.Column("decided_date", sa.Date, nullable=True),
        sa.Column("topic_tags", postgresql.ARRAY(sa.String), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_amendments_meeting_id", "amendments", ["meeting_id"])
    op.create_index("ix_amendments_status", "amendments", ["status"])
    op.create_index("ix_amendments_target_document_id", "amendments", ["target_document_id"])

    # --- Written questions ---
    op.create_table(
        "written_questions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("title", sa.String(512), nullable=False),
        sa.Column("body", sa.Text, nullable=True),
        sa.Column("questioner_ids", postgresql.ARRAY(postgresql.UUID(as_uuid=True)), nullable=True),
        sa.Column("addressee", sa.String(255), nullable=True),
        sa.Column("meeting_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("meetings.id"), nullable=True),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("documents.id"), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="submitted"),
        sa.Column("submitted_date", sa.Date, nullable=True),
        sa.Column("answered_date", sa.Date, nullable=True),
        sa.Column(
            "answer_document_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("documents.id"), nullable=True
        ),
        sa.Column("topic_tags", postgresql.ARRAY(sa.String), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_written_questions_meeting_id", "written_questions", ["meeting_id"])
    op.create_index("ix_written_questions_status", "written_questions", ["status"])

    # --- Promises ---
    op.create_table(
        "promises",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("title", sa.String(512), nullable=False),
        sa.Column("body", sa.Text, nullable=True),
        sa.Column(
            "maker_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("politicians.id"), nullable=True
        ),
        sa.Column("meeting_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("meetings.id"), nullable=True),
        sa.Column(
            "agenda_item_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("agenda_items.id"), nullable=True
        ),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("documents.id"), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="pending"),
        sa.Column("made_date", sa.Date, nullable=True),
        sa.Column("due_date", sa.Date, nullable=True),
        sa.Column("fulfilled_date", sa.Date, nullable=True),
        sa.Column("topic_tags", postgresql.ARRAY(sa.String), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_promises_maker_id", "promises", ["maker_id"])
    op.create_index("ix_promises_status", "promises", ["status"])

    # --- Decisions ---
    op.create_table(
        "decisions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("meeting_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("meetings.id"), nullable=False),
        sa.Column(
            "agenda_item_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("agenda_items.id"), nullable=True
        ),
        sa.Column("decision_type", sa.String(32), nullable=False, server_default="vote"),
        sa.Column("outcome", sa.String(32), nullable=True),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_decisions_meeting_id", "decisions", ["meeting_id"])

    # --- Votes ---
    op.create_table(
        "votes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "decision_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("decisions.id"), nullable=False
        ),
        sa.Column("proposition_type", sa.String(64), nullable=True),
        sa.Column("proposition_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("date", sa.Date, nullable=True),
        sa.Column("outcome", sa.String(32), nullable=True),
        sa.Column("votes_for", sa.Integer, nullable=True),
        sa.Column("votes_against", sa.Integer, nullable=True),
        sa.Column("votes_abstain", sa.Integer, nullable=True),
        sa.Column("party_breakdown", postgresql.JSONB, nullable=True),
        sa.Column("politician_votes", postgresql.JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_votes_decision_id", "votes", ["decision_id"])
    op.create_index("ix_votes_date", "votes", ["date"])

    # --- Topics ---
    op.create_table(
        "topics",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(255), nullable=False, unique=True),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column(
            "parent_topic_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("topics.id"), nullable=True
        ),
        sa.Column("aliases", postgresql.ARRAY(sa.String), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_topics_slug", "topics", ["slug"])

    # --- Source records ---
    op.create_table(
        "source_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("source_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("sources.id"), nullable=False),
        sa.Column("external_id", sa.String(512), nullable=True),
        sa.Column("url", sa.Text, nullable=True),
        sa.Column("content_hash", sa.String(128), nullable=True),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("raw_metadata", postgresql.JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_source_records_source_id", "source_records", ["source_id"])
    op.create_index("ix_source_records_external_id", "source_records", ["external_id"])
    op.create_index("ix_source_records_content_hash", "source_records", ["content_hash"])

    # --- Extraction runs ---
    op.create_table(
        "extraction_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("source_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("sources.id"), nullable=False),
        sa.Column("extractor_name", sa.String(128), nullable=False),
        sa.Column("extractor_version", sa.String(64), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="pending"),
        sa.Column("records_processed", sa.Integer, nullable=False, server_default="0"),
        sa.Column("errors_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("warnings", postgresql.ARRAY(sa.String), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_extraction_runs_source_id", "extraction_runs", ["source_id"])
    op.create_index("ix_extraction_runs_status", "extraction_runs", ["status"])

    # --- Evidence (before assertions, which reference it) ---
    op.create_table(
        "evidence",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "source_record_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("source_records.id"),
            nullable=True,
        ),
        sa.Column(
            "extraction_run_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("extraction_runs.id"),
            nullable=True,
        ),
        sa.Column("snippet", sa.Text, nullable=True),
        sa.Column("locator", sa.String(512), nullable=True),
        sa.Column("url", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_evidence_source_record_id", "evidence", ["source_record_id"])

    # --- Assertions ---
    op.create_table(
        "assertions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "source_record_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("source_records.id"),
            nullable=True,
        ),
        sa.Column(
            "extraction_run_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("extraction_runs.id"),
            nullable=True,
        ),
        sa.Column("entity_type", sa.String(64), nullable=False),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("field_name", sa.String(128), nullable=False),
        sa.Column("value", sa.Text, nullable=False),
        sa.Column("confidence", sa.Float, nullable=True),
        sa.Column(
            "evidence_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("evidence.id"), nullable=True
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_assertions_source_record_id", "assertions", ["source_record_id"])
    op.create_index("ix_assertions_entity_type_entity_id", "assertions", ["entity_type", "entity_id"])

    # --- Identity candidates ---
    op.create_table(
        "identity_candidates",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("entity_type", sa.String(64), nullable=False),
        sa.Column("candidate_a_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("candidate_b_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("match_type", sa.String(32), nullable=False),
        sa.Column("confidence", sa.Float, nullable=True),
        sa.Column("reasons", postgresql.ARRAY(sa.String), nullable=True),
        sa.Column("context", postgresql.JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_identity_candidates_entity_type", "identity_candidates", ["entity_type"])
    op.create_index("ix_identity_candidates_match_type", "identity_candidates", ["match_type"])

    # --- Identity resolution reviews ---
    op.create_table(
        "identity_resolution_reviews",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "candidate_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("identity_candidates.id"),
            nullable=False,
        ),
        sa.Column("status", sa.String(32), nullable=False, server_default="pending"),
        sa.Column("reviewer_notes", sa.Text, nullable=True),
        sa.Column("resolved_entity_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index(
        "ix_identity_resolution_reviews_candidate_id", "identity_resolution_reviews", ["candidate_id"]
    )

    # --- Metric definitions ---
    op.create_table(
        "metric_definitions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("code", sa.String(128), nullable=False, unique=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("entity_scope", sa.String(64), nullable=True),
        sa.Column("value_type", sa.String(32), nullable=False),
        sa.Column("time_grain", sa.String(32), nullable=False),
        sa.Column("dependencies", postgresql.ARRAY(sa.String), nullable=True),
        sa.Column("caveats", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_metric_definitions_code", "metric_definitions", ["code"])

    # --- Metric results ---
    op.create_table(
        "metric_results",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("metric_code", sa.String(128), nullable=False),
        sa.Column("entity_type", sa.String(64), nullable=False),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("time_grain", sa.String(32), nullable=False),
        sa.Column("period_start", sa.Date, nullable=False),
        sa.Column("period_end", sa.Date, nullable=False),
        sa.Column("value", sa.Float, nullable=False),
        sa.Column("evidence_ids", postgresql.ARRAY(postgresql.UUID(as_uuid=True)), nullable=True),
        sa.Column("computed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_metric_results_metric_code", "metric_results", ["metric_code"])
    op.create_index("ix_metric_results_entity", "metric_results", ["entity_type", "entity_id"])
    op.create_index("ix_metric_results_period", "metric_results", ["period_start", "period_end"])


def downgrade() -> None:
    """Drop all core domain tables in reverse dependency order."""
    op.drop_table("metric_results")
    op.drop_table("metric_definitions")
    op.drop_table("identity_resolution_reviews")
    op.drop_table("identity_candidates")
    op.drop_table("assertions")
    op.drop_table("evidence")
    op.drop_table("extraction_runs")
    op.drop_table("source_records")
    op.drop_table("topics")
    op.drop_table("votes")
    op.drop_table("decisions")
    op.drop_table("promises")
    op.drop_table("written_questions")
    op.drop_table("amendments")
    op.drop_table("motions")
    op.drop_table("documents")
    op.drop_table("debate_segments")
    op.drop_table("agenda_items")
    op.drop_table("meetings")
    op.drop_table("mandates")
    op.drop_table("sources")
    op.drop_table("politicians")
    op.drop_table("parties")
    op.drop_table("governing_bodies")
    op.drop_table("institutions")
    op.drop_table("jurisdictions")
