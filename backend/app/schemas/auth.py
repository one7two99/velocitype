from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.auth.password import MIN_PASSWORD_LENGTH

USERNAME_PATTERN = r"^[A-Za-z0-9_.-]+$"


class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=32, pattern=USERNAME_PATTERN)
    email: EmailStr = Field(max_length=255)
    password: str = Field(min_length=MIN_PASSWORD_LENGTH, max_length=128)

    @field_validator("password")
    @classmethod
    def _password_strength(cls, v: str) -> str:
        if v.strip() != v:
            raise ValueError("password must not have leading/trailing whitespace")
        return v


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=255)
    password: str = Field(min_length=1, max_length=128)


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    username: str
    email: EmailStr
    created_at: datetime
    last_login: datetime | None
    is_active: bool


class MessageResponse(BaseModel):
    detail: str


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=MIN_PASSWORD_LENGTH, max_length=128)

    @field_validator("new_password")
    @classmethod
    def _new_password_strength(cls, v: str) -> str:
        if v.strip() != v:
            raise ValueError("password must not have leading/trailing whitespace")
        return v


class ChangeEmailRequest(BaseModel):
    password: str = Field(min_length=1, max_length=128)
    email: EmailStr = Field(max_length=255)


class DeleteAccountRequest(BaseModel):
    password: str = Field(min_length=1, max_length=128)
