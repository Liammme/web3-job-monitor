from __future__ import annotations
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer

from app.core.config import settings
from app.utils.auth import verify_access_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def require_user(token: str = Depends(oauth2_scheme)) -> str:
    subject = verify_access_token(token)
    if not subject:
        raise HTTPException(status_code=401, detail="Invalid token")
    return subject


def verify_login(username: str, password: str) -> bool:
    return username == settings.auth_username and password == settings.auth_password
