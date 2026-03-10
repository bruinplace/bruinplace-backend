from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.api.v1.users.models import User
from app.api.v1.properties.schemas import (
    PropertyCreate,
    PropertyDetailResponse,
    PropertyListingsQuery,
    PropertyListingsResponse,
    PropertyListResponse,
    PropertyResponse,
    PropertyReviewsQuery,
    PropertyReviewsResponse,
    PropertySearchQuery,
    PropertyUpdate,
)
from app.api.v1.properties.services import (
    create_property,
    get_property_detail,
    get_property_listings,
    get_property_reviews,
    search_properties,
    soft_delete_property,
    update_property,
)

router = APIRouter()


@router.get("", response_model=PropertyListResponse)
def get_properties_controller(
    db: Session = Depends(get_db),
    params: PropertySearchQuery = Depends(),
):
    """Search and list properties using text or geospatial queries."""
    return search_properties(db=db, params=params)


@router.post("", response_model=PropertyResponse, status_code=status.HTTP_201_CREATED)
def post_property_controller(
    payload: PropertyCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Create a property."""
    return create_property(db=db, data=payload, user_id=user.id)


@router.get("/{property_id}", response_model=PropertyDetailResponse)
def get_property_controller(
    property_id: UUID,
    db: Session = Depends(get_db),
):
    """Return property details and aggregated review statistics."""
    return get_property_detail(db=db, property_id=property_id)


@router.patch("/{property_id}", response_model=PropertyResponse)
def patch_property_controller(
    property_id: UUID,
    payload: PropertyUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Partially update a property."""
    return update_property(
        db=db,
        property_id=property_id,
        user_id=user.id,
        data=payload,
    )


@router.delete("/{property_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_property_controller(
    property_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Soft-delete a property."""
    soft_delete_property(db=db, property_id=property_id, user_id=user.id)


@router.get("/{property_id}/listings", response_model=PropertyListingsResponse)
def get_property_listings_controller(
    property_id: UUID,
    db: Session = Depends(get_db),
    params: PropertyListingsQuery = Depends(),
):
    """Return listings associated with a property."""
    return get_property_listings(
        db=db,
        property_id=property_id,
        limit=params.limit,
        offset=params.offset,
    )


@router.get("/{property_id}/reviews", response_model=PropertyReviewsResponse)
def get_property_reviews_controller(
    property_id: UUID,
    db: Session = Depends(get_db),
    params: PropertyReviewsQuery = Depends(),
):
    """Return reviews associated with a property."""
    return get_property_reviews(
        db=db,
        property_id=property_id,
        limit=params.limit,
        offset=params.offset,
    )
