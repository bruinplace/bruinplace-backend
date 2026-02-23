import math
from typing import Optional
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.api.v1.listings.services import get_listings as get_listings_for_property
from app.api.v1.properties.models import Property
from app.api.v1.properties.schemas import (
    PropertyCreate,
    PropertyDetailResponse,
    PropertyListResponse,
    PropertyListingsResponse,
    PropertyResponse,
    PropertyReviewsResponse,
    PropertyReviewResponse,
    PropertyReviewStatsResponse,
    PropertySearchItemResponse,
    PropertySearchQuery,
    PropertyUpdate,
)
from app.api.v1.reviews.models import Review


def _to_search_item(
    property_obj: Property, latitude: Optional[float], longitude: Optional[float]
) -> PropertySearchItemResponse:
    """Convert a Property ORM row into PropertySearchItemResponse."""
    distance_km = None
    if latitude is not None and longitude is not None:
        distance_km = _haversine_km(
            latitude, longitude, property_obj.latitude, property_obj.longitude
        )
    return PropertySearchItemResponse(
        id=property_obj.id,
        name=property_obj.name,
        address=property_obj.address,
        postal_code=property_obj.postal_code,
        city=property_obj.city,
        state=property_obj.state,
        country=property_obj.country,
        latitude=property_obj.latitude,
        longitude=property_obj.longitude,
        management_company=property_obj.management_company,
        created_at=property_obj.created_at,
        updated_at=property_obj.updated_at,
        distance_km=distance_km,
    )


def _haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Great-circle distance in kilometers."""
    r = 6371.0
    lat1_r = math.radians(lat1)
    lat2_r = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lng = math.radians(lng2 - lng1)
    a = (
        math.sin(delta_lat / 2) ** 2
        + math.cos(lat1_r) * math.cos(lat2_r) * math.sin(delta_lng / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return round(r * c, 3)


def _get_property_or_404(db: Session, property_id: UUID) -> Property:
    """Fetch one non-deleted property or raise 404."""
    property_obj = (
        db.query(Property)
        .where(Property.id == property_id, Property.deleted_at.is_(None))
        .first()
    )
    if not property_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Property not found"
        )
    return property_obj


def _to_property_response(property_obj: Property) -> PropertyResponse:
    """Convert Property ORM row to PropertyResponse."""
    return PropertyResponse(
        id=property_obj.id,
        name=property_obj.name,
        address=property_obj.address,
        postal_code=property_obj.postal_code,
        city=property_obj.city,
        state=property_obj.state,
        country=property_obj.country,
        latitude=property_obj.latitude,
        longitude=property_obj.longitude,
        management_company=property_obj.management_company,
        created_at=property_obj.created_at,
        updated_at=property_obj.updated_at,
    )


def search_properties(db: Session, params: PropertySearchQuery) -> PropertyListResponse:
    """
    Search/list properties using text and optional geospatial filters.

    Simpler approach:
    - Do text/location filtering in SQL.
    - If latitude/longitude are provided, compute distance in Python.
    - If radius_km is provided, filter by radius in Python.
    """
    q = db.query(Property).where(Property.deleted_at.is_(None))

    if params.q:
        term = f"%{params.q.strip()}%"
        q = q.where(
            or_(
                Property.name.ilike(term),
                Property.address.ilike(term),
                Property.city.ilike(term),
                Property.state.ilike(term),
                Property.country.ilike(term),
                Property.postal_code.ilike(term),
            )
        )

    if params.city:
        q = q.where(Property.city.ilike(f"%{params.city.strip()}%"))
    if params.state:
        q = q.where(Property.state.ilike(f"%{params.state.strip()}%"))
    if params.country:
        q = q.where(Property.country.ilike(f"%{params.country.strip()}%"))

    rows = q.order_by(Property.created_at.desc()).all()
    items = [
        _to_search_item(
            property_obj=row,
            latitude=params.latitude,
            longitude=params.longitude,
        )
        for row in rows
    ]

    if params.radius_km is not None:
        # Radius requires a center point; if not provided, ignore radius filter.
        if params.latitude is not None and params.longitude is not None:
            items = [
                item
                for item in items
                if item.distance_km is not None and item.distance_km <= params.radius_km
            ]

    if params.latitude is not None and params.longitude is not None:
        # When distance is available, show closest properties first.
        items.sort(
            key=lambda item: (
                item.distance_km if item.distance_km is not None else float("inf")
            )
        )

    total = len(items)
    items = items[params.offset : params.offset + params.limit]
    return PropertyListResponse(items=items, total=total)


def create_property(db: Session, data: PropertyCreate) -> PropertyResponse:
    """Create a property."""
    property_obj = Property(
        name=data.name,
        address=data.address,
        postal_code=data.postal_code,
        city=data.city,
        state=data.state,
        country=data.country,
        latitude=data.latitude,
        longitude=data.longitude,
        management_company=data.management_company,
    )
    db.add(property_obj)
    db.commit()
    db.refresh(property_obj)
    return _to_property_response(property_obj=property_obj)


def update_property(
    db: Session, property_id: UUID, data: PropertyUpdate
) -> PropertyResponse:
    """Update a property with partial fields."""
    property_obj = _get_property_or_404(db=db, property_id=property_id)
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(property_obj, key, value)
    db.commit()
    db.refresh(property_obj)
    return _to_property_response(property_obj=property_obj)


def soft_delete_property(db: Session, property_id: UUID) -> None:
    """Soft-delete a property."""
    property_obj = _get_property_or_404(db=db, property_id=property_id)
    property_obj.soft_delete()
    db.commit()


def get_property_detail(db: Session, property_id: UUID) -> PropertyDetailResponse:
    """Get property details and aggregated review statistics."""
    property_obj = _get_property_or_404(db=db, property_id=property_id)
    review_count, average_rating = (
        db.query(func.count(Review.id), func.avg(Review.rating))
        .where(Review.property_id == property_id)
        .one()
    )
    return PropertyDetailResponse(
        id=property_obj.id,
        name=property_obj.name,
        address=property_obj.address,
        postal_code=property_obj.postal_code,
        city=property_obj.city,
        state=property_obj.state,
        country=property_obj.country,
        latitude=property_obj.latitude,
        longitude=property_obj.longitude,
        management_company=property_obj.management_company,
        created_at=property_obj.created_at,
        updated_at=property_obj.updated_at,
        review_stats=PropertyReviewStatsResponse(
            review_count=int(review_count or 0),
            average_rating=(
                round(float(average_rating), 2) if average_rating else None
            ),
        ),
    )


def get_property_listings(
    db: Session, property_id: UUID, limit: int, offset: int
) -> PropertyListingsResponse:
    """Get listings associated with a property."""
    _get_property_or_404(db=db, property_id=property_id)
    return PropertyListingsResponse.model_validate(
        get_listings_for_property(
            db=db,
            property_id=property_id,
            limit=limit,
            offset=offset,
        )
    )


def get_property_reviews(
    db: Session, property_id: UUID, limit: int, offset: int
) -> PropertyReviewsResponse:
    """Get reviews associated with a property."""
    _get_property_or_404(db=db, property_id=property_id)
    q = db.query(Review).where(Review.property_id == property_id)
    total = q.count()
    rows = q.order_by(Review.created_at.desc()).offset(offset).limit(limit).all()
    items = [PropertyReviewResponse.model_validate(row) for row in rows]
    return PropertyReviewsResponse(items=items, total=total)
