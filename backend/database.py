"""Connection configuration only. Run `python migrate.py` before starting services."""
import os

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def database_url():
    url = os.environ.get("DATABASE_URL")
    if not url:
        if os.environ.get("APP_ENV", "development").lower() == "production":
            raise RuntimeError("DATABASE_URL is required in production")
        return f"sqlite:///{os.path.join(BASE_DIR, 'f1_races.db')}"
    return url.replace("postgres://", "postgresql://", 1) if url.startswith("postgres://") else url


def make_engine(url):
    engine = create_engine(url, pool_pre_ping=True)
    if engine.dialect.name == "sqlite":
        @event.listens_for(engine, "connect")
        def enable_foreign_keys(connection, _):
            connection.execute("PRAGMA foreign_keys=ON")
    return engine


engine = make_engine(database_url())
SessionLocal = sessionmaker(bind=engine)
