import os
import uuid

from fastapi import Depends, Request, Response
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import User

COOKIE_NAME = "fin_demo_user_id"
COOKIE_MAX_AGE_SECONDS = 60 * 60 * 24 * 365


def get_or_create_demo_user(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
) -> User:
    existing_id = request.cookies.get(COOKIE_NAME)

    if existing_id:
        existing = db.get(User, existing_id)
        if existing:
            return existing

    created = User(email=f"demo-{uuid.uuid4()}@fin.local")
    db.add(created)
    db.commit()
    db.refresh(created)

    is_production = os.getenv("ENVIRONMENT", "development") == "production"
    response.set_cookie(
        key=COOKIE_NAME,
        value=created.id,
        max_age=COOKIE_MAX_AGE_SECONDS,
        httponly=True,
        samesite="none" if is_production else "lax",
        secure=is_production,
        path="/",
    )

    return created
