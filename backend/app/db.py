import os
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import NullPool

load_dotenv()


def _to_psycopg_url(raw_url: str) -> str:
    """Rewrite a Prisma-style pooled connection string for psycopg3.

    `pgbouncer=true` is a Prisma/asyncpg-side hint for Supabase's
    transaction-mode pooler — psycopg3 passes unrecognized query params
    straight to libpq, which rejects it as an invalid connection option.
    NullPool + connect_args={"prepare_threshold": None} already give the
    same "don't rely on server-side prepared statements/persistent pool
    state" behavior that flag exists for, so it's safe to drop.
    """
    scheme, netloc, path, query, fragment = urlsplit(raw_url)
    filtered_query = urlencode([(k, v) for k, v in parse_qsl(query) if k != "pgbouncer"])
    return urlunsplit(("postgresql+psycopg", netloc, path, filtered_query, fragment))


DATABASE_URL = _to_psycopg_url(os.environ["DATABASE_URL"])

engine = create_engine(
    DATABASE_URL,
    poolclass=NullPool,
    connect_args={"prepare_threshold": None},
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
