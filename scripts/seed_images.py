"""Seed property images from UniShack JSON image URLs into S3 + database.

Usage:
    uv run python scripts/run_script.py seed_images <path-to-unishack_photos.json>

The script reads .env via the app's config, so no extra DB setup is needed.
Requires S3_BUCKET_NAME and AWS credentials to be set in .env.
"""

import json
import sys
from urllib.request import Request, urlopen

from app.api.v1.images.models import PropertyImage
from app.api.v1.images.s3_utils import (
    build_s3_url,
    generate_property_image_id_and_key,
    upload_object,
)
from app.api.v1.properties.models import Property
from app.db.session import SessionLocal
from scripts.script_user import SCRIPT_USER_ID, ensure_script_user


def seed_images(json_path: str) -> None:
    with open(json_path, encoding="utf-8") as f:
        apartments = json.load(f)

    db = SessionLocal()
    try:
        ensure_script_user(db)

        # Build name -> Property lookup (scoped to script user to avoid duplicates)
        all_properties = (
            db.query(Property)
            .filter(Property.deleted_at.is_(None), Property.owner_id == SCRIPT_USER_ID)
            .all()
        )
        property_by_name = {p.name: p for p in all_properties}

        success = 0
        skipped = 0
        failed = 0

        for apt in apartments:
            name = apt.get("name", "<unknown>")
            image_urls = apt.get("image_urls", [])

            if not image_urls:
                print(f"  SKIP (no URLs): {name}")
                skipped += 1
                continue

            prop = property_by_name.get(name)
            if prop is None:
                print(f"  SKIP (no property in DB): {name}")
                skipped += 1
                continue

            # Skip if any image already exists for this property (idempotency)
            existing = (
                db.query(PropertyImage)
                .filter(PropertyImage.property_id == prop.id)
                .first()
            )
            if existing:
                print(f"  SKIP (already seeded): {name}")
                skipped += 1
                continue

            for display_order, image_url in enumerate(image_urls):
                try:
                    # Download the image
                    req = Request(image_url)
                    resp = urlopen(req, timeout=30)  # noqa: S310
                    image_bytes = resp.read()
                    content_type = resp.headers.get("Content-Type", "image/webp")

                    # Derive filename from URL for extension detection
                    filename = image_url.rsplit("/", 1)[-1]

                    # Generate image ID and S3 key
                    image_id, storage_key = generate_property_image_id_and_key(
                        property_id=prop.id,
                        filename=filename,
                        content_type=content_type,
                    )

                    # Upload to S3
                    upload_object(key=storage_key, body=image_bytes, content_type=content_type)

                    # Create DB record
                    db_image = PropertyImage(
                        id=image_id,
                        property_id=prop.id,
                        storage_key=storage_key,
                        url=build_s3_url(storage_key),
                        display_order=display_order,
                    )
                    db.add(db_image)
                    db.flush()

                    success += 1
                    print(f"  OK: {name} [{display_order}] -> {storage_key}")

                except Exception as exc:
                    print(f"  FAIL: {name} [{display_order}] -- {exc}")
                    failed += 1

        db.commit()
        print(f"\nDone. Success={success}, Skipped={skipped}, Failed={failed}")

    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(
            "Usage: uv run python scripts/run_script.py seed_images <path-to-unishack_photos.json>"
        )
        sys.exit(1)
    seed_images(sys.argv[1])
