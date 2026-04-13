"""Add expression GIN indexes for API search.

Revision ID: 0002
Revises: 0001
Create Date: 2026-04-13 23:30:00.000000+00:00
"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create PostgreSQL GIN indexes for full-text search expressions."""
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_institutions_search_tsv
        ON institutions
        USING GIN (
            to_tsvector(
                'dutch',
                coalesce(name, '') || ' ' || coalesce(slug, '') || ' ' || coalesce(description, '')
            )
        )
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_parties_search_tsv
        ON parties
        USING GIN (to_tsvector('dutch', coalesce(name, '') || ' ' || coalesce(abbreviation, '')))
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_politicians_search_tsv
        ON politicians
        USING GIN (
            to_tsvector(
                'dutch',
                coalesce(full_name, '')
                || ' '
                || coalesce(given_name, '')
                || ' '
                || coalesce(family_name, '')
                || ' '
                || coalesce(notes, '')
            )
        )
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_meetings_search_tsv
        ON meetings
        USING GIN (
            to_tsvector(
                'dutch',
                coalesce(title, '') || ' ' || coalesce(meeting_type, '') || ' ' || coalesce(location, '')
            )
        )
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_agenda_items_search_tsv
        ON agenda_items
        USING GIN (to_tsvector('dutch', coalesce(title, '') || ' ' || coalesce(description, '')))
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_documents_search_tsv
        ON documents
        USING GIN (to_tsvector('dutch', coalesce(title, '') || ' ' || coalesce(text_content, '')))
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_motions_search_tsv
        ON motions
        USING GIN (to_tsvector('dutch', coalesce(title, '') || ' ' || coalesce(body, '')))
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_amendments_search_tsv
        ON amendments
        USING GIN (to_tsvector('dutch', coalesce(title, '') || ' ' || coalesce(body, '')))
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_written_questions_search_tsv
        ON written_questions
        USING GIN (
            to_tsvector(
                'dutch',
                coalesce(title, '') || ' ' || coalesce(body, '') || ' ' || coalesce(addressee, '')
            )
        )
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_promises_search_tsv
        ON promises
        USING GIN (to_tsvector('dutch', coalesce(title, '') || ' ' || coalesce(body, '')))
        """
    )


def downgrade() -> None:
    """Drop PostgreSQL full-text search expression indexes."""
    op.execute("DROP INDEX IF EXISTS ix_promises_search_tsv")
    op.execute("DROP INDEX IF EXISTS ix_written_questions_search_tsv")
    op.execute("DROP INDEX IF EXISTS ix_amendments_search_tsv")
    op.execute("DROP INDEX IF EXISTS ix_motions_search_tsv")
    op.execute("DROP INDEX IF EXISTS ix_documents_search_tsv")
    op.execute("DROP INDEX IF EXISTS ix_agenda_items_search_tsv")
    op.execute("DROP INDEX IF EXISTS ix_meetings_search_tsv")
    op.execute("DROP INDEX IF EXISTS ix_politicians_search_tsv")
    op.execute("DROP INDEX IF EXISTS ix_parties_search_tsv")
    op.execute("DROP INDEX IF EXISTS ix_institutions_search_tsv")
