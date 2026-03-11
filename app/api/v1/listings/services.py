from datetime import date
from typing import Optional
from uuid import UUID

from fastapi import HTTPException, status as http_status
from sqlalchemy import and_, case, func, or_
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
    ListingMapBounds,
    ListingMapItemResponse,
    ListingMapResponse,
    ListingResponse,
    ListingSearchItemResponse,
    ListingSearchResponse,
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


def _parse_iso_date(value: Optional[str]) -> Optional[date]:
    """Parse YYYY-MM-DD values safely; invalid values are ignored."""
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _normalize_search_query(value: str) -> str:
    """Collapse whitespace and trim user-entered query text."""
    return " ".join(value.split()).strip()


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


def _search_item_to_out(
    *,
    listing: Listing,
    property_row: Property,
    amenities: list[AmenityResponse],
    relevance_score: float,
) -> ListingSearchItemResponse:
    """Build one ranked listing search result."""
    return ListingSearchItemResponse(
        id=listing.id,
        property_id=listing.property_id,
        title=listing.title,
        description=listing.description,
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
        country=property_row.country,
        latitude=property_row.latitude,
        longitude=property_row.longitude,
        amenities=amenities,
        relevance_score=round(relevance_score, 6),
    )


def search_listings(
    db: Session,
    *,
    q: str,
    status: Optional[ListingStatus] = None,
    unit_type: Optional[UnitType] = None,
    min_rent: Optional[int] = None,
    max_rent: Optional[int] = None,
    property_id: Optional[UUID] = None,
    available_from_after: Optional[str] = None,
    min_score: float = 0.12,
) -> ListingSearchResponse:
    """
    Ranked fuzzy search over listing + property + amenity text.

    Uses PostgreSQL full-text ranking (`ts_rank_cd`) and trigram similarity
    (`pg_trgm`) to return typo-tolerant, relevance-sorted listing results.
    """
    normalized_query = _normalize_search_query(q)
    if not normalized_query:
        return ListingSearchResponse(items=[], total=0)

    lower_query = normalized_query.lower()
    contains_pattern = f"%{lower_query}%"
    prefix_pattern = f"{lower_query}%"

    amenities_text_subquery = (
        db.query(
            ListingAmenity.listing_id.label("listing_id"),
            func.string_agg(Amenity.label, " ").label("amenities_text"),
        )
        .join(Amenity, ListingAmenity.amenity_id == Amenity.id)
        .group_by(ListingAmenity.listing_id)
        .subquery()
    )

    listing_text = func.concat_ws(
        " ",
        func.coalesce(Listing.title, ""),
        func.coalesce(Listing.description, ""),
    )
    property_text = func.concat_ws(
        " ",
        func.coalesce(Property.name, ""),
        func.coalesce(Property.address, ""),
        func.coalesce(Property.city, ""),
        func.coalesce(Property.state, ""),
        func.coalesce(Property.postal_code, ""),
        func.coalesce(Property.country, ""),
    )
    amenities_text = func.coalesce(amenities_text_subquery.c.amenities_text, "")
    full_text = func.concat_ws(" ", listing_text, property_text, amenities_text)

    listing_tsv = func.to_tsvector("english", listing_text)
    property_tsv = func.to_tsvector("english", property_text)
    amenities_tsv = func.to_tsvector("english", amenities_text)
    ts_query = func.websearch_to_tsquery("english", normalized_query)

    fts_match = or_(
        listing_tsv.op("@@")(ts_query),
        property_tsv.op("@@")(ts_query),
        amenities_tsv.op("@@")(ts_query),
    )
    fts_rank = (
        func.ts_rank_cd(listing_tsv, ts_query) * 1.8
        + func.ts_rank_cd(property_tsv, ts_query) * 1.6
        + func.ts_rank_cd(amenities_tsv, ts_query) * 1.0
    )

    trigram_score = func.greatest(
        func.similarity(func.coalesce(Listing.title, ""), normalized_query),
        func.similarity(func.coalesce(Listing.description, ""), normalized_query),
        func.similarity(func.coalesce(Property.name, ""), normalized_query),
        func.similarity(func.coalesce(Property.address, ""), normalized_query),
        func.similarity(func.coalesce(Property.city, ""), normalized_query),
        func.similarity(func.coalesce(Property.state, ""), normalized_query),
        func.similarity(amenities_text, normalized_query),
    )

    exact_boost = case(
        (func.lower(Listing.title) == lower_query, 1.1),
        (func.lower(Property.name) == lower_query, 1.0),
        else_=0.0,
    )
    prefix_boost = case(
        (func.lower(Listing.title).like(prefix_pattern), 0.45),
        (func.lower(Property.name).like(prefix_pattern), 0.35),
        else_=0.0,
    )

    relevance_score = (
        (fts_rank * 2.2)
        + (trigram_score * 1.1)
        + exact_boost
        + prefix_boost
    ).label("relevance_score")

    query_len = len(lower_query)
    if query_len <= 3:
        fuzzy_floor = max(min_score, 0.30)
    elif query_len <= 6:
        fuzzy_floor = max(min_score, 0.20)
    else:
        fuzzy_floor = max(min_score, 0.12)

    match_condition = or_(
        fts_match,
        trigram_score >= fuzzy_floor,
        func.lower(full_text).like(contains_pattern),
    )

    search_query = (
        db.query(Listing, Property, relevance_score)
        .join(Property, Listing.property_id == Property.id)
        .outerjoin(
            amenities_text_subquery,
            amenities_text_subquery.c.listing_id == Listing.id,
        )
        .where(
            Listing.deleted_at.is_(None),
            Property.deleted_at.is_(None),
            match_condition,
        )
    )
    if status is not None:
        search_query = search_query.where(Listing.status == status)
    if unit_type is not None:
        search_query = search_query.where(Listing.unit_type == unit_type)
    if min_rent is not None:
        search_query = search_query.where(Listing.monthly_rent >= min_rent)
    if max_rent is not None:
        search_query = search_query.where(Listing.monthly_rent <= max_rent)
    if property_id is not None:
        search_query = search_query.where(Listing.property_id == property_id)

    available_from_date = _parse_iso_date(available_from_after)
    if available_from_date is not None:
        search_query = search_query.where(Listing.available_from >= available_from_date)

    total = search_query.order_by(None).count()
    rows = search_query.order_by(relevance_score.desc(), Listing.created_at.desc()).all()

    listing_ids = [listing.id for listing, _, _ in rows]
    amenities_map = _amenities_for_listing_ids(db=db, listing_ids=listing_ids)
    items = [
        _search_item_to_out(
            listing=listing,
            property_row=property_row,
            amenities=amenities_map.get(listing.id, []),
            relevance_score=float(score or 0.0),
        )
        for listing, property_row, score in rows
    ]
    return ListingSearchResponse(items=items, total=total)


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
    available_from_date = _parse_iso_date(available_from_after)
    if available_from_date is not None:
        q = q.where(Listing.available_from >= available_from_date)

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
    limit: Optional[int] = None,
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
    available_from_date = _parse_iso_date(available_from_after)
    if available_from_date is not None:
        q = q.where(Listing.available_from >= available_from_date)

    total = q.count()
    rows_query = q.order_by(Listing.created_at.desc())
    if limit is not None:
        rows_query = rows_query.limit(limit)
    rows = rows_query.all()
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
