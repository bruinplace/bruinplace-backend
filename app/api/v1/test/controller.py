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
        "items": [
            {"id": 1, "name": "Item One"},
            {"id": 2, "name": "Item Two"},
            {"id": 3, "name": "Item Three"},
        ],
        "message": "Sample data for testing",
    }


@router.get("/health")
def health():
    """Health check endpoint."""
    return {"status": "ok"}
