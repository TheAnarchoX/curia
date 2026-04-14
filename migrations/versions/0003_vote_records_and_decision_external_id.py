"""Add vote_records table and decisions.external_id column.

Revision ID: 0003
Revises: 0002
Create Date: 2026-04-14 11:00:00.000000+00:00
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add external_id to decisions and create vote_records table."""
    # --- decisions.external_id ---
    op.add_column("decisions", sa.Column("external_id", sa.String(512), nullable=True))
    op.create_index(
        "ux_decisions_meeting_id_external_id",
        "decisions",
        ["meeting_id", "external_id"],
        unique=True,
        postgresql_where=sa.text("external_id IS NOT NULL"),
    )

    # --- vote_records ---
    op.create_table(
        "vote_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("vote_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("votes.id"), nullable=False),
        sa.Column(
            "politician_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("politicians.id"), nullable=True
        ),
        sa.Column("party_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("parties.id"), nullable=True),
        sa.Column("value", sa.String(32), nullable=False),
        sa.Column("party_size", sa.Integer, nullable=True),
        sa.Column("is_mistake", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("external_id", sa.String(512), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_vote_records_vote_id", "vote_records", ["vote_id"])
    op.create_index("ix_vote_records_politician_id", "vote_records", ["politician_id"])
    op.create_index("ix_vote_records_external_id", "vote_records", ["external_id"], unique=True)


def downgrade() -> None:
    """Drop vote_records table and decisions.external_id column."""
    op.drop_table("vote_records")
    op.drop_index("ux_decisions_meeting_id_external_id", table_name="decisions")
    op.drop_column("decisions", "external_id")
