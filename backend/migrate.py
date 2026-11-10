"""Explicit, versioned, additive migrations for SQLite and PostgreSQL.

Run once before deploying new code: python migrate.py
Existing data is preserved. Duplicate identities stop migration for manual review.
"""
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from database import engine
from migrations.v001_initial import upgrade as upgrade_v1

MIGRATIONS = ((1, upgrade_v1),)
SCHEMA_VERSION = MIGRATIONS[-1][0]


def check_schema(target=engine):
    try:
        with target.connect() as conn:
            version = conn.execute(text("SELECT MAX(version) FROM schema_migrations")).scalar()
    except SQLAlchemyError as exc:
        raise RuntimeError("Database is not migrated. Run python migrate.py first.") from exc
    if version != SCHEMA_VERSION:
        raise RuntimeError("Database schema does not match this application. Run python migrate.py.")


def upgrade(target=engine):
    with target.connect() as conn:
        # Serialize migration processes independently of the workflow scheduler.
        if target.dialect.name == "sqlite":
            conn.exec_driver_sql("BEGIN IMMEDIATE")
        else:
            conn.begin()
            conn.execute(text("SELECT pg_advisory_xact_lock(48173001)"))
        try:
            conn.execute(text("CREATE TABLE IF NOT EXISTS schema_migrations (version INTEGER PRIMARY KEY)"))
            version = conn.execute(text("SELECT MAX(version) FROM schema_migrations")).scalar() or 0
            if version > SCHEMA_VERSION:
                raise RuntimeError("Database is newer than this application")
            for number, apply in MIGRATIONS:
                if version < number:
                    apply(conn)
                    conn.execute(text("INSERT INTO schema_migrations (version) VALUES (:version)"), {"version": number})
            conn.commit()
        except Exception:
            conn.rollback()
            raise


if __name__ == "__main__":
    upgrade()
    print(f"Database schema is at version {SCHEMA_VERSION}")
