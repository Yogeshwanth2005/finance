from unittest.mock import MagicMock
from fastapi import Response

from app.demo_user import get_or_create_demo_user, COOKIE_NAME
from app.models import User


def _fake_request(cookie_value=None):
    request = MagicMock()
    request.cookies = {COOKIE_NAME: cookie_value} if cookie_value else {}
    return request


def test_returns_existing_user_when_cookie_matches_a_row():
    existing_user = User(id="user-1", email="demo-1@fin.local")
    db = MagicMock()
    db.get.return_value = existing_user

    result = get_or_create_demo_user(_fake_request("user-1"), Response(), db)

    assert result is existing_user
    db.add.assert_not_called()


def test_creates_new_user_and_sets_cookie_when_no_cookie_present():
    db = MagicMock()
    db.get.return_value = None

    response = Response()
    get_or_create_demo_user(_fake_request(None), response, db)

    db.add.assert_called_once()
    db.commit.assert_called_once()
    assert "set-cookie" in response.headers
    assert COOKIE_NAME in response.headers["set-cookie"]


def test_creates_new_user_when_cookie_id_not_found_in_db():
    db = MagicMock()
    db.get.return_value = None

    get_or_create_demo_user(_fake_request("stale-id"), Response(), db)

    db.add.assert_called_once()
