from datetime import datetime

from sqlalchemy import Column, DateTime
from sqlalchemy.orm import declarative_base

DeclarativeBase = declarative_base()


class Base(DeclarativeBase):
    """Abstract base model with created_at and updated_at."""

    __abstract__ = True

    created_at = Column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )


class SoftDeleteBase(Base):
    """Abstract base model with soft delete (deleted_at)."""

    __abstract__ = True

    deleted_at = Column(DateTime(timezone=True), nullable=True, default=None)

    def soft_delete(self) -> None:
        """Mark this instance as soft-deleted by setting deleted_at. Caller must commit the session."""
        self.deleted_at = datetime.utcnow()
