"""httpOnly + SameSite=Strict cookie helpers (Section 2).

Tokens are only ever transported in httpOnly cookies — never returned in a body
for JS to read, never placed in localStorage.
"""
from __future__ import annotations

from fastapi import Response

from app.config import get_settings

_settings = get_settings()


def _common_kwargs() -> dict:
    kwargs: dict = {
        "httponly": True,
        "secure": _settings.cookie_secure,
        "samesite": _settings.cookie_samesite,
        "path": "/",
    }
    if _settings.cookie_domain:
        kwargs["domain"] = _settings.cookie_domain
    return kwargs


def set_access_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=_settings.access_cookie_name,
        value=token,
        max_age=_settings.access_token_expire_minutes * 60,
        **_common_kwargs(),
    )


def set_refresh_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=_settings.refresh_cookie_name,
        value=token,
        max_age=_settings.refresh_token_expire_days * 24 * 3600,
        **_common_kwargs(),
    )


def clear_auth_cookies(response: Response) -> None:
    for name in (_settings.access_cookie_name, _settings.refresh_cookie_name):
        response.delete_cookie(
            key=name,
            path="/",
            domain=_settings.cookie_domain or None,
        )
