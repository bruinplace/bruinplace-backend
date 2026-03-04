class S3ObjectNotFoundError(Exception):
    """Raised when a head_object call returns 404."""


class S3Error(Exception):
    """Raised for generic S3/boto3 errors."""
