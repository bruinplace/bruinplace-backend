"""Backfill low-res image variants for existing listing/property images.

Usage:
    uv run python scripts/run_script.py backfill_low_res_images
    uv run python scripts/run_script.py backfill_low_res_images --scope listing
    uv run python scripts/run_script.py backfill_low_res_images --scope property
    uv run python scripts/run_script.py backfill_low_res_images --dry-run
"""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.api.v1.images.exceptions import S3Error, S3ObjectNotFoundError
from app.api.v1.images.image_processing import InvalidImageError, create_low_res_variant
from app.api.v1.images.models import ListingImage, PropertyImage
from app.api.v1.listings.models import Listing  # noqa: F401
from app.api.v1.properties.models import Property  # noqa: F401
from app.api.v1.images.s3_utils import (
    build_low_res_storage_key,
    build_s3_url,
    get_object_bytes,
    upload_object,
)
from app.db.session import SessionLocal, engine


@dataclass
class BackfillStats:
    total: int = 0
    processed: int = 0
    updated: int = 0
    skipped: int = 0
    failed: int = 0


@dataclass
class ImageTaskResult:
    image_id: UUID
    status: str
    low_res_storage_key: str | None = None
    low_res_url: str | None = None
    reason: str | None = None


def _progress_line(scope: str, stats: BackfillStats) -> str:
    pct = (stats.processed / stats.total * 100) if stats.total else 100.0
    return (
        f"[{scope}] {stats.processed}/{stats.total} ({pct:.1f}%) "
        f"updated={stats.updated} skipped={stats.skipped} failed={stats.failed}"
    )


def _commit_updates(
    db: Session,
    *,
    model,
    pending_updates: list[dict[str, object]],
) -> None:
    if not pending_updates:
        return
    db.bulk_update_mappings(model, pending_updates)
    db.commit()
    pending_updates.clear()


def _process_one_image(image_id: UUID, storage_key: str, dry_run: bool) -> ImageTaskResult:
    if not storage_key:
        return ImageTaskResult(
            image_id=image_id,
            status="skipped",
            reason="no-storage-key",
        )

    try:
        original_bytes = get_object_bytes(storage_key)
        low_res_bytes = create_low_res_variant(original_bytes)
        low_res_storage_key = build_low_res_storage_key(storage_key)
        low_res_url = build_s3_url(low_res_storage_key)

        if not dry_run:
            upload_object(
                key=low_res_storage_key,
                body=low_res_bytes,
                content_type="image/jpeg",
            )

        return ImageTaskResult(
            image_id=image_id,
            status="updated",
            low_res_storage_key=low_res_storage_key,
            low_res_url=low_res_url,
        )
    except (S3ObjectNotFoundError, InvalidImageError) as exc:
        return ImageTaskResult(image_id=image_id, status="failed", reason=str(exc))
    except S3Error as exc:
        return ImageTaskResult(image_id=image_id, status="failed", reason=str(exc))
    except Exception as exc:  # noqa: BLE001
        return ImageTaskResult(
            image_id=image_id,
            status="failed",
            reason=f"{type(exc).__name__}: {exc}",
        )


def _backfill_model(
    db: Session,
    *,
    model,
    scope: str,
    dry_run: bool,
    max_items: int | None,
    workers: int,
    db_batch_size: int,
) -> BackfillStats:
    rows_query = (
        db.query(model.id, model.storage_key)
        .where(
            or_(
                model.low_res_storage_key.is_(None),
                model.low_res_url.is_(None),
            )
        )
        .order_by(model.created_at.asc())
    )
    if max_items is not None:
        rows_query = rows_query.limit(max_items)
    rows = rows_query.all()

    stats = BackfillStats(total=len(rows))
    print(
        f"[{scope}] queued {stats.total} images for low-res backfill (workers={workers}, db_batch_size={db_batch_size})",
        flush=True,
    )

    pending_updates: list[dict[str, object]] = []

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [
            executor.submit(
                _process_one_image,
                row.id,
                row.storage_key,
                dry_run,
            )
            for row in rows
        ]

        for future in as_completed(futures):
            result = future.result()
            stats.processed += 1
            row_id = str(result.image_id)

            if result.status == "updated":
                stats.updated += 1
                if not dry_run:
                    pending_updates.append(
                        {
                            "id": result.image_id,
                            "low_res_storage_key": result.low_res_storage_key,
                            "low_res_url": result.low_res_url,
                        }
                    )
                    if len(pending_updates) >= db_batch_size:
                        try:
                            _commit_updates(
                                db,
                                model=model,
                                pending_updates=pending_updates,
                            )
                        except Exception as exc:  # noqa: BLE001
                            db.rollback()
                            stats.failed += len(pending_updates)
                            stats.updated -= len(pending_updates)
                            print(
                                f"{_progress_line(scope, stats)} id={row_id} status=failed reason=db-commit-error: {type(exc).__name__}: {exc}",
                                flush=True,
                            )
                            pending_updates.clear()

                print(
                    f"{_progress_line(scope, stats)} id={row_id} status=updated",
                    flush=True,
                )
                continue

            if result.status == "skipped":
                stats.skipped += 1
                print(
                    f"{_progress_line(scope, stats)} id={row_id} status=skipped-{result.reason}",
                    flush=True,
                )
                continue

            stats.failed += 1
            print(
                f"{_progress_line(scope, stats)} id={row_id} status=failed reason={result.reason}",
                flush=True,
            )

    if not dry_run and pending_updates:
        try:
            _commit_updates(
                db,
                model=model,
                pending_updates=pending_updates,
            )
        except Exception as exc:  # noqa: BLE001
            db.rollback()
            stats.failed += len(pending_updates)
            stats.updated -= len(pending_updates)
            print(
                f"{_progress_line(scope, stats)} status=failed reason=db-final-commit-error: {type(exc).__name__}: {exc}",
                flush=True,
            )
            pending_updates.clear()

    print(f"[{scope}] finished: {_progress_line(scope, stats)}", flush=True)
    return stats


def run(
    scope: str,
    dry_run: bool,
    max_items: int | None,
    workers: int,
    db_batch_size: int,
) -> None:
    # Keep output focused on per-item progress for long-running backfills.
    engine.echo = False
    db = SessionLocal()
    try:
        total_updated = 0
        total_skipped = 0
        total_failed = 0
        total_processed = 0

        if scope in {"all", "property"}:
            property_stats = _backfill_model(
                db,
                model=PropertyImage,
                scope="property_images",
                dry_run=dry_run,
                max_items=max_items,
                workers=workers,
                db_batch_size=db_batch_size,
            )
            total_updated += property_stats.updated
            total_skipped += property_stats.skipped
            total_failed += property_stats.failed
            total_processed += property_stats.processed

        if scope in {"all", "listing"}:
            listing_stats = _backfill_model(
                db,
                model=ListingImage,
                scope="listing_images",
                dry_run=dry_run,
                max_items=max_items,
                workers=workers,
                db_batch_size=db_batch_size,
            )
            total_updated += listing_stats.updated
            total_skipped += listing_stats.skipped
            total_failed += listing_stats.failed
            total_processed += listing_stats.processed

        print(
            "[summary] "
            f"processed={total_processed} updated={total_updated} "
            f"skipped={total_skipped} failed={total_failed} dry_run={dry_run}",
            flush=True,
        )
    finally:
        db.close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Backfill low-res image variants for stored listing/property images."
    )
    parser.add_argument(
        "--scope",
        choices=["all", "property", "listing"],
        default="all",
        help="Which image tables to process.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run conversion and validation without writing to S3 or DB.",
    )
    parser.add_argument(
        "--max-items",
        type=int,
        default=None,
        help="Optional max number of rows per scope to process.",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=8,
        help="Number of worker threads for S3 download/resize/upload.",
    )
    parser.add_argument(
        "--db-batch-size",
        type=int,
        default=100,
        help="How many successful rows to buffer before one DB commit.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    run(
        scope=args.scope,
        dry_run=args.dry_run,
        max_items=args.max_items,
        workers=args.workers,
        db_batch_size=args.db_batch_size,
    )
