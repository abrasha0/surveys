import hmac
import hashlib
import secrets
import logging
from typing import Optional

from fastapi import APIRouter, Response, Cookie, HTTPException, Depends
from pydantic import BaseModel

from config import config

logger = logging.getLogger(__name__)

_SECRET_KEY = secrets.token_hex(32)
_TOKEN_TTL = 60 * 60 * 8  # 8h — wystarczające dla single-user session


def create_session_token(password: str) -> Optional[str]:
    if not hmac.compare_digest(password, config.app["password"]):
        return None
    payload = secrets.token_hex(16)
    sig = hmac.new(
        _SECRET_KEY.encode(), payload.encode(), hashlib.sha256
    ).hexdigest()
    return f"{payload}.{sig}"


def verify_session_token(token: str) -> bool:
    try:
        payload, sig = token.split(".", 1)
    except ValueError:
        return False
    expected = hmac.new(
        _SECRET_KEY.encode(), payload.encode(), hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(sig, expected)


def get_current_user(session_token: Optional[str] = Cookie(None)):
    if not session_token or not verify_session_token(session_token):
        raise HTTPException(status_code=401, detail="Not authenticated")
    return "user"


auth_router = APIRouter(prefix="/api/auth", tags=["auth"])


@auth_router.get("/health")
def health_check():
    return {"status": "ok"}


class LoginRequest(BaseModel):
    password: str


@auth_router.post("/login")
def login(body: LoginRequest, response: Response):
    token = create_session_token(body.password)
    if token is None:
        raise HTTPException(status_code=401, detail="Invalid password")
    response.set_cookie(
        key="session_token",
        value=token,
        httponly=True,
        samesite="lax",
        max_age=_TOKEN_TTL,
    )
    return {"status": "ok"}


@auth_router.post("/logout")
def logout(response: Response):
    response.delete_cookie("session_token")
    return {"status": "ok"}
