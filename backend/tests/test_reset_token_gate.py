"""The reset token may only appear in the /auth/forgot-password response when EXPOSE_RESET_TOKEN is on.

Without it, anyone who knows an email could take over that account on a public deployment.
"""

from models.auth import ForgotPasswordInput
from routers import auth as auth_router


class _Tokens:
    def __init__(self):
        self.inserted = []

    async def insert_one(self, doc):
        self.inserted.append(doc)


class _FakeDb:
    def __init__(self):
        self.password_reset_tokens = _Tokens()


async def _forgot(monkeypatch):
    fake = _FakeDb()

    async def fake_user(email):
        return {"_id": "u1", "id": "u1", "email": email}

    monkeypatch.setattr(auth_router, "db", fake)
    monkeypatch.setattr(auth_router, "_user_by_email", fake_user)
    result = await auth_router.forgot_password(ForgotPasswordInput(email="someone@example.com"))
    return result, fake


async def test_token_hidden_by_default(monkeypatch):
    monkeypatch.delenv("EXPOSE_RESET_TOKEN", raising=False)
    result, fake = await _forgot(monkeypatch)
    assert result.demo_token is None
    assert len(fake.password_reset_tokens.inserted) == 1  # still stored for a future email flow


async def test_token_exposed_only_when_flag_is_true(monkeypatch):
    monkeypatch.setenv("EXPOSE_RESET_TOKEN", "true")
    result, fake = await _forgot(monkeypatch)
    assert result.demo_token == fake.password_reset_tokens.inserted[0]["_id"]


async def test_other_flag_values_do_not_expose_the_token(monkeypatch):
    monkeypatch.setenv("EXPOSE_RESET_TOKEN", "false")
    result, _ = await _forgot(monkeypatch)
    assert result.demo_token is None
