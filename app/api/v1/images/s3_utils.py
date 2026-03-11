"""
S3 utility functions with no FastAPI dependency.
"""

import mimetypes
import uuid
from uuid import UUID

from app.api.v1.images.exceptions import S3Error, S3ObjectNotFoundError

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from app.core.config import settings

s3_client = boto3.client(
    "s3",
    region_name=settings.AWS_REGION,
    aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
    aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
    endpoint_url=f"https://s3.{settings.AWS_REGION}.amazonaws.com",
)

S3_BUCKET = settings.S3_BUCKET_NAME


# ---------------------------------------------------------------------------
# Key / URL helpers
# ---------------------------------------------------------------------------
def extension_from_filename_or_content_type(filename: str, content_type: str) -> str:
    """Infer file extension from filename first, then MIME type."""
    ext = filename.rsplit(".", 1)[-1].strip().lower() if "." in filename else ""
    if ext:
        return ext
    guessed = mimetypes.guess_extension(content_type) or ""
    guessed = guessed.lstrip(".")
    return guessed or "bin"


def property_images_prefix(property_id: UUID) -> str:
    """Return the S3 key prefix for all images under a property."""
    return f"properties/{property_id}/images/"


def listing_images_prefix(property_id: UUID, listing_id: UUID) -> str:
    """Return the S3 key prefix for all images under a listing."""
    return f"properties/{property_id}/listings/{listing_id}/images/"


def build_storage_key_for_property(
    property_id: UUID,
    image_id: UUID,
    ext: str,
) -> str:
    """Build canonical S3 key for a property image."""
    return f"{property_images_prefix(property_id)}{image_id}.{ext}"


def build_storage_key_for_listing(
    property_id: UUID,
    listing_id: UUID,
    image_id: UUID,
    ext: str,
) -> str:
    """Build canonical S3 key for a listing image."""
    return f"{listing_images_prefix(property_id, listing_id)}{image_id}.{ext}"


def build_s3_url(storage_key: str) -> str:
    """Construct the public S3 URL for a storage key."""
    return f"https://{S3_BUCKET}.s3.{settings.AWS_REGION}.amazonaws.com/{storage_key}"


def generate_property_image_id_and_key(
    property_id: UUID,
    filename: str,
    content_type: str,
) -> tuple[UUID, str]:
    """Generate a fresh image_id and storage_key for a property image."""
    image_id = uuid.uuid4()
    ext = extension_from_filename_or_content_type(filename, content_type)
    key = build_storage_key_for_property(property_id, image_id, ext)
    return image_id, key


def generate_listing_image_id_and_key(
    property_id: UUID,
    listing_id: UUID,
    filename: str,
    content_type: str,
) -> tuple[UUID, str]:
    """Generate a fresh image_id and storage_key for a listing image."""
    image_id = uuid.uuid4()
    ext = extension_from_filename_or_content_type(filename, content_type)
    key = build_storage_key_for_listing(property_id, listing_id, image_id, ext)
    return image_id, key


# ---------------------------------------------------------------------------
# S3 operations — raise plain exceptions
# ---------------------------------------------------------------------------
def upload_object(key: str, body: bytes, content_type: str) -> None:
    """Upload raw bytes to S3."""
    try:
        s3_client.put_object(
            Bucket=S3_BUCKET,
            Key=key,
            Body=body,
            ContentType=content_type,
        )
    except (ClientError, BotoCoreError) as exc:
        raise S3Error(f"Failed to upload object {key!r}") from exc


def object_exists(key: str) -> bool:
    """Return True if the object exists in S3, False if not found."""
    try:
        s3_client.head_object(Bucket=S3_BUCKET, Key=key)
        return True
    except ClientError as exc:
        code = exc.response.get("Error", {}).get("Code", "")
        if code in {"404", "NoSuchKey", "NotFound"}:
            return False
        raise S3Error(f"Storage error checking {key!r}") from exc
    except BotoCoreError as exc:
        raise S3Error("Storage provider is unavailable") from exc


def assert_object_exists(key: str) -> None:
    """Raise S3ObjectNotFoundError when the object is not in S3."""
    if not object_exists(key):
        raise S3ObjectNotFoundError(f"Object not found in storage: {key!r}")


def delete_object(key: str) -> None:
    """Delete an object from S3."""
    try:
        s3_client.delete_object(Bucket=S3_BUCKET, Key=key)
    except (ClientError, BotoCoreError) as exc:
        raise S3Error(f"Failed to delete object {key!r}") from exc


def generate_presigned_put_url(key: str, content_type: str) -> str:
    """Generate a pre-signed S3 PUT URL for direct client uploads."""
    try:
        return s3_client.generate_presigned_url(
            ClientMethod="put_object",
            Params={"Bucket": S3_BUCKET, "Key": key, "ContentType": content_type},
            ExpiresIn=settings.S3_PRESIGNED_URL_EXPIRES_SECONDS,
        )
    except (ClientError, BotoCoreError) as exc:
        raise S3Error(f"Failed to generate presigned URL for {key!r}") from exc
