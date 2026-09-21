"""seed_admin must never invent a default-password admin when env is unset."""

from lib import auth


class _NoDb:
    def __getattr__(self, name):
        raise AssertionError(f"db.{name} must not be touched when admin env is unset")


async def test_seed_admin_skips_without_password(monkeypatch):
    monkeypatch.setenv("ADMIN_EMAIL", "admin@example.com")
    monkeypatch.delenv("ADMIN_PASSWORD", raising=False)
    monkeypatch.setattr(auth, "db", _NoDb())
    await auth.seed_admin()


async def test_seed_admin_skips_without_email(monkeypatch):
    monkeypatch.delenv("ADMIN_EMAIL", raising=False)
    monkeypatch.setenv("ADMIN_PASSWORD", "SomePassword!1")
    monkeypatch.setattr(auth, "db", _NoDb())
    await auth.seed_admin()
