from fastapi import APIRouter, Depends

from app.api.deps import get_current_user
from .models import User
from .schemas import UserResponse

router = APIRouter()

@router.get("", response_model=UserResponse)
def get_me(user: User = Depends(get_current_user)) -> UserResponse:
    return user
