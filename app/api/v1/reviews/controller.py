from uuid import UUID

from fastapi import APIRouter, Depends, status
from app.api.v1.reviews.schemas import ReviewCreate, ReviewResponse, ReviewUpdate
from app.api.v1.reviews.services import (
    create_review,
    delete_review,
    get_review_by_id,
    update_review,
)
from app.api.deps import get_current_user, get_db
from sqlalchemy.orm import Session

router = APIRouter()


@router.post(
    "/properties/{property_id}/reviews",
    response_model=ReviewResponse,
    status_code=status.HTTP_201_CREATED,
)
def post_property_review(
    property_id: UUID,
    payload: ReviewCreate,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    return create_review(db, property_id=property_id, user_id=user.id, data=payload)


@router.get("/reviews/{review_id}", response_model=ReviewResponse)
def get_review(review_id: UUID, db: Session = Depends(get_db)):
    return get_review_by_id(db, review_id=review_id)


@router.patch("/reviews/{review_id}", response_model=ReviewResponse)
def patch_review(
    review_id: UUID,
    payload: ReviewUpdate,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    return update_review(db, review_id=review_id, user_id=user.id, data=payload)


@router.delete("/reviews/{review_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_review_controller(
    review_id: UUID,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    delete_review(db, review_id=review_id, user_id=user.id)
