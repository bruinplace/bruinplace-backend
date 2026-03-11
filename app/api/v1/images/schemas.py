from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class ImageUploadUrlRequest(BaseModel):
    """Payload for requesting a pre-signed S3 upload URL."""

    filename: str = Field(..., min_length=1, max_length=512)
    content_type: str = Field(..., min_length=1, max_length=255)


class ImageUploadUrlResponse(BaseModel):
    """Pre-signed upload target and metadata needed by the client."""

    image_id: UUID
    storage_key: str
    upload_url: str
    method: str = "PUT"
    required_headers: dict[str, str]
    expires_in_seconds: int


class BulkImageUploadUrlsRequest(BaseModel):
    """Payload for requesting pre-signed upload URLs for many files."""

    files: list[ImageUploadUrlRequest] = Field(..., min_length=1, max_length=20)


class BulkImageUploadUrlsResponse(BaseModel):
    """Batch response for pre-signed upload URLs."""

    items: list[ImageUploadUrlResponse]
    total: int


class ImageFinalizeRequest(BaseModel):
    """Payload for finalizing an uploaded S3 object into an image row."""

    image_id: UUID
    storage_key: str = Field(..., min_length=1)
    display_order: Optional[int] = Field(None, ge=0)


class BulkImageFinalizeRequest(BaseModel):
    """Payload for finalizing multiple uploaded objects."""

    items: list[ImageFinalizeRequest] = Field(..., min_length=1, max_length=20)


class ImageResponse(BaseModel):
    """Image metadata returned by image APIs."""

    id: UUID
    storage_key: str
    url: str
    display_order: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ImageListResponse(BaseModel):
    """Paginated-like list response for images."""

    items: list[ImageResponse]
    total: int
