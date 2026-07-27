"""Verwaltungs-CLI, z. B.: python -m app.cli create-user <name> <passwort> [admin|viewer]

Bei bestehendem Benutzer wird das Passwort neu gesetzt; die Rolle ändert sich
nur, wenn sie explizit angegeben ist (gleiches Verhalten wie create-user.sh im
yugioh_database-Projekt).
"""

import argparse
import sys

from sqlalchemy import select

from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models import User


def create_user(username: str, password: str, role: str | None) -> None:
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.username == username))
        if user is None:
            user = User(username=username, password_hash=hash_password(password), role=role or "admin")
            db.add(user)
            action = f"angelegt (Rolle: {user.role})"
        else:
            user.password_hash = hash_password(password)
            if role:
                user.role = role
            action = f"Passwort neu gesetzt (Rolle: {user.role})"
        db.commit()
        print(f"Benutzer {username!r} {action}.")


def main() -> None:
    parser = argparse.ArgumentParser(prog="app.cli")
    sub = parser.add_subparsers(dest="command", required=True)
    p_create = sub.add_parser("create-user", help="Benutzer anlegen / Passwort zurücksetzen")
    p_create.add_argument("username")
    p_create.add_argument("password")
    p_create.add_argument("role", nargs="?", choices=["admin", "viewer"], default=None)
    args = parser.parse_args()

    if args.command == "create-user":
        create_user(args.username, args.password, args.role)
    else:  # pragma: no cover
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
