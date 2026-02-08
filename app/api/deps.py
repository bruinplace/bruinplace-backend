from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import settings
from app.core.security import decode_access_token
from app.db.session import SessionLocal
from sqlalchemy.orm import Session


security = HTTPBearer(auto_error=False)


def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
):
    token = credentials.credentials if credentials else None
    if not token:
        token = request.cookies.get("bp_session")
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"
        )

    payload = decode_access_token(
        token, secret_key=settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM
    )

    user = {
        "sub": payload.get("sub"),
        "email": payload.get("email"),
        "name": payload.get("name"),
        "profile_picture": payload.get("picture"),
    }

    if not user["sub"] or not user["email"]:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload"
        )

    return user


def get_db() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
