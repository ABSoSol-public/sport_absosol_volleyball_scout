from fastapi import Cookie, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import verify_session_token
from app.db.session import get_db
from app.models import User

SESSION_COOKIE = "volleyscout_session"


def get_current_user(
    db: Session = Depends(get_db),
    volleyscout_session: str | None = Cookie(default=None),
) -> User:
    if not volleyscout_session:
        raise HTTPException(401, "Nicht angemeldet.")
    user_id = verify_session_token(volleyscout_session, get_settings().secret_key)
    if user_id is None:
        raise HTTPException(401, "Sitzung ungültig oder abgelaufen.")
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(401, "Benutzer existiert nicht mehr.")
    return user


def require_writer(user: User = Depends(get_current_user)) -> User:
    if user.role == "viewer":
        raise HTTPException(403, "Nur-Lese-Zugriff — diese Aktion ist nicht erlaubt.")
    return user
