import uuid

from sqlalchemy import CheckConstraint, Column, ForeignKey, Integer, String, Text, UniqueConstraint
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
    rating = Column(Integer, nullable=False,
                    comment="Rating given by the user to the property between 1 and 5")
    comment = Column(Text, nullable=True)

    # created_at, updated_at from Base

    __table_args__ = (
        UniqueConstraint("property_id", "user_id", name="uq_review_property_user",
                         comment="One review per user per property"),
        CheckConstraint("rating >= 1 AND rating <= 5", name="chk_review_rating_1_to_5",
                        comment="Rating must be between 1 and 5"),
    )
