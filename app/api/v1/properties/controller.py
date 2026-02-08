from fastapi import APIRouter
from app.api.v1.properties.schemas import PropertyOut

router = APIRouter()


@router.get("/{property_id}", response_model=PropertyOut)
def get_property(property_id: str):
    return {"id": property_id}
