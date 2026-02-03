import secrets
from datetime import timedelta
from urllib.parse import urlencode

import requests
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import RedirectResponse, JSONResponse
from google.oauth2 import id_token as google_id_token
from google.auth.transport.requests import Request as GoogleRequest

from app.api.deps import get_current_user, get_db
from app.core.config import settings
from app.core.security import create_access_token
from sqlalchemy.orm import Session
from app.api.v1.users.models import User


router = APIRouter()


@router.get("/login")
def login():
    if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_REDIRECT_URI:
        raise HTTPException(status_code=500, detail="Google OAuth not configured")

    state = secrets.token_urlsafe(16)
    params = {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "redirect_uri": settings.GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": "openid email profile",
        "include_granted_scopes": "true",
        "prompt": "select_account",
        "state": state,
        # Optional hint; verification still enforced server-side
        # "hd": settings.ALLOWED_GOOGLE_HD[0] if settings.ALLOWED_GOOGLE_HD else None,
    }
    auth_url = "https://accounts.google.com/o/oauth2/v2/auth?" + urlencode({k: v for k, v in params.items() if v is not None})
    response = RedirectResponse(auth_url, status_code=status.HTTP_302_FOUND)
    response.set_cookie("oauth_state", state, httponly=True, samesite="lax")
    return response


@router.get("/callback")
def callback(
    request: Request,
    code: str | None = None,
    state: str | None = None,
    db: Session = Depends(get_db),
):
    stored_state = request.cookies.get("oauth_state")
    if not code or not state or not stored_state or state != stored_state:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid OAuth state or code")

    # Exchange authorization code for tokens
    token_resp = requests.post(
        "https://oauth2.googleapis.com/token",
        data={
            "code": code,
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "redirect_uri": settings.GOOGLE_REDIRECT_URI,
            "grant_type": "authorization_code",
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=10,
    )

    if not token_resp.ok:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to exchange code")

    token_data = token_resp.json()
    id_token = token_data.get("id_token")
    if not id_token:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No id_token in response")

    # Verify the ID token
    idinfo = google_id_token.verify_oauth2_token(id_token, GoogleRequest(), settings.GOOGLE_CLIENT_ID)

    email = idinfo.get("email")
    email_verified = idinfo.get("email_verified")
    if not email or not email_verified:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Email not verified")

    allowed = any(email.endswith("@" + d) for d in settings.allowed_google_domains)
    if not allowed:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Email domain not allowed")

    # Upsert user (JIT provisioning)
    user_id = idinfo.get("sub")
    existing: User | None = db.get(User, user_id)
    if existing:
        existing.email = email
        existing.name = idinfo.get("name")
        existing.picture = idinfo.get("picture")
        # Update last_login
        from datetime import datetime

        existing.last_login = datetime.utcnow()
    else:
        db.add(
            User(
                id=user_id,
                email=email,
                name=idinfo.get("name"),
                picture=idinfo.get("picture"),
            )
        )
    db.commit()

    # Issue app JWT
    payload = {
        "sub": user_id,
        "email": email,
        "name": idinfo.get("name"),
        "picture": idinfo.get("picture"),
    }
    access_token = create_access_token(
        payload,
        secret_key=settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )

    # Return token and user info; also set HttpOnly session cookie for web clients
    resp = JSONResponse(
        {
            "access_token": access_token,
            "token_type": "bearer",
            "user": payload,
        }
    )
    resp.set_cookie(
        key="bp_session",
        value=access_token,
        httponly=True,
        samesite="lax",
        secure=(settings.ENVIRONMENT == "production"),
    )
    # Clear one-time oauth state cookie
    resp.delete_cookie("oauth_state")
    return resp


@router.get("/me")
def me(user=Depends(get_current_user)):
    return user


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(response: Response):
    # Clear session and transient oauth cookies
    response.delete_cookie("bp_session")
    response.delete_cookie("oauth_state")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
