from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field

from app.api.v1.listings.schemas import ListingListResponse


class PropertyResponse(BaseModel):
    """Base property response."""

    id: UUID
    name: str
    address: str
    postal_code: str
    city: str
    state: str
    country: str
    latitude: float
    longitude: float
    management_company: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PropertyCreate(BaseModel):
    """Payload for creating a property."""

    name: str = Field(..., min_length=1)
    address: str = Field(..., min_length=1)
    postal_code: str = Field(..., min_length=1)
    city: str = Field(..., min_length=1)
    state: str = Field(..., min_length=1)
    country: str = Field(..., min_length=1)
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    management_company: Optional[str] = None


class PropertyUpdate(BaseModel):
    """Payload for partial updates to a property."""

    name: Optional[str] = Field(None, min_length=1)
    address: Optional[str] = Field(None, min_length=1)
    postal_code: Optional[str] = Field(None, min_length=1)
    city: Optional[str] = Field(None, min_length=1)
    state: Optional[str] = Field(None, min_length=1)
    country: Optional[str] = Field(None, min_length=1)
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)
    management_company: Optional[str] = None


class PropertyReviewStatsResponse(BaseModel):
    """Aggregated review statistics for a property."""

    review_count: int
    average_rating: Optional[float] = None


class PropertyDetailResponse(PropertyResponse):
    """Property details plus review aggregates."""

    review_stats: PropertyReviewStatsResponse


class PropertySearchItemResponse(PropertyResponse):
    """Property item for search/list response."""

    distance_km: Optional[float] = None


class PropertyListResponse(BaseModel):
    """Paginated property search/list response."""

    items: list[PropertySearchItemResponse]
    total: int


class PropertySearchQuery(BaseModel):
    """Query params for searching/listing properties."""

    q: Optional[str] = Field(
        None, description="Text search across name/address/location"
    )
    city: Optional[str] = Field(None, description="Filter by city")
    state: Optional[str] = Field(None, description="Filter by state")
    country: Optional[str] = Field(None, description="Filter by country")
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)
    radius_km: Optional[float] = Field(
        None, gt=0, description="Radius (km) around latitude/longitude"
    )
    limit: int = Field(20, ge=1, le=100)
    offset: int = Field(0, ge=0)


class PropertyListingsQuery(BaseModel):
    """Query params for listing a property's listings."""

    limit: int = Field(20, ge=1, le=100)
    offset: int = Field(0, ge=0)


class PropertyListingsResponse(ListingListResponse):
    """Listings for a property."""


class PropertyReviewResponse(BaseModel):
    """Review response for property review listings."""

    id: UUID
    property_id: UUID
    user_id: str
    rating: int
    comment: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PropertyReviewsQuery(BaseModel):
    """Query params for listing a property's reviews."""

    limit: int = Field(20, ge=1, le=100)
    offset: int = Field(0, ge=0)


class PropertyReviewsResponse(BaseModel):
    """Paginated review list for a property."""

    items: list[PropertyReviewResponse]
    total: int
