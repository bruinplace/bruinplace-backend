"""Seed the database with apartment data from a UniShack JSON export.

Usage:
    uv run python scripts/run_script.py seed_unishack <path-to-unishack.json>

The script reads .env via the app's config, so no extra DB setup is needed.
"""

import json
import re
import sys

from app.api.v1.listings.models import Listing, ListingStatus, UnitType
from app.api.v1.properties.models import Property
from app.db.session import SessionLocal
from scripts.script_user import SCRIPT_USER_ID, ensure_script_user

# UCLA campus coordinates — used as default since the JSON lacks lat/lng
DEFAULT_LATITUDE = 34.0689
DEFAULT_LONGITUDE = -118.4452

UNIT_TYPE_MAP: dict[str, UnitType] = {
    "double": UnitType.SHARED_ROOM,
    "triple": UnitType.SHARED_ROOM,
    "private room": UnitType.PRIVATE_ROOM,
    "studio": UnitType.STUDIO,
}


def parse_price(raw: str) -> int:
    """Extract integer dollar amount from strings like '$ 1050 +/mo' or '$600 deposit'."""
    digits = re.sub(r"[^\d]", "", raw)
    return int(digits) if digits else 0


def parse_int(raw: str) -> int | None:
    """Extract the first integer from a string like '3 Month Lease' or 'up to 3 residents'."""
    match = re.search(r"\d+", raw)
    return int(match.group()) if match else None


def map_unit_type(raw: str) -> UnitType:
    return UNIT_TYPE_MAP.get(raw.strip().lower(), UnitType.OTHER)


def map_status(availability: str) -> ListingStatus:
    if "available" in availability.strip().lower():
        return ListingStatus.ACTIVE
    return ListingStatus.ARCHIVED


def seed(json_path: str) -> None:
    with open(json_path, encoding="utf-8") as f:
        apartments = json.load(f)

    db = SessionLocal()
    try:
        ensure_script_user(db)

        property_count = 0
        listing_count = 0

        for apt in apartments:
            prop = Property(
                owner_id=SCRIPT_USER_ID,
                name=apt["name"],
                address=apt.get("address") or apt["name"],
                postal_code=apt.get("postal_code") or "90024",
                city=apt.get("city") or "Los Angeles",
                state=apt.get("state") or "CA",
                country=apt.get("country") or "US",
                latitude=DEFAULT_LATITUDE,
                longitude=DEFAULT_LONGITUDE,
            )
            db.add(prop)
            db.flush()  # assigns prop.id
            property_count += 1

            for unit in apt.get("units", []):
                listing = Listing(
                    property_id=prop.id,
                    owner_id=SCRIPT_USER_ID,
                    title=f"{apt['name']} - {unit.get('unit_type', 'Unit')}",
                    description=apt.get("address_meta", ""),
                    monthly_rent=parse_price(unit.get("price", "0")),
                    deposit_amount=parse_price(unit["deposit_amount"]) if unit.get("deposit_amount") else None,
                    lease_term_months=parse_int(unit["lease_term_months"]) if unit.get("lease_term_months") else None,
                    max_occupants=parse_int(unit["max_occupants"]) if unit.get("max_occupants") else None,
                    unit_type=map_unit_type(unit.get("unit_type", "")),
                    status=map_status(unit.get("availability", "")),
                )
                db.add(listing)
                listing_count += 1

        db.commit()
        print(f"Seeded {property_count} properties and {listing_count} listings.")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(
            "Usage: uv run python scripts/run_script.py seed_unishack <path-to-unishack.json>"
        )
        sys.exit(1)
    seed(sys.argv[1])
