from fastapi import APIRouter
from app.api.v1 import auth, listings, properties, reviews, users

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(users.router, prefix="/me", tags=["users"])
api_router.include_router(listings.router, prefix="/listings", tags=["listings"])
api_router.include_router(properties.router, prefix="/properties", tags=["properties"])
api_router.include_router(reviews.router, tags=["reviews"])
