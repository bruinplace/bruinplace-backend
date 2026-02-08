import enum
import uuid

from sqlalchemy import Column, Date, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID

from app.db.base import SoftDeleteBase


class UnitType(str, enum.Enum):
    """Listing unit type."""

    STUDIO = "studio"
    ONE_B_ONE_B = "1b1b"
    TWO_B_TWO_B = "2b2b"
    SHARED_ROOM = "shared_room"
    PRIVATE_ROOM = "private_room"
    OTHER = "other"


class ListingStatus(str, enum.Enum):
    """Listing lifecycle status."""

    DRAFT = "draft"
    ACTIVE = "active"
    RENTED = "rented"
    ARCHIVED = "archived"


class Listing(SoftDeleteBase):
    __tablename__ = "listings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    property_id = Column(UUID(as_uuid=True), ForeignKey("properties.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    title = Column(Text, nullable=False)
    description = Column(Text, nullable=False)
    monthly_rent = Column(Integer, nullable=False)
    deposit_amount = Column(Integer, nullable=True)
    available_from = Column(Date, nullable=True)
    lease_term_months = Column(Integer, nullable=True)
    lease_type = Column(String, nullable=True)
    unit_type = Column(Enum(UnitType), nullable=False)
    square_feet = Column(Integer, nullable=True)
    max_occupants = Column(Integer, nullable=True)
    status = Column(Enum(ListingStatus), default=ListingStatus.DRAFT, nullable=False)

    # created_at, updated_at, deleted_at from SoftDeleteBase
