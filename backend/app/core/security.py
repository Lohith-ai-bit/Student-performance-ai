"""Password hashing (bcrypt) and JWT issuing/verification. No plaintext passwords, ever."""
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from app.core.config import settings


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:
        return False


def _create_token(subject: str, role: str, email: str, name: str, expires_delta: timedelta, token_type: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": subject,
        "role": role,
        "email": email,
        "name": name,
        "type": token_type,
        "iat": now,
        "exp": now + expires_delta,
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def create_access_token(user_id: str, role: str, email: str, name: str) -> str:
    return _create_token(
        user_id, role, email, name,
        timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES), "access",
    )


def create_refresh_token(user_id: str, role: str, email: str, name: str) -> str:
    return _create_token(
        user_id, role, email, name,
        timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS), "refresh",
    )


def decode_token(token: str) -> dict:
    """Raises jwt.InvalidTokenError / jwt.ExpiredSignatureError on failure."""
    return jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
