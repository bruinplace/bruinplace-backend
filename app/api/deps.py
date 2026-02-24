from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.api.v1.users.models import User
from app.core.config import settings
from app.core.security import decode_access_token
from app.db.session import SessionLocal


security = HTTPBearer(auto_error=False)


def get_db() -> Session:
    """Yield a database session and ensure it is closed after the request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    """Decode the JWT and return the authenticated User row from the database."""
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

    sub = payload.get("sub")
    if not sub:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload"
        )

    user = db.get(User, sub)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found"
        )

    return user
