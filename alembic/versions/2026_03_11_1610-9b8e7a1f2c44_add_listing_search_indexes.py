"""Add listing search indexes for full-text and fuzzy matching.

Revision ID: 9b8e7a1f2c44
Revises: 6c9f7a1d9f04
Create Date: 2026-03-11 16:10:00.000000

"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "9b8e7a1f2c44"
down_revision: Union[str, Sequence[str], None] = "6c9f7a1d9f04"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_listings_search_tsv
        ON listings
        USING GIN (
            to_tsvector(
                'english',
                coalesce(title, '') || ' ' || coalesce(description, '')
            )
        )
        WHERE deleted_at IS NULL
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_listings_search_trgm
        ON listings
        USING GIN (
            (
                coalesce(title, '') || ' ' || coalesce(description, '')
            ) gin_trgm_ops
        )
        WHERE deleted_at IS NULL
        """
    )

    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_properties_search_tsv
        ON properties
        USING GIN (
            to_tsvector(
                'english',
                coalesce(name, '') || ' ' || coalesce(address, '') || ' ' ||
                coalesce(city, '') || ' ' || coalesce(state, '') || ' ' ||
                coalesce(postal_code, '') || ' ' || coalesce(country, '')
            )
        )
        WHERE deleted_at IS NULL
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_properties_search_trgm
        ON properties
        USING GIN (
            (
                coalesce(name, '') || ' ' || coalesce(address, '') || ' ' ||
                coalesce(city, '') || ' ' || coalesce(state, '') || ' ' ||
                coalesce(postal_code, '') || ' ' || coalesce(country, '')
            ) gin_trgm_ops
        )
        WHERE deleted_at IS NULL
        """
    )

    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_amenities_label_trgm
        ON amenities
        USING GIN (label gin_trgm_ops)
        """
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("DROP INDEX IF EXISTS ix_amenities_label_trgm")
    op.execute("DROP INDEX IF EXISTS ix_properties_search_trgm")
    op.execute("DROP INDEX IF EXISTS ix_properties_search_tsv")
    op.execute("DROP INDEX IF EXISTS ix_listings_search_trgm")
    op.execute("DROP INDEX IF EXISTS ix_listings_search_tsv")
