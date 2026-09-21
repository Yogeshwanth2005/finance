from __future__ import annotations

import os
import uuid
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import APIRouter, Depends, HTTPException, Request, Response

from lib.auth import (
    clear_auth_cookies,
    get_current_user,
    hash_password,
    new_reset_token,
    set_auth_cookies,
    verify_password,
)
from lib.db import db
from models.auth import (
    ChangePasswordInput,
    ForgotPasswordInput,
    ForgotPasswordResponse,
    LoginInput,
    RegisterInput,
    ResetPasswordInput,
    UserSettingsInput,
    UserPublic,
)

router = APIRouter(prefix="/auth", tags=["auth"])


def _public(user: dict) -> UserPublic:
    return UserPublic(
        id=user["id"] if "id" in user else user["_id"],
        name=user["name"],
        email=user["email"],
        role=user.get("role", "user"),
        profile_complete=bool(user.get("profile_complete", False)),
        preferred_language=user.get("preferred_language", "en"),
        notifications_enabled=bool(user.get("notifications_enabled", True)),
        privacy_mode=bool(user.get("privacy_mode", True)),
        created_at=user["created_at"],
    )


async def _user_by_email(email: str) -> dict | None:
    user = await db.users.find_one({"email": email.lower()})
    if user:
        user["id"] = user["_id"]
    return user


@router.post("/register", response_model=UserPublic)
async def register(input_data: RegisterInput, response: Response) -> UserPublic:
    email = str(input_data.email).lower()
    if await _user_by_email(email):
        raise HTTPException(status_code=409, detail="An account with this email already exists")
    user = {
        "_id": str(uuid.uuid4()),
        "name": input_data.name.strip(),
        "email": email,
        "password_hash": hash_password(input_data.password),
        "role": "user",
        "profile_complete": False,
        "preferred_language": "en",
        "notifications_enabled": True,
        "privacy_mode": True,
        "created_at": datetime.now(timezone.utc),
    }
    await db.users.insert_one(user)
    set_auth_cookies(response, user["_id"], email)
    return _public({**user, "id": user["_id"]})


@router.post("/login", response_model=UserPublic)
async def login(input_data: LoginInput, request: Request, response: Response) -> UserPublic:
    email = str(input_data.email).lower()
    identifier = f"{request.client.host if request.client else 'unknown'}:{email}"
    attempt = await db.login_attempts.find_one({"_id": identifier})
    now = datetime.now(timezone.utc)
    if attempt and attempt.get("locked_until"):
        locked_until = attempt["locked_until"].replace(tzinfo=timezone.utc) if attempt["locked_until"].tzinfo is None else attempt["locked_until"]
        if locked_until > now:
            raise HTTPException(status_code=429, detail="Too many attempts. Try again in a few minutes.")

    user = await _user_by_email(email)
    if not user or not verify_password(input_data.password, user["password_hash"]):
        failed = (attempt or {}).get("attempts", 0) + 1
        update = {"$set": {"attempts": failed, "identifier": identifier}}
        if failed >= 5:
            update["$set"]["locked_until"] = now + timedelta(minutes=15)
        await db.login_attempts.update_one({"_id": identifier}, update, upsert=True)
        raise HTTPException(status_code=401, detail="Email or password is incorrect")

    await db.login_attempts.delete_one({"_id": identifier})
    set_auth_cookies(response, user["_id"], email)
    return _public(user)


@router.post("/logout")
async def logout(response: Response, _: dict = Depends(get_current_user)) -> dict[str, str]:
    clear_auth_cookies(response)
    return {"message": "Signed out"}


@router.get("/me", response_model=UserPublic)
async def me(user: dict = Depends(get_current_user)) -> UserPublic:
    return _public(user)


@router.patch("/settings", response_model=UserPublic)
async def update_settings(input_data: UserSettingsInput, user: dict = Depends(get_current_user)) -> UserPublic:
    updates = {key: value for key, value in input_data.model_dump().items() if value is not None}
    if "name" in updates:
        updates["name"] = updates["name"].strip()
    if updates:
        await db.users.update_one({"_id": user["id"]}, {"$set": updates})
    updated = await db.users.find_one({"_id": user["id"]})
    return _public(updated)


@router.post("/change-password")
async def change_password(input_data: ChangePasswordInput, user: dict = Depends(get_current_user)) -> dict[str, str]:
    stored = await db.users.find_one({"_id": user["id"]})
    if not stored or not verify_password(input_data.current_password, stored["password_hash"]):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    if input_data.current_password == input_data.new_password:
        raise HTTPException(status_code=400, detail="Choose a different new password")
    await db.users.update_one({"_id": user["id"]}, {"$set": {"password_hash": hash_password(input_data.new_password)}})
    return {"message": "Password updated successfully"}


@router.get("/session", response_model=UserPublic | None)
async def session(request: Request, response: Response) -> UserPublic | None:
    token = request.cookies.get("access_token")
    refresh_token = request.cookies.get("refresh_token")
    payload = None
    if token:
        try:
            decoded = jwt.decode(token, os.environ["JWT_SECRET"], algorithms=["HS256"])
            if decoded.get("type") == "access":
                payload = decoded
        except jwt.InvalidTokenError:
            payload = None
    if payload is None and refresh_token:
        try:
            decoded = jwt.decode(refresh_token, os.environ["JWT_SECRET"], algorithms=["HS256"])
            if decoded.get("type") == "refresh":
                payload = decoded
        except jwt.InvalidTokenError:
            payload = None
    if payload is None:
        return None
    user = await db.users.find_one({"_id": payload.get("sub")})
    if not user:
        return None
    set_auth_cookies(response, user["_id"], user["email"])
    return _public(user)


@router.post("/refresh", response_model=UserPublic)
async def refresh(request: Request, response: Response) -> UserPublic:
    token = request.cookies.get("refresh_token")
    if not token:
        raise HTTPException(status_code=401, detail="No refresh session")
    try:
        payload = jwt.decode(token, os.environ["JWT_SECRET"], algorithms=["HS256"])
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Invalid refresh token")
    except jwt.InvalidTokenError as exc:
        raise HTTPException(status_code=401, detail="Invalid refresh session") from exc
    user = await db.users.find_one({"_id": payload.get("sub")})
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    set_auth_cookies(response, user["_id"], user["email"])
    return _public(user)


@router.post("/forgot-password", response_model=ForgotPasswordResponse)
async def forgot_password(input_data: ForgotPasswordInput) -> ForgotPasswordResponse:
    user = await _user_by_email(str(input_data.email).lower())
    if not user:
        return ForgotPasswordResponse(message="If the account exists, reset instructions have been created.")
    token = new_reset_token()
    await db.password_reset_tokens.insert_one(
        {
            "_id": token,
            "user_id": user["_id"],
            "expires_at": datetime.now(timezone.utc) + timedelta(hours=1),
            "used": False,
        }
    )
    # There is no email provider in this MVP. Returning a clearly-labelled demo token keeps the flow testable.
    return ForgotPasswordResponse(message="Reset instructions created for this demo workspace.", demo_token=token)


@router.post("/reset-password")
async def reset_password(input_data: ResetPasswordInput) -> dict[str, str]:
    record = await db.password_reset_tokens.find_one({"_id": input_data.token, "used": False})
    if not record:
        raise HTTPException(status_code=400, detail="This reset link is invalid or already used")
    expiry = record["expires_at"].replace(tzinfo=timezone.utc) if record["expires_at"].tzinfo is None else record["expires_at"]
    if expiry < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="This reset link has expired")
    await db.users.update_one({"_id": record["user_id"]}, {"$set": {"password_hash": hash_password(input_data.password)}})
    await db.password_reset_tokens.update_one({"_id": input_data.token}, {"$set": {"used": True}})
    return {"message": "Password updated. You can sign in now."}