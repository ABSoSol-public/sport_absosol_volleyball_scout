from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import SESSION_COOKIE, get_current_user
from app.core.config import get_settings
from app.core.security import create_session_token, verify_password
from app.db.session import get_db
from app.models import User

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1)


class UserInfo(BaseModel):
    username: str
    role: str


@router.post("/login", response_model=UserInfo)
def login(data: LoginRequest, response: Response, db: Session = Depends(get_db)) -> UserInfo:
    settings = get_settings()
    user = db.scalar(select(User).where(User.username == data.username))
    if user is None or not verify_password(data.password, user.password_hash):
        raise HTTPException(401, "Benutzername oder Passwort falsch.")
    ttl = settings.session_ttl_hours * 3600
    response.set_cookie(
        SESSION_COOKIE,
        create_session_token(user.id, settings.secret_key, ttl),
        max_age=ttl,
        httponly=True,
        samesite="lax",
        secure=settings.cookie_secure,
    )
    return UserInfo(username=user.username, role=user.role)


@router.post("/logout")
def logout(response: Response) -> dict[str, str]:
    response.delete_cookie(SESSION_COOKIE)
    return {"status": "ok"}


@router.get("/me", response_model=UserInfo)
def me(user: User = Depends(get_current_user)) -> UserInfo:
    return UserInfo(username=user.username, role=user.role)
