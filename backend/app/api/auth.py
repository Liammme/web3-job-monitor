from __future__ import annotations
from fastapi import APIRouter, HTTPException

from app.api.deps import verify_login
from app.schemas.auth import LoginRequest, TokenResponse
from app.utils.auth import create_access_token

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
def login(req: LoginRequest):
    if not verify_login(req.username, req.password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_access_token(req.username)
    return TokenResponse(access_token=token)
