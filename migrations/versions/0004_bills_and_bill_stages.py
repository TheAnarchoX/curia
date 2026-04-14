"""Add bills and bill_stages tables.

Revision ID: 0004
Revises: 0003
Create Date: 2026-04-14 12:00:00.000000+00:00
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create bills and bill_stages tables."""
    # --- bills ---
    op.create_table(
        "bills",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("external_id", sa.String(512), nullable=True),
        sa.Column("title", sa.String(512), nullable=False),
        sa.Column("summary", sa.Text, nullable=True),
        sa.Column("bill_type", sa.String(64), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="introduced"),
        sa.Column("introduced_date", sa.Date, nullable=True),
        sa.Column("dossier_number", sa.Integer, nullable=True),
        sa.Column(
            "governing_body_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("governing_bodies.id"),
            nullable=True,
        ),
        sa.Column("proposer_ids", postgresql.ARRAY(postgresql.UUID(as_uuid=True)), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_bills_status", "bills", ["status"])
    op.create_index("ix_bills_dossier_number", "bills", ["dossier_number"])
    op.create_index(
        "ux_bills_external_id",
        "bills",
        ["external_id"],
        unique=True,
        postgresql_where=sa.text("external_id IS NOT NULL"),
    )

    # --- bill_stages ---
    op.create_table(
        "bill_stages",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("bill_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("bills.id"), nullable=False),
        sa.Column("stage_name", sa.String(64), nullable=False),
        sa.Column("stage_date", sa.Date, nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("vote_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("votes.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_bill_stages_bill_id", "bill_stages", ["bill_id"])
    op.create_index("ix_bill_stages_stage_name", "bill_stages", ["stage_name"])


def downgrade() -> None:
    """Drop bill_stages and bills tables."""
    op.drop_table("bill_stages")
    op.drop_table("bills")
