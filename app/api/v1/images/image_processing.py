"""Image transformation helpers."""

from io import BytesIO

from PIL import Image, ImageOps, UnidentifiedImageError


DEFAULT_LOW_RES_MAX_DIMENSION = 640
DEFAULT_LOW_RES_QUALITY = 72


class InvalidImageError(ValueError):
    """Raised when provided bytes are not a valid image."""


def create_low_res_variant(
    source_bytes: bytes,
    *,
    max_dimension: int = DEFAULT_LOW_RES_MAX_DIMENSION,
    quality: int = DEFAULT_LOW_RES_QUALITY,
) -> bytes:
    """
    Build a compressed low-res JPEG variant while preserving orientation.
    """
    if not source_bytes:
        raise InvalidImageError("Image file is empty.")

    try:
        with Image.open(BytesIO(source_bytes)) as raw_image:
            image = ImageOps.exif_transpose(raw_image)
            if image.mode != "RGB":
                image = image.convert("RGB")

            image.thumbnail((max_dimension, max_dimension), Image.Resampling.LANCZOS)

            output = BytesIO()
            image.save(
                output,
                format="JPEG",
                quality=quality,
                optimize=True,
                progressive=True,
            )
            return output.getvalue()
    except UnidentifiedImageError as exc:
        raise InvalidImageError("Unsupported image file format.") from exc
