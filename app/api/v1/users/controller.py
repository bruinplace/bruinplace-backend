from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from .models import User
from .schemas import MeOut

router = APIRouter()


@router.get("", response_model=MeOut)
def get_me(user=Depends(get_current_user), db: Session = Depends(get_db)):
    db_user: User | None = db.get(User, user["sub"])
    if not db_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return {
        "id": db_user.id,
        "email": db_user.email,
        "name": db_user.name,
        "profile_picture": db_user.profile_image if hasattr(db_user, "profile_image") else db_user.profile_picture,
        "created_at": db_user.created_at,
        "last_login": db_user.last_login,
    }
