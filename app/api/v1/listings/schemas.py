from datetime import date, datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field

from app.api.v1.listings.models import ListingStatus, UnitType


class AmenityResponse(BaseModel):
    """Amenity reference (id, key, label) for listing responses."""

    id: UUID
    key: str
    label: str

    class Config:
        from_attributes = True


class ListingCreate(BaseModel):
    """Payload for creating a new listing."""

    property_id: UUID
    title: str = Field(..., min_length=1, max_length=2000)
    description: str = Field(..., min_length=1)
    monthly_rent: int = Field(..., ge=0)
    deposit_amount: Optional[int] = Field(None, ge=0)
    available_from: Optional[date] = None
    lease_term_months: Optional[int] = Field(None, ge=1)
    lease_type: Optional[str] = Field(None, max_length=100)
    unit_type: UnitType
    square_feet: Optional[int] = Field(None, ge=0)
    max_occupants: Optional[int] = Field(None, ge=1)
    status: ListingStatus = ListingStatus.DRAFT
    amenity_ids: list[UUID] = Field(default_factory=list)


class ListingUpdate(BaseModel):
    """Payload for partial update of a listing; all fields optional."""

    title: Optional[str] = Field(None, min_length=1, max_length=2000)
    description: Optional[str] = Field(None, min_length=1)
    monthly_rent: Optional[int] = Field(None, ge=0)
    deposit_amount: Optional[int] = Field(None, ge=0)
    available_from: Optional[date] = None
    lease_term_months: Optional[int] = Field(None, ge=1)
    lease_type: Optional[str] = Field(None, max_length=100)
    unit_type: Optional[UnitType] = None
    square_feet: Optional[int] = Field(None, ge=0)
    max_occupants: Optional[int] = Field(None, ge=1)
    status: Optional[ListingStatus] = None
    amenity_ids: Optional[list[UUID]] = None


class ListingResponse(BaseModel):
    """Full listing response including amenities."""

    id: UUID
    property_id: UUID
    user_id: str
    title: str
    description: str
    monthly_rent: int
    deposit_amount: Optional[int]
    available_from: Optional[date]
    lease_term_months: Optional[int]
    lease_type: Optional[str]
    unit_type: UnitType
    square_feet: Optional[int]
    max_occupants: Optional[int]
    status: ListingStatus
    created_at: datetime
    updated_at: datetime
    amenities: list[AmenityResponse] = Field(default_factory=list)

    class Config:
        from_attributes = True


class ListingFilterQuery(BaseModel):
    """Query parameters for searching and filtering listings."""

    status: Optional[ListingStatus] = Field(None, description="Filter by status")
    unit_type: Optional[UnitType] = Field(None, description="Filter by unit type")
    min_rent: Optional[int] = Field(None, ge=0, description="Minimum monthly rent")
    max_rent: Optional[int] = Field(None, ge=0, description="Maximum monthly rent")
    property_id: Optional[UUID] = Field(None, description="Filter by property")
    search: Optional[str] = Field(None, description="Search in title and description")
    available_from_after: Optional[str] = Field(
        None,
        description="Listings available on or after this date (YYYY-MM-DD)",
    )
    limit: int = Field(20, ge=1, le=100)
    offset: int = Field(0, ge=0)


class ListingListResponse(BaseModel):
    """Paginated list of listings with total count."""

    items: list[ListingResponse]
    total: int


class ListingMapQuery(BaseModel):
    """Query parameters for map viewport listing fetches."""

    north: float = Field(..., ge=-90, le=90)
    south: float = Field(..., ge=-90, le=90)
    east: float = Field(..., ge=-180, le=180)
    west: float = Field(..., ge=-180, le=180)
    pad_ratio: float = Field(
        0.15,
        ge=0,
        le=1,
        description="Extra bounds percentage loaded beyond viewport",
    )
    status: Optional[ListingStatus] = Field(None, description="Filter by status")
    unit_type: Optional[UnitType] = Field(None, description="Filter by unit type")
    min_rent: Optional[int] = Field(None, ge=0, description="Minimum monthly rent")
    max_rent: Optional[int] = Field(None, ge=0, description="Maximum monthly rent")
    search: Optional[str] = Field(None, description="Search in listing/property text")
    available_from_after: Optional[str] = Field(
        None,
        description="Listings available on or after this date (YYYY-MM-DD)",
    )
    limit: Optional[int] = Field(
        None,
        ge=1,
        description="Optional max number of results to return. Defaults to no cap.",
    )


class ListingMapBounds(BaseModel):
    """Bounds applied by the backend after optional padding."""

    north: float
    south: float
    east: float
    west: float


class ListingMapItemResponse(BaseModel):
    """Map-optimized listing payload with coordinates."""

    id: UUID
    property_id: UUID
    title: str
    monthly_rent: int
    unit_type: UnitType
    square_feet: Optional[int]
    status: ListingStatus
    created_at: datetime
    property_name: str
    address: str
    city: str
    state: str
    postal_code: str
    latitude: float
    longitude: float


class ListingMapResponse(BaseModel):
    """Map viewport query response."""

    items: list[ListingMapItemResponse]
    total: int
    has_more: bool
    applied_bounds: ListingMapBounds


class ListingSearchQuery(BaseModel):
    """Query parameters for ranked full-text/fuzzy listing search."""

    q: str = Field(..., min_length=1, description="Search query text")
    status: Optional[ListingStatus] = Field(None, description="Filter by status")
    unit_type: Optional[UnitType] = Field(None, description="Filter by unit type")
    min_rent: Optional[int] = Field(None, ge=0, description="Minimum monthly rent")
    max_rent: Optional[int] = Field(None, ge=0, description="Maximum monthly rent")
    property_id: Optional[UUID] = Field(None, description="Filter by property")
    available_from_after: Optional[str] = Field(
        None,
        description="Listings available on or after this date (YYYY-MM-DD)",
    )
    min_score: float = Field(
        0.12,
        ge=0,
        le=1,
        description="Minimum trigram similarity score for fuzzy-only matches",
    )


class ListingSearchItemResponse(BaseModel):
    """Ranked listing search result with listing, property, and score metadata."""

    id: UUID
    property_id: UUID
    title: str
    description: str
    monthly_rent: int
    unit_type: UnitType
    square_feet: Optional[int]
    status: ListingStatus
    created_at: datetime
    property_name: str
    address: str
    city: str
    state: str
    postal_code: str
    country: str
    latitude: float
    longitude: float
    amenities: list[AmenityResponse] = Field(default_factory=list)
    relevance_score: float


class ListingSearchResponse(BaseModel):
    """Unpaginated listing search response."""

    items: list[ListingSearchItemResponse]
    total: int
