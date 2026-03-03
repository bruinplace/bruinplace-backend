import mimetypes
import uuid
from uuid import UUID

import boto3
from botocore.exceptions import BotoCoreError, ClientError
from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.v1.images.models import ListingImage, PropertyImage
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
from app.api.v1.listings.models import Listing
from app.api.v1.properties.models import Property
from app.core.config import settings


s3_client = boto3.client(
    "s3",
    region_name=settings.AWS_REGION,
    aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
    aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
    endpoint_url=f"https://s3.{settings.AWS_REGION}.amazonaws.com",
)


def _validate_s3_settings() -> None:
    """Ensure required S3 settings are present before storage operations."""
    if not settings.S3_BUCKET_NAME:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="S3 bucket is not configured",
        )


def _require_property(db: Session, property_id: UUID) -> Property:
    """Load a property or raise 404 when it does not exist."""
    property_row = db.get(Property, property_id)
    if not property_row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Property not found",
        )
    return property_row


def _require_listing(db: Session, listing_id: UUID) -> Listing:
    """Load a non-deleted listing or raise 404."""
    listing = db.get(Listing, listing_id)
    if not listing or listing.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Listing not found",
        )
    return listing


def _extension_from_filename_or_content_type(filename: str, content_type: str) -> str:
    """Infer file extension from filename first, then MIME type."""
    ext = filename.rsplit(".", 1)[-1].strip().lower() if "." in filename else ""
    if ext:
        return ext
    guessed = mimetypes.guess_extension(content_type) or ""
    guessed = guessed.lstrip(".")
    return guessed or "bin"


def _public_url_for_key(storage_key: str) -> str:
    """Build a public/read URL for a storage key."""
    return (
        f"https://{settings.S3_BUCKET_NAME}.s3."
        f"{settings.AWS_REGION}.amazonaws.com/{storage_key}"
    )


def _next_display_order(
    db: Session, image_model, parent_column, parent_id: UUID
) -> int:
    """Return next display_order value scoped to parent resource."""
    max_order = (
        db.query(func.max(image_model.display_order))
        .where(parent_column == parent_id)
        .scalar()
    )
    return (max_order or -1) + 1


def _list_images(
    db: Session, image_model, parent_column, parent_id: UUID
) -> ImageListResponse:
    """List images for a parent entity in stable display order."""
    rows = (
        db.query(image_model)
        .where(parent_column == parent_id)
        .order_by(image_model.display_order.asc(), image_model.created_at.asc())
        .all()
    )
    items = [ImageResponse.model_validate(row) for row in rows]
    return ImageListResponse(items=items, total=len(items))


def _build_upload_url_response(
    payload: ImageUploadUrlRequest,
    storage_key: str,
) -> ImageUploadUrlResponse:
    """Create image_id/storage_key pair and return upload URL payload."""
    image_id = uuid.uuid4()
    extension = _extension_from_filename_or_content_type(
        filename=payload.filename,
        content_type=payload.content_type,
    )
    storage_key = f"{storage_key}{image_id}.{extension}"
    try:
        upload_url = s3_client.generate_presigned_url(
            ClientMethod="put_object",
            Params={
                "Bucket": settings.S3_BUCKET_NAME,
                "Key": storage_key,
                "ContentType": payload.content_type,
            },
            ExpiresIn=settings.S3_PRESIGNED_URL_EXPIRES_SECONDS,
        )
    except (ClientError, BotoCoreError) as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to generate upload URL",
        ) from exc

    return ImageUploadUrlResponse(
        image_id=image_id,
        storage_key=storage_key,
        upload_url=upload_url,
        required_headers={"Content-Type": payload.content_type},
        expires_in_seconds=settings.S3_PRESIGNED_URL_EXPIRES_SECONDS,
    )


def _assert_s3_object_exists(storage_key: str) -> None:
    """Validate that an uploaded object exists in S3."""
    _validate_s3_settings()
    try:
        s3_client.head_object(Bucket=settings.S3_BUCKET_NAME, Key=storage_key)
    except ClientError as exc:
        code = exc.response.get("Error", {}).get("Code", "")
        if code in {"404", "NoSuchKey", "NotFound"}:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Uploaded object was not found in storage",
            ) from exc
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Storage provider error while validating upload",
        ) from exc
    except BotoCoreError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Storage provider is unavailable",
        ) from exc


def _delete_s3_object(storage_key: str) -> None:
    """Delete an object from S3 by storage key."""
    _validate_s3_settings()
    try:
        s3_client.delete_object(Bucket=settings.S3_BUCKET_NAME, Key=storage_key)
    except (ClientError, BotoCoreError) as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to delete object from storage",
        ) from exc


def _get_or_validate_existing_image(
    db: Session,
    image_model,
    image_id: UUID,
    parent_column,
    parent_id: UUID,
    conflict_detail: str,
):
    """Load existing image by id and ensure it belongs to expected parent."""
    existing = db.get(image_model, image_id)
    if not existing:
        return None
    if getattr(existing, parent_column.key) != parent_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=conflict_detail,
        )
    return existing


def _save_new_image(db: Session, image_model, **kwargs) -> ImageResponse:
    """Persist a new image row and return serialized response."""
    image = image_model(**kwargs)
    db.add(image)
    db.commit()
    db.refresh(image)
    return ImageResponse.model_validate(image)


def _ensure_unique_batch_ids(payload: BulkImageFinalizeRequest) -> None:
    """Reject batch finalize payloads containing duplicate image IDs."""
    image_ids = [item.image_id for item in payload.items]
    if len(set(image_ids)) != len(image_ids):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Duplicate image_id values in batch payload",
        )


def _delete_image_row(
    db: Session,
    image_model,
    parent_column,
    parent_id: UUID,
    image_id: UUID,
    not_found_detail: str,
) -> None:
    """Delete image DB row and backing S3 object for a parent resource."""
    image = (
        db.query(image_model)
        .where(image_model.id == image_id, parent_column == parent_id)
        .first()
    )
    if not image:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=not_found_detail,
        )
    _delete_s3_object(image.storage_key)
    db.delete(image)
    db.commit()


def get_property_images(db: Session, property_id: UUID) -> ImageListResponse:
    """Return all images attached to a property."""
    _require_property(db, property_id)
    return _list_images(
        db=db,
        image_model=PropertyImage,
        parent_column=PropertyImage.property_id,
        parent_id=property_id,
    )


def get_listing_images(db: Session, listing_id: UUID) -> ImageListResponse:
    """Return all images attached to a listing."""
    _require_listing(db, listing_id)
    return _list_images(
        db=db,
        image_model=ListingImage,
        parent_column=ListingImage.listing_id,
        parent_id=listing_id,
    )


def create_property_upload_url(
    db: Session, property_id: UUID, payload: ImageUploadUrlRequest
) -> ImageUploadUrlResponse:
    """Generate one pre-signed upload URL for a property image."""
    _validate_s3_settings()
    _require_property(db, property_id)
    return _build_upload_url_response(
        payload=payload,
        storage_key=f"properties/{property_id}/images/",
    )


def create_property_upload_urls(
    db: Session, property_id: UUID, payload: BulkImageUploadUrlsRequest
) -> BulkImageUploadUrlsResponse:
    """Generate pre-signed upload URLs for multiple property images."""
    items = [
        create_property_upload_url(db=db, property_id=property_id, payload=file_payload)
        for file_payload in payload.files
    ]
    return BulkImageUploadUrlsResponse(items=items, total=len(items))


def create_listing_upload_url(
    db: Session, listing_id: UUID, payload: ImageUploadUrlRequest
) -> ImageUploadUrlResponse:
    """Generate one pre-signed upload URL for a listing image."""
    _validate_s3_settings()
    listing = _require_listing(db, listing_id)
    return _build_upload_url_response(
        payload=payload,
        storage_key=(f"properties/{listing.property_id}/listings/{listing_id}/images/"),
    )


def create_listing_upload_urls(
    db: Session, listing_id: UUID, payload: BulkImageUploadUrlsRequest
) -> BulkImageUploadUrlsResponse:
    """Generate pre-signed upload URLs for multiple listing images."""
    items = [
        create_listing_upload_url(db=db, listing_id=listing_id, payload=file_payload)
        for file_payload in payload.files
    ]
    return BulkImageUploadUrlsResponse(items=items, total=len(items))


def finalize_property_image(
    db: Session, property_id: UUID, payload: ImageFinalizeRequest
) -> ImageResponse:
    """Finalize one uploaded property image and persist metadata."""
    _require_property(db, property_id)

    expected_prefix = f"properties/{property_id}/images/"
    if not payload.storage_key.startswith(expected_prefix):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="storage_key does not match property path",
        )

    _assert_s3_object_exists(payload.storage_key)

    existing = _get_or_validate_existing_image(
        db=db,
        image_model=PropertyImage,
        image_id=payload.image_id,
        parent_column=PropertyImage.property_id,
        parent_id=property_id,
        conflict_detail="Image ID already exists for another property",
    )
    if existing:
        return ImageResponse.model_validate(existing)

    return _save_new_image(
        db=db,
        image_model=PropertyImage,
        id=payload.image_id,
        property_id=property_id,
        storage_key=payload.storage_key,
        url=_public_url_for_key(payload.storage_key),
        display_order=payload.display_order
        if payload.display_order is not None
        else _next_display_order(
            db=db,
            image_model=PropertyImage,
            parent_column=PropertyImage.property_id,
            parent_id=property_id,
        ),
    )


def finalize_property_images(
    db: Session, property_id: UUID, payload: BulkImageFinalizeRequest
) -> ImageListResponse:
    """Finalize multiple uploaded property images."""
    _ensure_unique_batch_ids(payload)
    items = [
        finalize_property_image(db=db, property_id=property_id, payload=item)
        for item in payload.items
    ]
    return ImageListResponse(items=items, total=len(items))


def finalize_listing_image(
    db: Session, listing_id: UUID, payload: ImageFinalizeRequest
) -> ImageResponse:
    """Finalize one uploaded listing image and persist metadata."""
    listing = _require_listing(db, listing_id)

    expected_prefix = f"properties/{listing.property_id}/listings/{listing_id}/images/"
    if not payload.storage_key.startswith(expected_prefix):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="storage_key does not match listing path",
        )

    _assert_s3_object_exists(payload.storage_key)

    existing = _get_or_validate_existing_image(
        db=db,
        image_model=ListingImage,
        image_id=payload.image_id,
        parent_column=ListingImage.listing_id,
        parent_id=listing_id,
        conflict_detail="Image ID already exists for another listing",
    )
    if existing:
        return ImageResponse.model_validate(existing)

    return _save_new_image(
        db=db,
        image_model=ListingImage,
        id=payload.image_id,
        listing_id=listing_id,
        property_id=listing.property_id,
        storage_key=payload.storage_key,
        url=_public_url_for_key(payload.storage_key),
        display_order=payload.display_order
        if payload.display_order is not None
        else _next_display_order(
            db=db,
            image_model=ListingImage,
            parent_column=ListingImage.listing_id,
            parent_id=listing_id,
        ),
    )


def finalize_listing_images(
    db: Session, listing_id: UUID, payload: BulkImageFinalizeRequest
) -> ImageListResponse:
    """Finalize multiple uploaded listing images."""
    _ensure_unique_batch_ids(payload)
    items = [
        finalize_listing_image(db=db, listing_id=listing_id, payload=item)
        for item in payload.items
    ]
    return ImageListResponse(items=items, total=len(items))


def delete_property_image(db: Session, property_id: UUID, image_id: UUID) -> None:
    """Delete one property image from storage and database."""
    _delete_image_row(
        db=db,
        image_model=PropertyImage,
        parent_column=PropertyImage.property_id,
        parent_id=property_id,
        image_id=image_id,
        not_found_detail="Property image not found",
    )


def delete_listing_image(db: Session, listing_id: UUID, image_id: UUID) -> None:
    """Delete one listing image from storage and database."""
    _delete_image_row(
        db=db,
        image_model=ListingImage,
        parent_column=ListingImage.listing_id,
        parent_id=listing_id,
        image_id=image_id,
        not_found_detail="Listing image not found",
    )
