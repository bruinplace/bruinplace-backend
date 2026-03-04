from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.api.v1.images.schemas import (
    BulkImageFinalizeRequest,
    BulkImageUploadUrlsRequest,
    BulkImageUploadUrlsResponse,
    ImageFinalizeRequest,
    ImageListResponse,
    ImageResponse,
    ImageUploadUrlRequest,
    ImageUploadUrlResponse,
)
from app.api.v1.images.services import (
    create_listing_upload_url,
    create_listing_upload_urls,
    create_property_upload_url,
    create_property_upload_urls,
    delete_listing_image,
    delete_property_image,
    finalize_listing_image,
    finalize_listing_images,
    finalize_property_image,
    finalize_property_images,
    get_listing_images,
    get_property_images,
)

router = APIRouter()


# --------- Property Images ---------
@router.get("/properties/{property_id}/images", response_model=ImageListResponse)
def get_property_images_controller(
    property_id: UUID,
    db: Session = Depends(get_db),
):
    """Return all images attached to a property ordered by display order."""
    return get_property_images(db=db, property_id=property_id)


@router.post(
    "/properties/{property_id}/images/upload-url",
    response_model=ImageUploadUrlResponse,
)
def post_property_upload_url_controller(
    property_id: UUID,
    payload: ImageUploadUrlRequest,
    db: Session = Depends(get_db),
):
    """Generate a pre-signed S3 upload URL for a property image."""
    return create_property_upload_url(db=db, property_id=property_id, payload=payload)


@router.post(
    "/properties/{property_id}/images/upload-urls",
    response_model=BulkImageUploadUrlsResponse,
)
def post_property_upload_urls_controller(
    property_id: UUID,
    payload: BulkImageUploadUrlsRequest,
    db: Session = Depends(get_db),
):
    """Generate pre-signed S3 upload URLs for many property images."""
    return create_property_upload_urls(db=db, property_id=property_id, payload=payload)


@router.post(
    "/properties/{property_id}/images",
    response_model=ImageResponse,
    status_code=status.HTTP_201_CREATED,
)
def post_property_image_controller(
    property_id: UUID,
    payload: ImageFinalizeRequest,
    db: Session = Depends(get_db),
):
    """Finalize an uploaded property image and persist its metadata."""
    return finalize_property_image(db=db, property_id=property_id, payload=payload)


@router.post(
    "/properties/{property_id}/images/batch",
    response_model=ImageListResponse,
    status_code=status.HTTP_201_CREATED,
)
def post_property_images_batch_controller(
    property_id: UUID,
    payload: BulkImageFinalizeRequest,
    db: Session = Depends(get_db),
):
    """Finalize many uploaded property images and persist their metadata."""
    return finalize_property_images(db=db, property_id=property_id, payload=payload)


@router.delete(
    "/properties/{property_id}/images/{image_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_property_image_controller(
    property_id: UUID,
    image_id: UUID,
    db: Session = Depends(get_db),
):
    """Delete a property image from both S3 and the database."""
    delete_property_image(db=db, property_id=property_id, image_id=image_id)


# --------- Listing Images ---------
@router.get("/listings/{listing_id}/images", response_model=ImageListResponse)
def get_listing_images_controller(
    listing_id: UUID,
    db: Session = Depends(get_db),
):
    """Return all images attached to a listing ordered by display order."""
    return get_listing_images(db=db, listing_id=listing_id)


@router.post(
    "/listings/{listing_id}/images/upload-url",
    response_model=ImageUploadUrlResponse,
)
def post_listing_upload_url_controller(
    listing_id: UUID,
    payload: ImageUploadUrlRequest,
    db: Session = Depends(get_db),
):
    """Generate a pre-signed S3 upload URL for a listing image."""
    return create_listing_upload_url(db=db, listing_id=listing_id, payload=payload)


@router.post(
    "/listings/{listing_id}/images/upload-urls",
    response_model=BulkImageUploadUrlsResponse,
)
def post_listing_upload_urls_controller(
    listing_id: UUID,
    payload: BulkImageUploadUrlsRequest,
    db: Session = Depends(get_db),
):
    """Generate pre-signed S3 upload URLs for many listing images."""
    return create_listing_upload_urls(db=db, listing_id=listing_id, payload=payload)


@router.post(
    "/listings/{listing_id}/images",
    response_model=ImageResponse,
    status_code=status.HTTP_201_CREATED,
)
def post_listing_image_controller(
    listing_id: UUID,
    payload: ImageFinalizeRequest,
    db: Session = Depends(get_db),
):
    """Finalize an uploaded listing image and persist its metadata."""
    return finalize_listing_image(db=db, listing_id=listing_id, payload=payload)


@router.post(
    "/listings/{listing_id}/images/batch",
    response_model=ImageListResponse,
    status_code=status.HTTP_201_CREATED,
)
def post_listing_images_batch_controller(
    listing_id: UUID,
    payload: BulkImageFinalizeRequest,
    db: Session = Depends(get_db),
):
    """Finalize many uploaded listing images and persist their metadata."""
    return finalize_listing_images(db=db, listing_id=listing_id, payload=payload)


@router.delete(
    "/listings/{listing_id}/images/{image_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_listing_image_controller(
    listing_id: UUID,
    image_id: UUID,
    db: Session = Depends(get_db),
):
    """Delete a listing image from both S3 and the database."""
    delete_listing_image(db=db, listing_id=listing_id, image_id=image_id)
