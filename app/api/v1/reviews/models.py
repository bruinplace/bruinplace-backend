import uuid

from sqlalchemy import (
    CheckConstraint,
    Column,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID

from app.db.base import Base


class Review(Base):
    """Property-level review by a user. One review per user per property."""

    __tablename__ = "reviews"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    property_id = Column(
        UUID(as_uuid=True),
        ForeignKey("properties.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id = Column(
        String,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    rating = Column(
        Integer,
        nullable=False,
        comment="Overall rating between 1 and 5 (derived from category ratings).",
    )
    management_rating = Column(Integer, nullable=False)
    cleanliness_rating = Column(Integer, nullable=False)
    noise_level_rating = Column(Integer, nullable=False)
    lease_flexibility_rating = Column(Integer, nullable=False)
    comment = Column(Text, nullable=True)

    # created_at, updated_at from Base

    __table_args__ = (
        UniqueConstraint(
            "property_id",
            "user_id",
            name="uq_review_property_user",
            comment="One review per user per property",
        ),
        CheckConstraint(
            "rating >= 1 AND rating <= 5",
            name="chk_review_rating_1_to_5",
            comment="Overall rating must be between 1 and 5",
        ),
        CheckConstraint(
            "management_rating >= 1 AND management_rating <= 5",
            name="chk_review_management_rating_1_to_5",
        ),
        CheckConstraint(
            "cleanliness_rating >= 1 AND cleanliness_rating <= 5",
            name="chk_review_cleanliness_rating_1_to_5",
        ),
        CheckConstraint(
            "noise_level_rating >= 1 AND noise_level_rating <= 5",
            name="chk_review_noise_level_rating_1_to_5",
        ),
        CheckConstraint(
            "lease_flexibility_rating >= 1 AND lease_flexibility_rating <= 5",
            name="chk_review_lease_flexibility_rating_1_to_5",
        ),
    )
