"""Password hashing (Argon2id) and generic secret hashing.

Argon2id via passlib (Section 2). Refresh tokens and API keys are opaque random
strings, so they are hashed with SHA-256 (fast, constant-length) rather than
Argon2 — they carry full entropy and are not user-chosen, low-entropy passwords.
"""
from __future__ import annotations

import hashlib

from passlib.context import CryptContext

_pwd_context = CryptContext(
    schemes=["argon2"],
    deprecated="auto",
    argon2__type="ID",  # Argon2id
)

MIN_PASSWORD_LENGTH = 12


def hash_password(password: str) -> str:
    return _pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return _pwd_context.verify(password, password_hash)
    except Exception:
        return False


def needs_rehash(password_hash: str) -> bool:
    return _pwd_context.needs_update(password_hash)


def hash_token(token: str) -> str:
    """Hash a high-entropy opaque token (refresh token / API key) for storage."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
