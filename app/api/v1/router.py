from fastapi import APIRouter
from app.api.v1.auth.controller import router as auth_router
from app.api.v1.users.controller import router as users_router
from app.api.v1.properties.controller import router as properties_router
from app.api.v1.reviews.controller import router as reviews_router
from app.api.v1.test.controller import router as test_router

api_router = APIRouter()
api_router.include_router(test_router, prefix="/test", tags=["test"])
api_router.include_router(auth_router, prefix="/auth", tags=["auth"])
api_router.include_router(users_router, prefix="/me", tags=["users"])
api_router.include_router(properties_router, prefix="/properties", tags=["properties"])
api_router.include_router(reviews_router, tags=["reviews"])
