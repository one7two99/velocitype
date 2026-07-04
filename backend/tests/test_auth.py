"""Auth flow tests (integration; skip if no test DB).

Covers register/login/me/refresh/logout with httpOnly cookies, Pydantic 422s,
and password-policy enforcement.
"""
from __future__ import annotations

import pytest

from app.config import get_settings

_settings = get_settings()


async def test_register_sets_httponly_cookies(client, unique_user):
    resp = await client.post("/api/auth/register", json=unique_user)
    assert resp.status_code == 201
    body = resp.json()
    assert body["username"] == unique_user["username"]

    # Access + refresh cookies present and httpOnly.
    cookies = resp.headers.get_list("set-cookie")
    joined = " ".join(cookies).lower()
    assert _settings.access_cookie_name in joined
    assert _settings.refresh_cookie_name in joined
    assert "httponly" in joined


async def test_register_rejects_short_password(client, unique_user):
    bad = {**unique_user, "password": "short"}
    resp = await client.post("/api/auth/register", json=bad)
    assert resp.status_code == 422
    assert resp.headers["content-type"].startswith("application/problem+json")


async def test_login_and_me(client, unique_user):
    await client.post("/api/auth/register", json=unique_user)
    # Fresh client-side cookie jar via new login.
    login = await client.post(
        "/api/auth/login",
        json={"username": unique_user["username"], "password": unique_user["password"]},
    )
    assert login.status_code == 200

    me = await client.get("/api/auth/me")
    assert me.status_code == 200
    assert me.json()["email"] == unique_user["email"]


async def test_login_bad_credentials(client, unique_user):
    await client.post("/api/auth/register", json=unique_user)
    resp = await client.post(
        "/api/auth/login",
        json={"username": unique_user["username"], "password": "wrong-password-xx"},
    )
    assert resp.status_code == 401


async def test_me_requires_auth(client):
    resp = await client.get("/api/auth/me")
    assert resp.status_code == 401


async def test_refresh_rotates_and_logout(client, unique_user):
    await client.post("/api/auth/register", json=unique_user)
    old_refresh = client.cookies.get(_settings.refresh_cookie_name)

    refreshed = await client.post("/api/auth/refresh")
    assert refreshed.status_code == 200
    new_refresh = client.cookies.get(_settings.refresh_cookie_name)
    assert new_refresh and new_refresh != old_refresh

    logout = await client.post("/api/auth/logout")
    assert logout.status_code == 200
    # After logout the session cookie is cleared; /me should now be unauthorized.
    me = await client.get("/api/auth/me")
    assert me.status_code == 401
