from fastapi import APIRouter, Depends
from app.api.v1.reviews.schemas import ReviewCreate
from app.api.deps import get_current_user

router = APIRouter()


@router.post("/properties/{property_id}/reviews")
def create_review(
    property_id: str, payload: ReviewCreate, user=Depends(get_current_user)
):
    return {"status": "created"}
