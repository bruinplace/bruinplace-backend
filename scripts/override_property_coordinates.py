"""Override property coordinates using manually reviewed values from a CSV file.

Usage:
    uv run python scripts/run_script.py override_property_coordinates

Reads scripts/geocode_properties.csv, looks up each row by property_id, and
updates latitude/longitude only when manual_lat and manual_long are provided.
Rows missing those fields or whose property_id does not exist in the DB are skipped.
"""

import csv
from pathlib import Path

from app.api.v1.properties.models import Property
from app.api.v1.users.models import User  # noqa: F401 — registers 'users' table in SQLAlchemy metadata
from app.db.session import SessionLocal

CSV_PATH = Path(__file__).resolve().parent / "geocode_properties.csv"


def run() -> None:
    print(f"Reading CSV: {CSV_PATH}")

    with open(CSV_PATH, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    print(f"Total rows in CSV: {len(rows)}")

    db = SessionLocal()
    try:
        updated = 0
        skipped_no_coords = 0
        skipped_not_found = 0

        for row in rows:
            property_id = row.get("property_id", "").strip()
            manual_lat = row.get("manual_lat", "").strip()
            manual_long = row.get("manual_long", "").strip()

            if not manual_lat or not manual_long:
                print(
                    f"  SKIP (no manual coords) property_id={property_id!r} name={row.get('name', '')!r}"
                )
                skipped_no_coords += 1
                continue

            try:
                lat = float(manual_lat)
                lng = float(manual_long)
            except ValueError:
                print(
                    f"  SKIP (invalid coord values) property_id={property_id!r} manual_lat={manual_lat!r} manual_long={manual_long!r}"
                )
                skipped_no_coords += 1
                continue

            prop = db.query(Property).filter(Property.id == property_id).first()
            if prop is None:
                print(
                    f"  SKIP (not in DB)           property_id={property_id!r} name={row.get('name', '')!r}"
                )
                skipped_not_found += 1
                continue

            old_lat, old_lng = prop.latitude, prop.longitude
            prop.latitude = lat
            prop.longitude = lng
            print(
                f"  UPDATE property_id={property_id!r} name={prop.name!r} "
                f"({old_lat}, {old_lng}) -> ({lat}, {lng})"
            )
            updated += 1

        db.commit()
        print(
            f"\nDone. updated={updated}, "
            f"skipped_no_coords={skipped_no_coords}, "
            f"skipped_not_found={skipped_not_found}"
        )
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    run()
