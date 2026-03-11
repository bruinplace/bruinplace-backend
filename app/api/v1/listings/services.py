from datetime import date
from typing import Optional
from uuid import UUID

from fastapi import HTTPException, status as http_status
from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from app.api.v1.listings.models import (
    Amenity,
    Listing,
    ListingAmenity,
    ListingStatus,
    UnitType,
    SavedListing,
)
from app.api.v1.listings.schemas import (
    AmenityResponse,
    ListingCreate,
    ListingListResponse,
    ListingResponse,
    ListingMapBounds,
    ListingMapItemResponse,
    ListingMapResponse,
    ListingUpdate,
)
from app.api.v1.properties.models import Property


def list_amenities(db: Session) -> list[AmenityResponse]:
    """
    Return all amenities, ordered by key.

    Used when building create/edit listing forms so clients can show checkboxes
    or a multi-select for amenities.
    """
    rows = db.query(Amenity).order_by(Amenity.key).all()
    return [AmenityResponse.model_validate(r) for r in rows]


def _amenities_for_listing_ids(
    db: Session, listing_ids: list[UUID]
) -> dict[UUID, list[AmenityResponse]]:
    """
    Load amenities for multiple listings in one query (avoids N+1).

    Returns:
        Mapping of listing_id -> list of AmenityResponse for that listing.
    """
    if not listing_ids:
        return {}
    pairs = (
        db.query(ListingAmenity.listing_id, Amenity)
        .join(Amenity, ListingAmenity.amenity_id == Amenity.id)
        .where(ListingAmenity.listing_id.in_(listing_ids))
        .all()
    )
    by_listing = {lid: [] for lid in listing_ids}
    for listing_id, amenity in pairs:
        by_listing[listing_id].append(AmenityResponse.model_validate(amenity))
    return by_listing


def _clamp(value: float, lower: float, upper: float) -> float:
    return max(lower, min(upper, value))


def _normalize_longitude(value: float) -> float:
    normalized = ((value + 180.0) % 360.0) - 180.0
    if normalized == -180.0 and value > 0:
        return 180.0
    return normalized


def _longitude_span_degrees(west: float, east: float) -> float:
    span = east - west
    if span < 0:
        span += 360.0
    return span


def _with_padding(
    *,
    north: float,
    south: float,
    east: float,
    west: float,
    pad_ratio: float,
) -> ListingMapBounds:
    lat_span = max(north - south, 1e-6)
    lng_span = max(_longitude_span_degrees(west=west, east=east), 1e-6)

    lat_pad = lat_span * pad_ratio
    lng_pad = lng_span * pad_ratio

    return ListingMapBounds(
        north=_clamp(north + lat_pad, -90.0, 90.0),
        south=_clamp(south - lat_pad, -90.0, 90.0),
        east=_normalize_longitude(east + lng_pad),
        west=_normalize_longitude(west - lng_pad),
    )


def _longitude_in_bounds_condition(
    *,
    west: float,
    east: float,
):
    if west <= east:
        return and_(Property.longitude >= west, Property.longitude <= east)
    return or_(Property.longitude >= west, Property.longitude <= east)


def _map_item_to_out(*, listing: Listing, property_row: Property) -> ListingMapItemResponse:
    return ListingMapItemResponse(
        id=listing.id,
        property_id=listing.property_id,
        title=listing.title,
        monthly_rent=listing.monthly_rent,
        unit_type=listing.unit_type,
        square_feet=listing.square_feet,
        status=listing.status,
        created_at=listing.created_at,
        property_name=property_row.name,
        address=property_row.address,
        city=property_row.city,
        state=property_row.state,
        postal_code=property_row.postal_code,
        latitude=property_row.latitude,
        longitude=property_row.longitude,
    )


def _listing_to_out(
    listing: Listing, amenities: list[AmenityResponse]
) -> ListingResponse:
    """Build a ListingResponse from an ORM Listing and its preloaded amenities."""
    return ListingResponse(
        id=listing.id,
        property_id=listing.property_id,
        # Schema still exposes user_id; map from model owner_id.
        user_id=listing.owner_id,
        title=listing.title,
        description=listing.description,
        monthly_rent=listing.monthly_rent,
        deposit_amount=listing.deposit_amount,
        available_from=listing.available_from,
        lease_term_months=listing.lease_term_months,
        lease_type=listing.lease_type,
        unit_type=listing.unit_type,
        square_feet=listing.square_feet,
        max_occupants=listing.max_occupants,
        status=listing.status,
        created_at=listing.created_at,
        updated_at=listing.updated_at,
        amenities=amenities,
    )


def get_listings(
    db: Session,
    *,
    status: Optional[ListingStatus] = None,
    unit_type: Optional[UnitType] = None,
    min_rent: Optional[int] = None,
    max_rent: Optional[int] = None,
    property_id: Optional[UUID] = None,
    search: Optional[str] = None,
    available_from_after: Optional[str] = None,
    limit: int = 20,
    offset: int = 0,
) -> ListingListResponse:
    """
    Search and filter listings with pagination.

    Excludes soft-deleted listings. Applies optional filters for status,
    unit type, rent range, property, text search (title/description), and
    availability date. Results are ordered by created_at descending.

    Returns:
        ListingListResponse with items and total count.
    """
    q = db.query(Listing).where(Listing.deleted_at.is_(None))
    if status is not None:
        q = q.where(Listing.status == status)
    if unit_type is not None:
        q = q.where(Listing.unit_type == unit_type)
    if min_rent is not None:
        q = q.where(Listing.monthly_rent >= min_rent)
    if max_rent is not None:
        q = q.where(Listing.monthly_rent <= max_rent)
    if property_id is not None:
        q = q.where(Listing.property_id == property_id)
    if search:
        term = f"%{search.strip()}%"
        q = q.where(
            or_(
                Listing.title.ilike(term),
                Listing.description.ilike(term),
            )
        )
    if available_from_after:
        try:
            d = date.fromisoformat(available_from_after)
            q = q.where(Listing.available_from >= d)
        except ValueError:
            pass  # Invalid date string: ignore filter

    total = q.count()
    rows = q.order_by(Listing.created_at.desc()).offset(offset).limit(limit).all()
    listing_ids = [r.id for r in rows]
    amenities_map = _amenities_for_listing_ids(db=db, listing_ids=listing_ids)
    items = [
        _listing_to_out(
            listing=listing,
            amenities=amenities_map.get(listing.id, []),
        )
        for listing in rows
    ]
    return ListingListResponse(items=items, total=total)


def get_listings_in_bounds(
    db: Session,
    *,
    north: float,
    south: float,
    east: float,
    west: float,
    pad_ratio: float = 0.15,
    status: Optional[ListingStatus] = None,
    unit_type: Optional[UnitType] = None,
    min_rent: Optional[int] = None,
    max_rent: Optional[int] = None,
    search: Optional[str] = None,
    available_from_after: Optional[str] = None,
    limit: int = 120,
) -> ListingMapResponse:
    """Return listings inside (optionally padded) map bounds."""
    if south > north:
        raise HTTPException(
            status_code=http_status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="south must be less than or equal to north",
        )

    applied_bounds = _with_padding(
        north=north,
        south=south,
        east=east,
        west=west,
        pad_ratio=pad_ratio,
    )

    q = (
        db.query(Listing, Property)
        .join(Property, Listing.property_id == Property.id)
        .where(
            Listing.deleted_at.is_(None),
            Property.deleted_at.is_(None),
            Property.latitude >= applied_bounds.south,
            Property.latitude <= applied_bounds.north,
            _longitude_in_bounds_condition(
                west=applied_bounds.west,
                east=applied_bounds.east,
            ),
        )
    )

    if status is not None:
        q = q.where(Listing.status == status)
    if unit_type is not None:
        q = q.where(Listing.unit_type == unit_type)
    if min_rent is not None:
        q = q.where(Listing.monthly_rent >= min_rent)
    if max_rent is not None:
        q = q.where(Listing.monthly_rent <= max_rent)
    if search:
        term = f"%{search.strip()}%"
        q = q.where(
            or_(
                Listing.title.ilike(term),
                Listing.description.ilike(term),
                Property.name.ilike(term),
                Property.address.ilike(term),
            )
        )
    if available_from_after:
        try:
            d = date.fromisoformat(available_from_after)
            q = q.where(Listing.available_from >= d)
        except ValueError:
            pass

    total = q.count()
    rows = q.order_by(Listing.created_at.desc()).limit(limit).all()
    items = [
        _map_item_to_out(listing=listing, property_row=property_row)
        for listing, property_row in rows
    ]
    return ListingMapResponse(
        items=items,
        total=total,
        has_more=total > len(items),
        applied_bounds=applied_bounds,
    )


def get_listing_by_id(db: Session, listing_id: UUID) -> Optional[ListingResponse]:
    """
    Return full listing details by ID, including amenities.

    Returns None if the listing does not exist or has been soft-deleted.
    """
    listing = (
        db.query(Listing)
        .where(and_(Listing.id == listing_id, Listing.deleted_at.is_(None)))
        .first()
    )
    if not listing:
        return None

    amenities = _amenities_for_listing_ids(db=db, listing_ids=[listing.id]).get(
        listing.id, []
    )
    return _listing_to_out(listing=listing, amenities=amenities)


def create_listing(db: Session, user_id: str, data: ListingCreate) -> ListingResponse:
    """
    Create a new listing owned by the given user.

    Validates that the property exists before creating. Inserts the listing
    and its listing_amenities in one transaction.

    Raises:
        HTTPException: 404 if the payload's property_id does not exist.
    """
    property_exists = db.get(Property, data.property_id) is not None
    if not property_exists:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="Property not found",
        )
    listing = Listing(
        property_id=data.property_id,
        owner_id=user_id,
        title=data.title,
        description=data.description,
        monthly_rent=data.monthly_rent,
        deposit_amount=data.deposit_amount,
        available_from=data.available_from,
        lease_term_months=data.lease_term_months,
        lease_type=data.lease_type,
        unit_type=data.unit_type,
        square_feet=data.square_feet,
        max_occupants=data.max_occupants,
        status=data.status,
    )
    db.add(listing)
    db.flush()  # Get listing.id before adding listing_amenities

    # Add listing_amenities
    for amenity_id in data.amenity_ids:
        db.add(ListingAmenity(listing_id=listing.id, amenity_id=amenity_id))
    db.commit()

    db.refresh(listing)
    amenities = _amenities_for_listing_ids(db=db, listing_ids=[listing.id]).get(
        listing.id, []
    )
    return _listing_to_out(listing=listing, amenities=amenities)


def update_listing(
    db: Session, listing_id: UUID, user_id: str, data: ListingUpdate
) -> Optional[ListingResponse]:
    """
    Update a listing (owner only); partial update supported.

    Only fields present in data are updated. If amenity_ids is provided, the
    listing's amenities are replaced with the given set. Returns None if the
    listing is not found, soft-deleted, or the user is not the owner.
    """
    listing = (
        db.query(Listing)
        .where(and_(Listing.id == listing_id, Listing.deleted_at.is_(None)))
        .first()
    )
    if not listing or listing.owner_id != user_id:
        return None

    update = data.model_dump(exclude_unset=True)
    amenity_ids = update.pop("amenity_ids", None)
    for key, value in update.items():
        setattr(listing, key, value)

    if amenity_ids is not None:
        # Replace all listing_amenities with the new set
        db.query(ListingAmenity).where(ListingAmenity.listing_id == listing_id).delete()
        for aid in amenity_ids:
            db.add(ListingAmenity(listing_id=listing_id, amenity_id=aid))

    db.commit()
    db.refresh(listing)

    amenities = _amenities_for_listing_ids(db=db, listing_ids=[listing.id]).get(
        listing.id, []
    )
    return _listing_to_out(listing=listing, amenities=amenities)


def soft_delete_listing(db: Session, listing_id: UUID, user_id: str) -> bool:
    """
    Soft-delete a listing (owner only).

    Sets deleted_at so the listing is excluded from queries. Returns True if
    the listing was found and deleted; False if not found, already deleted,
    or the user is not the owner.
    """
    listing = (
        db.query(Listing)
        .where(and_(Listing.id == listing_id, Listing.deleted_at.is_(None)))
        .first()
    )
    if not listing or listing.owner_id != user_id:
        return False
    listing.soft_delete()
    db.commit()
    return True


def get_saved_listings(
    db: Session, *, user_id: str, limit: int = 20, offset: int = 0
) -> ListingListResponse:
    """
    Return listings saved by the given user, including amenities.

    Excludes soft-deleted listings. Ordered by when the listing was created
    (desc) to match general listing ordering.
    """
    q = (
        db.query(Listing)
        .join(SavedListing, SavedListing.listing_id == Listing.id)
        .where(
            SavedListing.user_id == user_id,
            Listing.deleted_at.is_(None),
        )
    )
    total = q.count()
    rows = q.order_by(Listing.created_at.desc()).offset(offset).limit(limit).all()
    listing_ids = [r.id for r in rows]
    amenities_map = _amenities_for_listing_ids(db=db, listing_ids=listing_ids)
    items = [
        _listing_to_out(listing=listing, amenities=amenities_map.get(listing.id, []))
        for listing in rows
    ]
    return ListingListResponse(items=items, total=total)


def save_listing_for_user(db: Session, *, user_id: str, listing_id: UUID) -> bool:
    """Save a listing for a user. Returns True if created, False if already saved."""
    # Ensure listing exists and is not soft-deleted
    listing = (
        db.query(Listing)
        .where(Listing.id == listing_id, Listing.deleted_at.is_(None))
        .first()
    )
    if not listing:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="Listing not found",
        )

    exists = (
        db.query(SavedListing)
        .where(
            SavedListing.user_id == user_id,
            SavedListing.listing_id == listing_id,
        )
        .first()
        is not None
    )
    if exists:
        return False

    db.add(SavedListing(user_id=user_id, listing_id=listing_id))
    db.commit()
    return True


def unsave_listing_for_user(db: Session, *, user_id: str, listing_id: UUID) -> bool:
    """Remove a saved listing. Returns True if deleted, False if not present."""
    q = db.query(SavedListing).where(
        SavedListing.user_id == user_id, SavedListing.listing_id == listing_id
    )
    if q.first() is None:
        return False
    q.delete(synchronize_session=False)
    db.commit()
    return True
