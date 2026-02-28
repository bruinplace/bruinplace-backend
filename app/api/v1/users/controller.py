from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.api.deps import get_current_user
from app.api.v1.listings.services import (
    get_saved_listings,
    save_listing_for_user,
    unsave_listing_for_user,
)
from app.api.v1.listings.schemas import ListingListResponse
from .models import User
from .schemas import SavedListingsQuery, UserResponse, UserUpdate
from sqlalchemy.orm import Session
from app.api.deps import get_db

router = APIRouter()

@router.get("", response_model=UserResponse)
def get_me(user: User = Depends(get_current_user)) -> UserResponse:
    return user


@router.patch("", response_model=UserResponse)
def patch_me(
    payload: UserUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UserResponse:
    """Update editable fields on the current user's profile."""
    current = db.get(User, user.id)
    if current is None:
        # Should not happen if get_current_user succeeded, but handle gracefully
        return user
    update = payload.model_dump(exclude_unset=True)
    for k, v in update.items():
        setattr(current, k, v)
    db.commit()
    db.refresh(current)
    return current


@router.get("/saved-listings", response_model=ListingListResponse)
def get_my_saved_listings(
    params: SavedListingsQuery = Depends(),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return get_saved_listings(
        db=db, user_id=user.id, limit=params.limit, offset=params.offset
    )


@router.post("/saved-listings/{listing_id}", status_code=status.HTTP_204_NO_CONTENT)
def save_listing(
    listing_id: UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # Idempotent: creating an existing saved listing still returns 204
    save_listing_for_user(db=db, user_id=user.id, listing_id=listing_id)


@router.delete("/saved-listings/{listing_id}", status_code=status.HTTP_204_NO_CONTENT)
def unsave_listing(
    listing_id: UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # Idempotent delete
    unsave_listing_for_user(db=db, user_id=user.id, listing_id=listing_id)
