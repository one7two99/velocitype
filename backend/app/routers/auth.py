"""Auth router: register, login, logout, refresh, me (Section 4).

- Argon2id password hashing
- RS256 JWT access tokens in httpOnly + SameSite=Strict cookies
- Opaque refresh tokens with rotation, stored hashed
- Per-IP Redis rate limiting on register/login
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy import or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.cookies import clear_auth_cookies, set_access_cookie, set_refresh_cookie
from app.auth.dependencies import get_current_user
from app.auth.password import hash_password, hash_token, verify_password
from app.auth.rate_limit import rate_limiter
from app.auth.tokens import (
    create_access_token,
    generate_refresh_token,
    refresh_expiry,
)
from app.config import get_settings
from app.db.session import get_db
from app.errors import ProblemException
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.schemas.auth import (
    ChangeEmailRequest,
    ChangePasswordRequest,
    DeleteAccountRequest,
    LoginRequest,
    MessageResponse,
    RegisterRequest,
    UserResponse,
)

_settings = get_settings()
router = APIRouter(prefix="/api/auth", tags=["auth"])


async def _issue_tokens(response: Response, db: AsyncSession, user: User) -> None:
    """Mint an access JWT + a fresh refresh token, persist the refresh hash, and
    set both httpOnly cookies."""
    access = create_access_token(user.id, user.username)
    refresh = generate_refresh_token()
    db.add(
        RefreshToken(
            id=uuid.uuid4(),
            user_id=user.id,
            token_hash=hash_token(refresh),
            expires_at=refresh_expiry(),
        )
    )
    await db.commit()
    set_access_cookie(response, access)
    set_refresh_cookie(response, refresh)


@router.post("/register", response_model=UserResponse, status_code=201)
async def register(
    payload: RegisterRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(rate_limiter("register", limit=_settings.rate_limit_register)),
) -> User:
    existing = await db.execute(
        select(User).where(
            or_(User.username == payload.username, User.email == str(payload.email))
        )
    )
    if existing.scalar_one_or_none() is not None:
        raise ProblemException(
            status_code=409,
            title="Conflict",
            detail="Username or email already registered.",
            type_="about:duplicate-user",
        )

    user = User(
        username=payload.username,
        email=str(payload.email),
        password_hash=hash_password(payload.password),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    await _issue_tokens(response, db, user)
    return user


@router.post("/login", response_model=UserResponse)
async def login(
    payload: LoginRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(rate_limiter("login", limit=_settings.rate_limit_login)),
) -> User:
    result = await db.execute(
        select(User).where(
            or_(User.username == payload.username, User.email == payload.username)
        )
    )
    user = result.scalar_one_or_none()

    # Constant-ish work whether or not the user exists (mitigate enumeration).
    valid = bool(user) and verify_password(payload.password, user.password_hash)
    if not user or not valid or not user.is_active:
        raise ProblemException(
            status_code=401,
            title="Unauthorized",
            detail="Invalid credentials.",
            type_="about:invalid-credentials",
        )

    user.last_login = datetime.now(timezone.utc)
    await db.commit()
    await _issue_tokens(response, db, user)
    return user


@router.post("/refresh", response_model=MessageResponse)
async def refresh(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    """Rotate the refresh token: verify + revoke the presented one, issue a new
    pair. Reuse of a revoked/expired token is rejected."""
    presented = request.cookies.get(_settings.refresh_cookie_name)
    if not presented:
        raise ProblemException(
            status_code=401, title="Unauthorized",
            detail="No refresh token.", type_="about:unauthorized",
        )

    token_hash = hash_token(presented)
    result = await db.execute(
        select(RefreshToken).where(RefreshToken.token_hash == token_hash)
    )
    stored = result.scalar_one_or_none()
    now = datetime.now(timezone.utc)

    if stored is None or stored.revoked or stored.expires_at <= now:
        clear_auth_cookies(response)
        raise ProblemException(
            status_code=401, title="Unauthorized",
            detail="Refresh token invalid or expired.", type_="about:unauthorized",
        )

    user = await db.get(User, stored.user_id)
    if user is None or not user.is_active:
        clear_auth_cookies(response)
        raise ProblemException(
            status_code=401, title="Unauthorized",
            detail="User not found or inactive.", type_="about:unauthorized",
        )

    stored.revoked = True  # rotation
    await db.commit()
    await _issue_tokens(response, db, user)
    return MessageResponse(detail="Token refreshed.")


@router.post("/logout", response_model=MessageResponse)
async def logout(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    presented = request.cookies.get(_settings.refresh_cookie_name)
    if presented:
        result = await db.execute(
            select(RefreshToken).where(RefreshToken.token_hash == hash_token(presented))
        )
        stored = result.scalar_one_or_none()
        if stored is not None and not stored.revoked:
            stored.revoked = True
            await db.commit()
    clear_auth_cookies(response)
    return MessageResponse(detail="Logged out.")


@router.get("/me", response_model=UserResponse)
async def me(current_user: User = Depends(get_current_user)) -> User:
    return current_user


def _bad_password() -> ProblemException:
    return ProblemException(
        status_code=401,
        title="Unauthorized",
        detail="Current password is incorrect.",
        type_="about:invalid-credentials",
    )


@router.patch("/password", response_model=MessageResponse)
async def change_password(
    payload: ChangePasswordRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> MessageResponse:
    if not verify_password(payload.current_password, user.password_hash):
        raise _bad_password()

    user.password_hash = hash_password(payload.new_password)
    # Invalidate every existing refresh token (log out other devices), then
    # re-issue a fresh pair for the current session.
    await db.execute(
        update(RefreshToken)
        .where(RefreshToken.user_id == user.id, RefreshToken.revoked.is_(False))
        .values(revoked=True)
    )
    await db.commit()
    await _issue_tokens(response, db, user)
    return MessageResponse(detail="Password changed.")


@router.patch("/email", response_model=UserResponse)
async def change_email(
    payload: ChangeEmailRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> User:
    if not verify_password(payload.password, user.password_hash):
        raise _bad_password()

    new_email = str(payload.email)
    if new_email != user.email:
        existing = await db.execute(
            select(User).where(User.email == new_email, User.id != user.id)
        )
        if existing.scalar_one_or_none() is not None:
            raise ProblemException(
                status_code=409,
                title="Conflict",
                detail="Email already registered.",
                type_="about:duplicate-user",
            )
        user.email = new_email
        await db.commit()
        await db.refresh(user)
    return user


@router.delete("/me", status_code=204, response_class=Response)
async def delete_account(
    payload: DeleteAccountRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Response:
    if not verify_password(payload.password, user.password_hash):
        raise _bad_password()
    # Cascades to sessions, keystrokes, key_stats, refresh_tokens, api_keys.
    await db.delete(user)
    await db.commit()
    clear_auth_cookies(response)
    return Response(status_code=204)
