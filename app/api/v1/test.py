"""
Simple test endpoints for frontend integration testing.
No auth required.
"""
from fastapi import APIRouter

router = APIRouter()


@router.get("/sample")
def sample():
    """Sample data for testing frontend display."""
    return {
        "listings": [
            {"id": "1", "title": "Cozy Westwood Studio", "monthly_rent": 1800},
            {"id": "2", "title": "2BR near Campus", "monthly_rent": 2400},
            {"id": "3", "title": "Shared Room - Gayley", "monthly_rent": 950},
        ],
        "message": "Sample data for testing",
    }
