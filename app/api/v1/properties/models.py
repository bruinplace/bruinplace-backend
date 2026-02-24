import uuid

from sqlalchemy import Column, Float, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID

from app.db.base import SoftDeleteBase


class Property(SoftDeleteBase):
    __tablename__ = "properties"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # This refers to the user who added the property; set to a system user if imported
    owner_id = Column(
        String,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        comment="User ID of the property owner",
    )

    name = Column(Text, nullable=False)
    address = Column(Text, nullable=False)
    postal_code = Column(String, nullable=False)
    city = Column(String, nullable=False)
    state = Column(String, nullable=False)
    country = Column(String, nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    management_company = Column(String, nullable=True)

    # created_at, updated_at, deleted_at from SoftDeleteBase
