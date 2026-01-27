from fastapi import APIRouter
from app.schemas.property import PropertyOut

router = APIRouter()

@router.get("/{property_id}", response_model=PropertyOut)
def get_property(property_id: str):
    return {"id": property_id}
