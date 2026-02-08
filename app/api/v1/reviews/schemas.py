from pydantic import BaseModel


class ReviewCreate(BaseModel):
    overall_rating: int
    comment: str
