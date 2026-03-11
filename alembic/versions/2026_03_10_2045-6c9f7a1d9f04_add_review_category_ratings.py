"""Add category ratings columns to reviews.

Revision ID: 6c9f7a1d9f04
Revises: aadb6c07d39b
Create Date: 2026-03-10 20:45:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "6c9f7a1d9f04"
down_revision: Union[str, Sequence[str], None] = "aadb6c07d39b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "reviews",
        sa.Column("management_rating", sa.Integer(), nullable=False, server_default="3"),
    )
    op.add_column(
        "reviews",
        sa.Column("cleanliness_rating", sa.Integer(), nullable=False, server_default="3"),
    )
    op.add_column(
        "reviews",
        sa.Column("noise_level_rating", sa.Integer(), nullable=False, server_default="3"),
    )
    op.add_column(
        "reviews",
        sa.Column(
            "lease_flexibility_rating", sa.Integer(), nullable=False, server_default="3"
        ),
    )

    # If legacy rows exist, backfill from overall rating.
    op.execute(
        """
        UPDATE reviews
        SET
            management_rating = rating,
            cleanliness_rating = rating,
            noise_level_rating = rating,
            lease_flexibility_rating = rating
        """
    )

    op.create_check_constraint(
        "chk_review_management_rating_1_to_5",
        "reviews",
        "management_rating >= 1 AND management_rating <= 5",
    )
    op.create_check_constraint(
        "chk_review_cleanliness_rating_1_to_5",
        "reviews",
        "cleanliness_rating >= 1 AND cleanliness_rating <= 5",
    )
    op.create_check_constraint(
        "chk_review_noise_level_rating_1_to_5",
        "reviews",
        "noise_level_rating >= 1 AND noise_level_rating <= 5",
    )
    op.create_check_constraint(
        "chk_review_lease_flexibility_rating_1_to_5",
        "reviews",
        "lease_flexibility_rating >= 1 AND lease_flexibility_rating <= 5",
    )

    op.alter_column("reviews", "management_rating", server_default=None)
    op.alter_column("reviews", "cleanliness_rating", server_default=None)
    op.alter_column("reviews", "noise_level_rating", server_default=None)
    op.alter_column("reviews", "lease_flexibility_rating", server_default=None)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint(
        "chk_review_lease_flexibility_rating_1_to_5", "reviews", type_="check"
    )
    op.drop_constraint("chk_review_noise_level_rating_1_to_5", "reviews", type_="check")
    op.drop_constraint("chk_review_cleanliness_rating_1_to_5", "reviews", type_="check")
    op.drop_constraint("chk_review_management_rating_1_to_5", "reviews", type_="check")
    op.drop_column("reviews", "lease_flexibility_rating")
    op.drop_column("reviews", "noise_level_rating")
    op.drop_column("reviews", "cleanliness_rating")
    op.drop_column("reviews", "management_rating")
