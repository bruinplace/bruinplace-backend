from pydantic import BaseModel

class ListingCreate(BaseModel):
    title: str
    monthly_rent: int
    property_id: str

class ListingOut(ListingCreate):
    id: str
