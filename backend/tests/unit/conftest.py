"""Pure-function tests: no backend server and no MongoDB.

The parent conftest's autouse session fixture seeds accounts through the live API, which these tests must not
need, so it is overridden with a no-op here. routers.profile imports lib.db, which builds a Motor client at import
(Motor connects lazily, so nothing is contacted); the env fallbacks only matter on a checkout without a .env.
"""

import os
from pathlib import Path

import pytest
from dotenv import load_dotenv

load_dotenv(Path(__file__).parents[2] / ".env")  # same load lib.db does, so a real .env keeps winning over the fallbacks
os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "unit_tests_never_connected")


@pytest.fixture(scope="session", autouse=True)
def seeded_retest_fixtures():
    yield
