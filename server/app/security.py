"""Passwords and login tokens.

- Passwords are never stored. We store a bcrypt HASH (one-way, salted).
- After login the server gives a JWT. The browser sends it on every request:
      Authorization: Bearer <token>
  The token holds the user id ("sub") and an expiry ("exp"), and is signed with SECRET_KEY,
  so nobody can change it without the server noticing.
"""
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from .config import ACCESS_TOKEN_DAYS, SECRET_KEY

ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode(), hashed.encode())
    except ValueError:
        return False


def create_token(user_id: int) -> str:
    payload = {"sub": str(user_id), "exp": datetime.now(timezone.utc) + timedelta(days=ACCESS_TOKEN_DAYS)}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def read_token(token: str) -> int | None:
    """Returns the user id, or None if the token is fake, changed or expired."""
    try:
        return int(jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])["sub"])
    except (jwt.PyJWTError, KeyError, ValueError):
        return None
