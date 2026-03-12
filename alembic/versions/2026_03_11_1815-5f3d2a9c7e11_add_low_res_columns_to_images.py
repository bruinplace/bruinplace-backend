"""Add low-res image columns for listing and property images.

Revision ID: 5f3d2a9c7e11
Revises: 9b8e7a1f2c44
Create Date: 2026-03-11 18:15:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "5f3d2a9c7e11"
down_revision: Union[str, Sequence[str], None] = "9b8e7a1f2c44"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "property_images",
        sa.Column("low_res_storage_key", sa.Text(), nullable=True),
    )
    op.add_column(
        "property_images",
        sa.Column("low_res_url", sa.Text(), nullable=True),
    )
    op.add_column(
        "listing_images",
        sa.Column("low_res_storage_key", sa.Text(), nullable=True),
    )
    op.add_column(
        "listing_images",
        sa.Column("low_res_url", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("listing_images", "low_res_url")
    op.drop_column("listing_images", "low_res_storage_key")
    op.drop_column("property_images", "low_res_url")
    op.drop_column("property_images", "low_res_storage_key")
