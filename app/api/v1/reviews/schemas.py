from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class ReviewResponse(BaseModel):
    """Full review response."""

    id: UUID
    property_id: UUID
    user_id: str
    rating: int
    management_rating: int
    cleanliness_rating: int
    noise_level_rating: int
    lease_flexibility_rating: int
    comment: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ReviewCreate(BaseModel):
    management_rating: int = Field(..., ge=1, le=5)
    cleanliness_rating: int = Field(..., ge=1, le=5)
    noise_level_rating: int = Field(..., ge=1, le=5)
    lease_flexibility_rating: int = Field(..., ge=1, le=5)
    comment: Optional[str] = None


class ReviewUpdate(BaseModel):
    management_rating: Optional[int] = Field(None, ge=1, le=5)
    cleanliness_rating: Optional[int] = Field(None, ge=1, le=5)
    noise_level_rating: Optional[int] = Field(None, ge=1, le=5)
    lease_flexibility_rating: Optional[int] = Field(None, ge=1, le=5)
    comment: Optional[str] = None
