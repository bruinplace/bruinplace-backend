from fastapi import APIRouter, Depends
from typing import List
from app.schemas.listing import ListingCreate, ListingOut
from app.api.deps import get_current_user

router = APIRouter()

@router.get("/", response_model=List[ListingOut])
def get_listings():
    return []

@router.post("/")
def create_listing(payload: ListingCreate, user=Depends(get_current_user)):
    return {"status": "created"}
