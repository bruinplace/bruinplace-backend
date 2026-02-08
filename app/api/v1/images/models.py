import uuid

from sqlalchemy import Column, ForeignKey, Integer, Text
from sqlalchemy.dialects.postgresql import UUID

from app.db.base import Base


class ImageBase(Base):
    """Abstract base for image models."""

    __abstract__ = True

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    storage_key = Column(Text, nullable=False)
    url = Column(Text, nullable=False)
    display_order = Column(Integer, nullable=False)

    # created_at, updated_at from Base


class PropertyImage(ImageBase):
    """
    Table for property images in object storage. This table is for generic property images (that are not associated to any particular listing).
    """

    __tablename__ = "property_images"

    property_id = Column(
        UUID(as_uuid=True),
        ForeignKey("properties.id", ondelete="CASCADE"),
        nullable=False,
    )


class ListingImage(ImageBase):
    """
    Table for listing images in object storage. All listings are associated with
    a property.
    """

    __tablename__ = "listing_images"

    listing_id = Column(
        UUID(as_uuid=True),
        ForeignKey("listings.id", ondelete="CASCADE"),
        nullable=False,
    )
    property_id = Column(
        UUID(as_uuid=True),
        ForeignKey("properties.id", ondelete="CASCADE"),
        nullable=False,
        comment="Property ID that this listing is associated with",
    )
