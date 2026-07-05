"""Symmetric encryption for at-rest secrets (e.g. per-user Mistral API keys).

The Fernet key is derived from the deployment's JWT private key, so there is no
extra secret to manage: rotating the JWT keys invalidates stored ciphertexts,
which for API keys simply means the user re-enters the key.
"""
from __future__ import annotations

import base64
import hashlib
from functools import lru_cache

from cryptography.fernet import Fernet, InvalidToken

from app.config import get_settings


@lru_cache
def _fernet() -> Fernet:
    digest = hashlib.sha256(get_settings().jwt_private_key.encode()).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def encrypt(plaintext: str) -> str:
    return _fernet().encrypt(plaintext.encode()).decode()


def decrypt(token: str) -> str | None:
    """Return the plaintext, or None if the ciphertext can't be decrypted
    (e.g. the JWT key changed). Callers treat None as "no usable key"."""
    try:
        return _fernet().decrypt(token.encode()).decode()
    except (InvalidToken, ValueError):
        return None
