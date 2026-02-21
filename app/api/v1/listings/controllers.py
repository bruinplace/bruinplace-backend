from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.api.v1.users.models import User
from app.api.v1.listings.schemas import (
    AmenityResponse,
    ListingCreate,
    ListingFilterQuery,
    ListingListResponse,
    ListingResponse,
    ListingUpdate,
)
from app.api.v1.listings.services import (
    create_listing,
    get_listing_by_id,
    get_listings,
    list_amenities,
    soft_delete_listing,
    update_listing,
)

router = APIRouter()


@router.get("", response_model=ListingListResponse)
def get_listings_controller(
    db: Session = Depends(get_db),
    params: ListingFilterQuery = Depends(),
):
    """
    Search and filter listings.

    Returns a paginated list of listings (excluding soft-deleted) with optional
    filters for status, unit type, rent range, property, text search, and
    availability date.
    """
    return get_listings(db, **params.model_dump())


@router.get("/amenities", response_model=list[AmenityResponse])
def get_amenities_controller(db: Session = Depends(get_db)):
    """
    Return all amenities.

    Used by clients to show amenity options when creating or editing a listing.
    """
    return list_amenities(db)


@router.post("", response_model=ListingResponse, status_code=status.HTTP_201_CREATED)
def post_listing_controller(
    payload: ListingCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Create a new listing owned by the authenticated user.

    Requires authentication. The listing is tied to the given property_id;
    returns 404 if the property does not exist.
    """
    return create_listing(db, user.id, payload)


@router.get("/{listing_id}", response_model=ListingResponse)
def get_listing_controller(
    listing_id: UUID,
    db: Session = Depends(get_db),
):
    """
    Return full listing details by ID.

    Returns 404 if the listing does not exist or has been soft-deleted.
    """
    listing = get_listing_by_id(db, listing_id)
    if not listing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Listing not found",
        )
    return listing


@router.patch("/{listing_id}", response_model=ListingResponse)
def patch_listing_controller(
    listing_id: UUID,
    payload: ListingUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Update a listing (owner only).

    Partial update: only provided fields are changed. Returns 404 if the listing
    does not exist, is soft-deleted, or the authenticated user is not the owner.
    """
    listing = update_listing(db, listing_id, user.id, payload)
    if not listing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Listing not found or you are not the owner",
        )
    return listing


@router.delete("/{listing_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_listing_controller(
    listing_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Soft-delete a listing (owner only).

    Sets deleted_at so the listing is excluded from list/detail. Returns 404 if
    the listing does not exist, is already soft-deleted, or the user is not owner.
    """
    deleted = soft_delete_listing(db, listing_id, user.id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Listing not found or you are not the owner",
        )
