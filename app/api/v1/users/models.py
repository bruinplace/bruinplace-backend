from datetime import datetime

from sqlalchemy import Column, DateTime, String

from app.db.base import SoftDeleteBase


class User(SoftDeleteBase):
    __tablename__ = "users"

    # Google OIDC subject is stable per client; use as primary key
    id = Column(String, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=True)
    profile_picture = Column(String, nullable=True)

    # created_at, updated_at, deleted_at from SoftDeleteBase
    last_login = Column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
