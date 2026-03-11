from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.api.v1.properties.models import Property
from app.api.v1.reviews.models import Review
from app.api.v1.reviews.schemas import (
    ReviewCreate,
    ReviewResponse,
    ReviewUpdate,
)


def _get_property_or_404(db: Session, property_id: UUID) -> None:
    exists = (
        db.query(Property)
        .where(Property.id == property_id, Property.deleted_at.is_(None))
        .first()
        is not None
    )
    if not exists:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Property not found"
        )


def _overall_rating_from_categories(
    *,
    management_rating: int,
    cleanliness_rating: int,
    noise_level_rating: int,
    lease_flexibility_rating: int,
) -> int:
    values = [
        management_rating,
        cleanliness_rating,
        noise_level_rating,
        lease_flexibility_rating,
    ]
    return int(round(sum(values) / len(values)))


def create_review(
    db: Session, *, property_id: UUID, user_id: str, data: ReviewCreate
) -> ReviewResponse:
    _get_property_or_404(db, property_id)

    existing = (
        db.query(Review)
        .where(Review.property_id == property_id, Review.user_id == user_id)
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You have already reviewed this property",
        )

    row = Review(
        property_id=property_id,
        user_id=user_id,
        rating=_overall_rating_from_categories(
            management_rating=data.management_rating,
            cleanliness_rating=data.cleanliness_rating,
            noise_level_rating=data.noise_level_rating,
            lease_flexibility_rating=data.lease_flexibility_rating,
        ),
        management_rating=data.management_rating,
        cleanliness_rating=data.cleanliness_rating,
        noise_level_rating=data.noise_level_rating,
        lease_flexibility_rating=data.lease_flexibility_rating,
        comment=data.comment,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return ReviewResponse.model_validate(row)


def get_review_by_id(db: Session, *, review_id: UUID) -> ReviewResponse:
    row = db.get(Review, review_id)
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Review not found"
        )
    return ReviewResponse.model_validate(row)


def update_review(
    db: Session, *, review_id: UUID, user_id: str, data: ReviewUpdate
) -> ReviewResponse:
    row = db.get(Review, review_id)
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Review not found"
        )
    if row.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to update this review",
        )

    update = data.model_dump(exclude_unset=True)
    for k, v in update.items():
        setattr(row, k, v)

    if any(
        key in update
        for key in (
            "management_rating",
            "cleanliness_rating",
            "noise_level_rating",
            "lease_flexibility_rating",
        )
    ):
        row.rating = _overall_rating_from_categories(
            management_rating=row.management_rating,
            cleanliness_rating=row.cleanliness_rating,
            noise_level_rating=row.noise_level_rating,
            lease_flexibility_rating=row.lease_flexibility_rating,
        )

    db.commit()
    db.refresh(row)
    return ReviewResponse.model_validate(row)


def delete_review(db: Session, *, review_id: UUID, user_id: str) -> None:
    row = db.get(Review, review_id)
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Review not found"
        )
    if row.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to delete this review",
        )
    db.delete(row)
    db.commit()
