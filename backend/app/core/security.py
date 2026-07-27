"""Passwort-Hashing und Session-Tokens — bewusst ohne Zusatzabhängigkeiten.

- Passwörter: PBKDF2-HMAC-SHA256 mit zufälligem Salt (Format:
  ``pbkdf2$<iterationen>$<salt_hex>$<hash_hex>``).
- Sessions: kompaktes signiertes Token ``base64url(payload).hmac`` mit
  Ablaufzeit, signiert mit ``VOLLEYSCOUT_SECRET_KEY``. Kein JWT-Standard nötig —
  das Token wird ausschließlich von diesem Backend erzeugt und geprüft.
"""

import base64
import hashlib
import hmac
import json
import secrets
import time

PBKDF2_ITERATIONS = 240_000


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode(), bytes.fromhex(salt), PBKDF2_ITERATIONS
    )
    return f"pbkdf2${PBKDF2_ITERATIONS}${salt}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        scheme, iterations, salt, expected = stored.split("$")
        if scheme != "pbkdf2":
            return False
        digest = hashlib.pbkdf2_hmac(
            "sha256", password.encode(), bytes.fromhex(salt), int(iterations)
        )
        return hmac.compare_digest(digest.hex(), expected)
    except (ValueError, TypeError):
        return False


def _sign(data: bytes, secret: str) -> str:
    return hmac.new(secret.encode(), data, hashlib.sha256).hexdigest()


def create_session_token(user_id: int, secret: str, ttl_seconds: int) -> str:
    payload = json.dumps({"uid": user_id, "exp": int(time.time()) + ttl_seconds}).encode()
    encoded = base64.urlsafe_b64encode(payload).decode().rstrip("=")
    return f"{encoded}.{_sign(payload, secret)}"


def verify_session_token(token: str, secret: str) -> int | None:
    """Gibt die User-Id zurück, oder None bei ungültigem/abgelaufenem Token."""
    try:
        encoded, signature = token.split(".")
        payload = base64.urlsafe_b64decode(encoded + "=" * (-len(encoded) % 4))
        if not hmac.compare_digest(_sign(payload, secret), signature):
            return None
        data = json.loads(payload)
        if data["exp"] < time.time():
            return None
        return int(data["uid"])
    except (ValueError, KeyError, TypeError):
        return None
