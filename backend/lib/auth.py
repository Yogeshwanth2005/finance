from __future__ import annotations

import logging
import os
import secrets
import uuid
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from fastapi import Depends, HTTPException, Request, Response, status

from lib.db import db

JWT_ALGORITHM = "HS256"
ACCESS_MINUTES = 30
REFRESH_DAYS = 7

logger = logging.getLogger(__name__)


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))


def _secret() -> str:
    return os.environ["JWT_SECRET"]


def _token(user_id: str, email: str, token_type: str, expires: timedelta) -> str:
    payload = {
        "sub": user_id,
        "email": email,
        "type": token_type,
        "exp": datetime.now(timezone.utc) + expires,
    }
    return jwt.encode(payload, _secret(), algorithm=JWT_ALGORITHM)


def create_access_token(user_id: str, email: str) -> str:
    return _token(user_id, email, "access", timedelta(minutes=ACCESS_MINUTES))


def create_refresh_token(user_id: str, email: str) -> str:
    return _token(user_id, email, "refresh", timedelta(days=REFRESH_DAYS))


def set_auth_cookies(response: Response, user_id: str, email: str) -> None:
    secure = os.environ.get("FRONTEND_URL", "").startswith("https://")
    common = {"httponly": True, "secure": secure, "samesite": "lax", "path": "/"}
    response.set_cookie("access_token", create_access_token(user_id, email), max_age=ACCESS_MINUTES * 60, **common)
    response.set_cookie("refresh_token", create_refresh_token(user_id, email), max_age=REFRESH_DAYS * 24 * 60 * 60, **common)


def clear_auth_cookies(response: Response) -> None:
    response.delete_cookie("access_token", path="/")
    response.delete_cookie("refresh_token", path="/")


async def get_current_user(request: Request) -> dict:
    token = request.cookies.get("access_token")
    if not token:
        header = request.headers.get("Authorization", "")
        token = header[7:] if header.startswith("Bearer ") else None
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    try:
        payload = jwt.decode(token, _secret(), algorithms=[JWT_ALGORITHM])
        if payload.get("type") != "access" or not payload.get("sub"):
            raise HTTPException(status_code=401, detail="Invalid access token")
    except jwt.ExpiredSignatureError as exc:
        raise HTTPException(status_code=401, detail="Session expired") from exc
    except jwt.InvalidTokenError as exc:
        raise HTTPException(status_code=401, detail="Invalid session") from exc

    user = await db.users.find_one({"_id": payload["sub"]})
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return {
        "id": user["_id"],
        "name": user["name"],
        "email": user["email"],
        "role": user.get("role", "user"),
        "profile_complete": bool(user.get("profile_complete", False)),
        "preferred_language": user.get("preferred_language", "en"),
        "notifications_enabled": bool(user.get("notifications_enabled", True)),
        "privacy_mode": bool(user.get("privacy_mode", True)),
        "created_at": user["created_at"],
    }


async def require_admin(user: dict = Depends(get_current_user)) -> dict:
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


async def seed_admin() -> None:
    email = os.environ.get("ADMIN_EMAIL", "").lower()
    password = os.environ.get("ADMIN_PASSWORD", "")
    if not email or not password:
        logger.warning("ADMIN_EMAIL/ADMIN_PASSWORD not set; skipping admin seed")
        return
    existing = await db.users.find_one({"email": email})
    if existing:
        if not verify_password(password, existing["password_hash"]):
            await db.users.update_one({"_id": existing["_id"]}, {"$set": {"password_hash": hash_password(password)}})
        return
    await db.users.insert_one(
        {
            "_id": str(uuid.uuid4()),
            "name": "Suraksha Admin",
            "email": email,
            "password_hash": hash_password(password),
            "role": "admin",
            "profile_complete": False,
            "preferred_language": "en",
            "notifications_enabled": True,
            "privacy_mode": True,
            "created_at": datetime.now(timezone.utc),
        }
    )


def new_reset_token() -> str:
    return secrets.token_urlsafe(32)