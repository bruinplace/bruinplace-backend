"""Pydantic schemas for users."""

from typing import Optional

from pydantic import BaseModel, Field


class UserResponse(BaseModel):
    """User response schema (for GET /auth/me and other user-facing endpoints)."""

    id: str
    email: str
    name: Optional[str] = None
    profile_picture: Optional[str] = None

    class Config:
        from_attributes = True


class SavedListingsQuery(BaseModel):
    """Query params for listing saved listings of the current user."""

    limit: int = Field(20, ge=1, le=100)
    offset: int = Field(0, ge=0)


class UserUpdate(BaseModel):
    """Editable fields for the current user's profile."""

    name: str | None = Field(None, min_length=1, max_length=255)
    profile_picture: str | None = None
