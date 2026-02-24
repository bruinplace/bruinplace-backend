import enum
import uuid

from sqlalchemy import (
    Column,
    Date,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID

from app.db.base import Base, SoftDeleteBase


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
    property_id = Column(
        UUID(as_uuid=True),
        ForeignKey("properties.id", ondelete="CASCADE"),
        nullable=False,
    )
    # This refers to the user who added the listing; set to a system user if imported
    owner_id = Column(
        String,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        comment="User ID of the listing owner",
    )

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


class Amenity(Base):
    __tablename__ = "amenities"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    key = Column(
        Text, unique=True, nullable=False, index=True, comment="Stable identifier"
    )
    label = Column(Text, nullable=False, comment="Human-readable amenity name")

    __table_args__ = (UniqueConstraint("key", name="uq_amenity_key"),)

    # created_at, updated_at from Base


class ListingAmenity(Base):
    """Many-to-many join table between listings and amenities."""

    __tablename__ = "listing_amenities"

    listing_id = Column(
        UUID(as_uuid=True),
        ForeignKey("listings.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    )
    amenity_id = Column(
        UUID(as_uuid=True),
        ForeignKey("amenities.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint("listing_id", "amenity_id", name="uq_listing_amenity"),
    )

    # created_at, updated_at from Base


class SavedListing(Base):
    """Many-to-many join table between users and listings."""

    __tablename__ = "saved_listings"

    user_id = Column(
        String,
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    )
    listing_id = Column(
        UUID(as_uuid=True),
        ForeignKey("listings.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    )

    # created_at, updated_at from Base
