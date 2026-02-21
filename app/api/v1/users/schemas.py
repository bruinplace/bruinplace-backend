"""Pydantic schemas for users."""

from typing import Optional

from pydantic import BaseModel


class UserResponse(BaseModel):
    """User response schema (for GET /auth/me and other user-facing endpoints)."""

    id: str
    email: str
    name: Optional[str] = None
    profile_picture: Optional[str] = None

    class Config:
        from_attributes = True
