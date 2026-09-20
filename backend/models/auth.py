from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, EmailStr, Field


class RegisterInput(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class LoginInput(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class ForgotPasswordInput(BaseModel):
    email: EmailStr


class ResetPasswordInput(BaseModel):
    token: str = Field(min_length=20)
    password: str = Field(min_length=8, max_length=128)


class UserPublic(BaseModel):
    id: str
    name: str
    email: EmailStr
    role: str
    profile_complete: bool
    preferred_language: Literal["en", "hi", "te", "ta"] = "en"
    notifications_enabled: bool = True
    privacy_mode: bool = True
    created_at: datetime


class UserSettingsInput(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=100)
    preferred_language: Literal["en", "hi", "te", "ta"] | None = None
    notifications_enabled: bool | None = None
    privacy_mode: bool | None = None


class ChangePasswordInput(BaseModel):
    current_password: str = Field(min_length=8, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)


class ForgotPasswordResponse(BaseModel):
    message: str
    demo_token: str | None = None